import asyncio
import boto3
import os
import math
import json
import time

from dataclasses import dataclass
from botocore.exceptions import BotoCoreError, ClientError
from botocore.config import Config

from pathlib import Path

from concurrent.futures import ThreadPoolExecutor
from typing import Union, Optional, Tuple
import threading

from yomitoku_client.utils import (
    load_pdf_to_bytes,
    load_tiff_to_bytes,
    make_page_index,
)

from yomitoku_client.logger import set_logger

from datetime import datetime

from .constants import SUPPORT_INPUT_FORMAT


logger = set_logger(__name__, "INFO")


class YomiTokuError(Exception):
    pass


class YomiTokuInvokeError(YomiTokuError):
    pass


@dataclass
class PagePayload:
    index: int
    content_type: str
    body: bytes
    source_name: str


@dataclass
class InvokeResult:
    index: int
    raw_dict: dict  # SageMaker JSON


@dataclass
class CircuitConfig:
    threshold: int = 5  # サーキットブレーカーの失敗閾値
    cooldown_sec: int = 30  # サーキットオープン後のクールダウン時間（秒）


@dataclass
class RequestConfig:
    read_timeout: int = 60
    connect_timeout: int = 10
    max_attempts: int = 3


def guess_content_type(path: Union[str]) -> str:
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext in [".png"]:
        return "image/png"
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if ext in [".tif", ".tiff"]:
        return "image/tiff"
    raise ValueError(f"Unsupported file extension: {ext}")


def load_image_bytes(
    path_img: str,
    content_type: str,
    dpi=200,
) -> Tuple[list[bytes], str]:
    if content_type == "application/pdf":
        img_bytes = load_pdf_to_bytes(path_img, dpi=dpi)
        # NOTE: PDFはページ分割・ラスター化してPNG化。以降のinvokeはimage/pngで送る
        content_type = "image/png"
    elif content_type == "image/tiff":
        img_bytes = load_tiff_to_bytes(path_img)
    else:
        with open(path_img, "rb") as f:
            img_bytes = [f.read()]
    return img_bytes, content_type


def with_mfa_session(
    base_sess: boto3.Session,
    mfa_serial: str,
    token: str,
) -> boto3.Session:
    """
    Create a session with MFA authentication.

    Args:
        base_sess: Base boto3 session (default creds / profile)
        mfa_serial: MFA device ARN (e.g. arn:aws:iam::...:mfa/xxxx)
        token: 6-digit MFA code
    """
    sts = base_sess.client("sts")
    resp = sts.get_session_token(
        SerialNumber=mfa_serial,
        TokenCode=token,
        DurationSeconds=43200,
    )
    c = resp["Credentials"]
    return boto3.Session(
        region_name=base_sess.region_name,
        aws_access_key_id=c["AccessKeyId"],
        aws_secret_access_key=c["SecretAccessKey"],
        aws_session_token=c["SessionToken"],
    )


def now_ms() -> int:
    return int(time.time() * 1000)


def _merge_results(results: list[InvokeResult]) -> dict:
    base = dict(results[0].raw_dict)
    key = "result"
    base[key][0]["num_page"] = results[0].index
    if not isinstance(base.get(key), list):
        return base
    for r in results[1:]:
        items = r.raw_dict.get(key, [])
        if isinstance(items, list):
            for item in items:
                item["num_page"] = r.index
                base[key].append(item)
    return base


