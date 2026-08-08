import asyncio
import json
import math
import os
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from yomitoku_client.logger import set_logger
from yomitoku_client.utils import (
    load_pdf_to_bytes,
    load_tiff_to_bytes,
    make_page_index,
)

from .constants import SUPPORT_INPUT_FORMAT
from .exceptions import YomitokuInvokeError

logger = set_logger(__name__, "INFO")
JST = timezone(timedelta(hours=9), name="Asia/Tokyo")


def _resolve_img_arg(
    img: str | bytes | None,
    path_img: str | bytes | None,
) -> str | bytes:
    """Resolve the image argument, accepting the deprecated ``path_img`` alias.

    ``analyze``/``analyze_async`` originally took ``path_img``; it was renamed to
    ``img`` (which also accepts bytes). ``path_img`` is still accepted for
    backward compatibility but is deprecated.
    """
    if path_img is not None:
        warnings.warn(
            "The 'path_img' argument is deprecated and will be removed in a "
            "future release; use 'img' instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        if img is None:
            img = path_img
    if img is None:
        raise TypeError("analyze() missing required argument: 'img'")
    return img


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
    cooldown_time: int = 30  # サーキットオープン後のクールダウン時間（秒）


@dataclass
class RequestConfig:
    read_timeout: int = 60
    connect_timeout: int = 10
    max_retries: int = 3


def guess_content_type(img: str|bytes) -> str:
    if type(img) == str:
        _, ext = os.path.splitext(img)
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
    else:
        if img.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        if img.startswith(b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'):
            return 'image/png'
        if img.startswith(b'\x49\x49\x2a\x00'):
            return 'image/tiff'
        if img.startswith(b'\x4d\x4d\x00\x2a'):
            return 'image/tiff'
        if img.startswith(b'%PDF'):
            return 'application/pdf'
        raise ValueError(f"Unsupported image type")


def load_image_bytes(
    path_img: str|bytes,
    content_type: str,
    dpi=200,
) -> tuple[list[bytes], str]:
    if content_type == "application/pdf":
        img_bytes = load_pdf_to_bytes(path_img, dpi=dpi)
        # NOTE: PDFはページ分割・ラスター化してPNG化。以降のinvokeはimage/pngで送る
        content_type = "image/png"
    elif content_type == "image/tiff":
        img_bytes = load_tiff_to_bytes(path_img)
    elif isinstance(path_img, (str,)):
        with open(path_img, "rb") as f:
            img_bytes = [f.read()]
    else:
        img_bytes = [path_img]
    return img_bytes, content_type


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
        region: str | None = None,
        profile: str | None = None,
        max_workers: int = 4,
        request_config: RequestConfig | None = None,
        circuit_config: CircuitConfig | None = None,
    ):
        logger.info("YomitokuClient initialized")
        self.endpoint = endpoint
        self.region = region

        self._cb_lock = threading.Lock()

        self._sess = boto3.Session(region_name=region, profile_name=profile)

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
                "max_attempts": self._request_config.max_retries,
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
            logger.error("Failed to describe endpoint %s: %s", self.endpoint, e)
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
                    now_ms() + self._circuit_config.cooldown_time * 1000
                )
                self._circuit_failures = 0
                logger.warning(
                    "Circuit OPEN for %ss (endpoint=%s)",
                    self._circuit_config.cooldown_time,
                    self.endpoint,
                )

    def _check_circuit(self):
        """サーキットブレーカーの状態を確認。オープン中なら例外を投げ、リクエストを拒否する"""

        with self._cb_lock:
            if now_ms() < self._circuit_open_until:
                remain = max(0, self._circuit_open_until - now_ms())
                raise YomitokuInvokeError(
                    f"Circuit open; retry after ~{remain // 1000}s",
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
            logger.info(
                "%s [page %s] analyzed.",
                payload.source_name,
                payload.index,
            )
            self._record_success()
            return InvokeResult(
                index=payload.index,
                raw_dict=data,
            )
        except BotoCoreError as e:
            self._record_failure()
            raise YomitokuInvokeError(
                f"AWS SDK error during invoke for page {payload.index}",
            ) from e
        except ClientError as e:
            code = int(
                e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) or 0,
            )
            if code in (429, 500, 502, 503, 504):
                self._record_failure()
            raise YomitokuInvokeError(
                f"SageMaker invoke failed ({code}) for page {payload.index}: {e}",
            ) from e
        except json.JSONDecodeError as e:
            self._record_failure()
            raise YomitokuInvokeError("Failed to decode JSON response") from e
        except Exception as e:
            # 予期しない例外は即座に再スロー（ここでサーキット状態を汚さない）
            raise e

    async def _ainvoke_one(
        self,
        payload: PagePayload,
        request_timeout: float | None = None,
    ):
        fut = self._loop.run_in_executor(self._pool, self._invoke_one, payload)
        timeout = (
            request_timeout
            if request_timeout is not None
            else (self._request_config.read_timeout + 5)
        )

        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError as e:
            self._record_failure()
            raise YomitokuInvokeError(
                f"Request timeout for page {payload.index} (>{timeout}s)",
            ) from e

    async def analyze_async(
        self,
        img: str | bytes | None = None,
        dpi: int = 200,
        page_index: None | int | list = None,
        request_timeout: float | None = None,
        total_timeout: float | None = None,
        *,
        path_img: str | bytes | None = None,
        content_type: str|None = None,
    ):
        # 後方互換: 引数名は path_img から img に変更された。旧名 path_img も
        # 受け付けるが deprecated 扱いとする。
        img = _resolve_img_arg(img, path_img)

        # 画像データ読み込み
        if content_type is None:
            content_type = guess_content_type(img)
        if type(img) == bytes:
            source_name = '<bytes>'
        else:
            source_name = img
        img_bytes, content_type = load_image_bytes(img, content_type, dpi)
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
                source_name=os.path.basename(source_name),
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
                asyncio.gather(*tasks),
                timeout=total_timeout,
            )
        except asyncio.TimeoutError as e:
            for t in tasks:
                if not t.done():
                    t.cancel()
            self._record_failure()
            raise YomitokuInvokeError(f"Analyze timeout (> {total_timeout}s)") from e
        except Exception as e:
            for t in tasks:
                if not t.done():
                    t.cancel()
            logger.exception("Analyze failed: %s", source_name)
            raise YomitokuInvokeError(f"Analyze failed for {source_name}") from e

        if not results:
            raise YomitokuInvokeError("No page results were returned.")

        # ページ順に整列
        results.sort(key=lambda r: r.index)
        merged_dict = _merge_results(results)
        return merged_dict

    async def analyze_batch_async(
        self,
        input_dir: str,
        output_dir: str,
        dpi: int = 200,
        page_index: None | int | list = None,
        request_timeout: float | None = None,
        total_timeout: float | None = None,
        overwrite: bool = False,
        log_path: str | None = None,
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
                "timestamp": datetime.now(JST).isoformat(),
                "file_path": path_img,
                "output_path": str(output_path),
                "dpi": dpi,
                "executed": False,
                "success": False,
                "error": None,
            }

            if output_path.exists() and not overwrite:
                logger.info("Skipped (exists): %s", output_path.name)
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
                logger.info("Saved: %s", output_path.name)
                record["success"] = True
            except Exception as e:
                logger.error("Failed: %s (%s)", path_img, e)
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
        img: str | bytes | None = None,
        dpi: int = 200,
        page_index: None | int | list = None,
        request_timeout: float | None = None,
        total_timeout: float | None = None,
        **kwargs
    ):
        return self._loop.run_until_complete(
            self.analyze_async(
                img,
                dpi,
                page_index,
                request_timeout,
                total_timeout,
                **kwargs
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
