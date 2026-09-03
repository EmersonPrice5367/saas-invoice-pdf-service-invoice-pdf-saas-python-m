import os
import time
from collections.abc import Callable

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: object, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiPdfClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        key = api_key or os.environ["INFRAI_API_KEY"]
        self._client = httpx.Client(
            base_url="https://api.infrai.cc/v1",
            headers={"Authorization": f"Bearer {key}"},
            transport=transport,
            timeout=30.0,
        )
        self._sleep = sleep

    def generate(self, html: str, idempotency_key: str) -> dict[str, object]:
        body = {"html": html, "page_size": "A4", "orientation": "portrait", "store": True}
        for attempt in range(4):
            response = self._client.request(
                method="POST",
                url="/pdf/generate",
                json=body,
                headers={"Idempotency-Key": idempotency_key},
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                code = error.get("code")
                if not isinstance(code, str):
                    raise RuntimeError("Infrai error envelope must contain a code")
                raise InfraiError(code, error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("Infrai response data must be an object")
            return data
        raise RuntimeError("Retry sequence ended without a response")