class YomitokuClient:
    def __init__(
        self,
        endpoint: str,
        region: str,
        mfa_serial: str = None,
        mfa_token: str = None,
        max_workers: int = 4,
        request_config: Optional[RequestConfig] = None,
        circuit_config: Optional[CircuitConfig] = None,
    ):
        logger.info("YomitokuClient initialized")
        self.endpoint = endpoint
        self.region = region

        self._cb_lock = threading.Lock()

        base_session = boto3.Session(region_name=region)
        if mfa_serial and mfa_token:
            logger.info("Using MFA authentication for AWS session")
            base_sess = boto3.Session(region_name=region)
            self._sess = with_mfa_session(base_sess, mfa_serial, mfa_token)
        else:
            self._sess = base_session

        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        self._pool = ThreadPoolExecutor(max_workers=max_workers)

        if request_config is None:
            self._request_config = RequestConfig()
        else:
            self._request_config = request_config

        if circuit_config is None:
            self._circuit_config = CircuitConfig()
        else:
            self._circuit_config = circuit_config

        # Circuit breaker
        self._circuit_failures = 0  # 連続失敗カウント
        self._circuit_open_until = 0  # サーキットオープン中の終了時刻（ミリ秒）
        self._connect()

    def _connect(self):
        # boto3の短期間再試行ポリシーを設定
        cfg = Config(
            retries={
                "max_attempts": self._request_config.max_attempts,
                "mode": "standard",
            },
            read_timeout=self._request_config.read_timeout,
            connect_timeout=self._request_config.connect_timeout,
        )

        self.sagemaker_runtime = self._sess.client("sagemaker-runtime", config=cfg)
        self.sagemaker = self._sess.client("sagemaker", config=cfg)
        try:
            self.sagemaker.describe_endpoint(EndpointName=self.endpoint)[
                "EndpointStatus"
            ]
        except Exception as e:
            logger.error(f"Failed to describe endpoint {self.endpoint}: {e}")
            raise

    def _record_success(self):
        with self._cb_lock:
            self._circuit_failures = 0

    def _record_failure(self):
        with self._cb_lock:
            # サーキットオープン中はカウントしない
            if now_ms() < self._circuit_open_until:
                return

            self._circuit_failures += 1

            # 失敗回数が閾値を超えたらサーキットオープン
            if self._circuit_failures >= self._circuit_config.threshold:
                self._circuit_open_until = (
                    now_ms() + self._circuit_config.cooldown_sec * 1000
                )
                self._circuit_failures = 0
                logger.warning(
                    "Circuit OPEN for %ss (endpoint=%s)",
                    self._circuit_config.cooldown_sec,
                    self.endpoint,
                )

    def _check_circuit(self):
        """サーキットブレーカーの状態を確認。オープン中なら例外を投げ、リクエストを拒否する"""

        with self._cb_lock:
            if now_ms() < self._circuit_open_until:
                remain = max(0, self._circuit_open_until - now_ms())
                raise YomiTokuInvokeError(
                    f"Circuit open; retry after ~{remain // 1000}s"
                )

    def _invoke_one(self, payload):
        self._check_circuit()
        try:
            resp = self.sagemaker_runtime.invoke_endpoint(
                EndpointName=self.endpoint,
                ContentType=payload.content_type,
                Body=payload.body,
            )
            raw = resp.get("Body").read()
            text = (
                raw.decode("utf-8", errors="replace")
                if isinstance(raw, (bytes, bytearray))
                else raw
            )
            data = json.loads(text)
            logger.info(f"{payload.source_name} [page {payload.index}] analyzed.")
            self._record_success()
            return InvokeResult(
                index=payload.index,
                raw_dict=data,
            )
        except BotoCoreError as e:
            self._record_failure()
            raise YomiTokuInvokeError(
                f"AWS SDK error during invoke for page {payload.index}"
            ) from e
        except ClientError as e:
            code = int(
                e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) or 0
            )
            if code in (429, 500, 502, 503, 504):
                self._record_failure()
            raise YomiTokuInvokeError(
                f"SageMaker invoke failed ({code}) for page {payload.index}: {e}"
            ) from e
        except json.JSONDecodeError as e:
            self._record_failure()
            raise YomiTokuInvokeError("Failed to decode JSON response") from e
        except Exception as e:
            # 予期しない例外は即座に再スロー（ここでサーキット状態を汚さない）
            raise e

    async def _ainvoke_one(
        self, payload: PagePayload, request_timeout: Optional[float] = None
    ):
        fut = self._loop.run_in_executor(self._pool, self._invoke_one, payload)
        timeout = (
            request_timeout
            if request_timeout is not None
            else (self._request_config.read_timeout + 5)
        )

        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self._record_failure()
            raise YomiTokuInvokeError(
                f"Request timeout for page {payload.index} (>{timeout}s)"
            )

    async def analyze_async(
        self,
        path_img: str,
        dpi: int = 200,
        page_index: Union[None, int, list] = None,
        request_timeout: Optional[float] = None,
        total_timeout: Optional[float] = None,
    ):
        # 画像データ読み込み
        content_type = guess_content_type(path_img)
        img_bytes, content_type = load_image_bytes(path_img, content_type, dpi)
        page_index = make_page_index(page_index, len(img_bytes))

        # 全ページ処理のタイムアウト設定
        if total_timeout is None:
            par = min(len(page_index), max(1, self._pool._max_workers))
            base = (
                request_timeout
                if request_timeout is not None
                else self._request_config.read_timeout
            ) + 5
            total_timeout = base * math.ceil(len(page_index) / par) * 1.5

        # ページごとのペイロード作成
        payloads = [
            PagePayload(
                index=i,
                content_type=content_type,
                body=b,
                source_name=os.path.basename(path_img),
            )
            for i, b in enumerate(img_bytes)
            if i in page_index
        ]

        par = min(len(payloads), max(1, self._pool._max_workers))
        sem = asyncio.Semaphore(par)

        async def run_one(payload):
            async with sem:
                return await self._ainvoke_one(payload, request_timeout)

        tasks = [asyncio.create_task(run_one(payload)) for payload in payloads]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks), timeout=total_timeout
            )
        except asyncio.TimeoutError:
            for t in tasks:
                if not t.done():
                    t.cancel()
            self._record_failure()
            raise YomiTokuInvokeError(f"Analyze timeout (> {total_timeout}s)")
        except Exception as e:
            for t in tasks:
                if not t.done():
                    t.cancel()
            logger.exception("Analyze failed: %s", path_img)
            raise YomiTokuInvokeError(f"Analyze failed for {path_img}") from e

        if not results:
            raise YomiTokuInvokeError("No page results were returned.")

        # ページ順に整列
        results.sort(key=lambda r: r.index)
        merged_dict = _merge_results(results)
        return merged_dict

    async def analyze_batch_async(
        self,
        input_dir: str,
        output_dir: str,
        dpi: int = 200,
        page_index: Union[None, int, list] = None,
        request_timeout: Optional[float] = None,
        total_timeout: Optional[float] = None,
        overwrite: bool = False,
        log_path: Optional[str] = None,
    ):
        os.makedirs(output_dir, exist_ok=True)

        if log_path is None:
            log_path = Path(output_dir) / "process_log.jsonl"

        path_imgs = [
            str(p)
            for p in Path(input_dir).iterdir()
            if p.suffix.lower()[1:] in SUPPORT_INPUT_FORMAT
        ]

        log_lock = asyncio.Lock()  # ログ書き込みの衝突防止

        async def log_record(record: dict):
            """ログをJSON Lines形式で追記"""
            async with log_lock:
                with open(log_path, "a", encoding="utf-8") as lf:
                    lf.write(json.dumps(record, ensure_ascii=False) + "\n")

        async def process_one(path_img: str):
            ext = Path(path_img).suffix.lower().replace(".", "")
            stem = Path(path_img).stem
            output_path = Path(output_dir) / f"{stem}_{ext}.json"

            record = {
                "timestamp": datetime.now().isoformat(),
                "file_path": path_img,
                "output_path": str(output_path),
                "dpi": dpi,
                "executed": False,
                "success": False,
                "error": None,
            }

            if output_path.exists() and not overwrite:
                logger.info(f"Skipped (exists): {output_path.name}")
                record["executed"] = False
                record["success"] = True
                await log_record(record)
                return

            record["executed"] = True

            try:
                result = await self.analyze_async(
                    path_img,
                    dpi=dpi,
                    page_index=page_index,
                    request_timeout=request_timeout,
                    total_timeout=total_timeout,
                )
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved: {output_path.name}")
                record["success"] = True
            except Exception as e:
                logger.error(f"Failed: {path_img} ({e})")
                record["success"] = False
                record["error"] = f"{type(e).__name__}: {e}"
            finally:
                await log_record(record)

        sem = asyncio.Semaphore(self._pool._max_workers)

        async def run_with_limit(path_img):
            async with sem:
                await process_one(path_img)

        await asyncio.gather(*(run_with_limit(p) for p in path_imgs))

    def analyze(
        self,
        path_img: str,
        dpi: int = 200,
        page_index: Union[None, int, list] = None,
        request_timeout: Optional[float] = None,
        total_timeout: Optional[float] = None,
    ):
        return self._loop.run_until_complete(
            self.analyze_async(
                path_img,
                dpi,
                page_index,
                request_timeout,
                total_timeout,
            ),
        )

    def close(self):
        self._pool.shutdown(wait=True)
        logger.info("YomitokuClient closed.")

    def __enter__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.close()
        return False

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
