import asyncio
import boto3
import os
import math
import json
import time

from dataclasses import dataclass
from botocore.exceptions import BotoCoreError, ClientError
from botocore.config import Config

from concurrent.futures import ThreadPoolExecutor
from typing import Union, Optional, Tuple

from yomitoku_client.utils import (
    load_pdf_to_bytes,
    load_tiff_to_bytes,
    make_page_index,
)
from yomitoku_client.parsers import parse_pydantic_model
from yomitoku_client.logger import set_logger


logger = set_logger(__name__, "INFO")


class YomiTokuError(Exception):
    pass


class YomiTokuInvokeError(YomiTokuError):
    pass


class CircuitOpenError(YomiTokuError):
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
    path_img: str, content_type: str, dpi=200
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
    base_sess: boto3.Session, mfa_serial: str, token: str
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


def _merge_results(self, results: list[InvokeResult]) -> dict:
    base = dict(results[0].raw_dict)
    key = "result"
    if not isinstance(base.get(key), list):
        return base
    for r in results[1:]:
        items = r.raw_dict.get(key, [])
        if isinstance(items, list):
            base[key].extend(items)
    return base


class YomitokuClient:
    def __init__(
        self,
        endpoint: str,
        region: str,
        mfa_serial: str = None,
        mfa_token: str = None,
        max_workers: int = 4,
        read_timeout: int = 60,
        connect_timeout: int = 10,
        max_attempts: int = 5,
        backoff_base: float = 0.2,
        circuit_threshold: int = 5,
        circuit_cooldown_sec: int = 30,
    ):
        logger.info("YomitokuClient initialized")
        self.endpoint = endpoint
        self.region = region

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

        self.read_timeout = read_timeout
        self.connect_timeout = connect_timeout
        self.max_attempts = max_attempts

        # Circuit breaker (超過エラー耐性)
        self._circuit_failures = 0
        self._circuit_open_until = 0
        self._backoff_base = backoff_base
        self._circuit_threshold = circuit_threshold
        self._circuit_cooldown_sec = circuit_cooldown_sec

        self._connect()

    def _connect(self):
        cfg = Config(
            retries={"max_attempts": self.max_attempts, "mode": "standard"},
            read_timeout=self.read_timeout,
            connect_timeout=self.connect_timeout,
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
        self._circuit_failures = 0

    def _record_failure(self):
        self._circuit_failures += 1
        if self._circuit_failures >= self._circuit_threshold:
            self._circuit_open_until = now_ms() + self._circuit_cooldown_sec * 1000
            self._circuit_failures = 0

    def _check_circuit(self):
        if now_ms() < self._circuit_open_until:
            raise CircuitOpenError("Circuit is open; temporarily rejecting requests.")

    def _invoke_one(self, payload):
        attempt = 0
        last_err: Optional[Exception] = None
        while attempt < 5:
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
            except (ClientError, BotoCoreError, json.JSONDecodeError, Exception) as e:
                last_err = e
                self._record_failure()
                delay = self._backoff_base * (2**attempt) + (0.01 * (attempt + 1))
                time.sleep(min(delay, 3.0))
                attempt += 1
        raise YomiTokuInvokeError(f"Invoke failed for page {payload.index}: {last_err}")

    async def _ainvoke_one(
        self, payload: PagePayload, request_timeout: Optional[float] = None
    ):
        fut = self._loop.run_in_executor(self._pool, self._invoke_one, payload)
        timeout = (
            request_timeout if request_timeout is not None else (self.read_timeout + 5)
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
                request_timeout if request_timeout is not None else self.read_timeout
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
        merged_dict = _merge_results(self, results)
        return parse_pydantic_model(merged_dict)

    def __call__(
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
            )
        )

    def close(self):
        self._pool.shutdown(wait=True)
        logger.info("YomitokuClient closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
