"""
后端调用火山 OpenAPI，例如启动 AI
使用VOLC-AK/SK
"""

import json
import hashlib
import hmac
from datetime import datetime, timezone


def hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(
        key,
        msg.encode("utf-8"),
        hashlib.sha256,
    ).digest()


def key_map(lower_key: str, headers: dict) -> str:
    for key in headers:
        if key.lower() == lower_key:
            return key
    return lower_key


class Signer:
    def __init__(
        self,
        request_data: dict,
        service: str,
        region: str = "cn-north-1",
    ):
        self.method = request_data.get("method", "POST").upper()
        self.path = request_data.get("path", "/")
        self.params = request_data.get("params", {})
        self.headers = request_data.get("headers", {})
        self.body = request_data.get("body", {})
        self.service = service
        self.region = region

    def add_authorization(self, account_config: dict) -> None:
        ak = account_config.get("accessKeyId")
        sk = account_config.get("secretKey")

        # 1. 添加请求时间
        now = datetime.now(timezone.utc)
        date = now.strftime("%Y%m%d")
        ts = now.strftime("%Y%m%dT%H%M%SZ")
        self.headers["X-Date"] = ts

        # 2. 计算请求正文的摘要
        body_str = json.dumps(self.body) if self.body else ""
        body_hash = hashlib.sha256(
            body_str.encode("utf-8")
        ).hexdigest()
        self.headers["X-Content-Sha256"] = body_hash

        # 3. 整理参与签名的请求头
        signed_headers = sorted(
            key.lower()
            for key in self.headers
            if key.lower() in [
                "content-type",
                "host",
                "x-content-sha256",
                "x-date",
            ]
        )

        canonical_headers = "".join(
            f"{key}:{self.headers[key_map(key, self.headers)].strip()}\n"
            for key in signed_headers
        )
        signed_headers_str = ";".join(signed_headers)

        # 4. 整理 URL 查询参数
        query_str = "&".join(
            f"{key}={value}"
            for key, value in sorted(self.params.items())
        )

        # 5. 按规定顺序组合请求信息
        canonical_request = (
            f"{self.method}\n{self.path}\n{query_str}\n"
            f"{canonical_headers}\n{signed_headers_str}\n{body_hash}"
        )

        credential_scope = (
            f"{date}/{self.region}/{self.service}/request"
        )
        request_hash = hashlib.sha256(
            canonical_request.encode("utf-8")
        ).hexdigest()

        string_to_sign = (
            f"HMAC-SHA256\n{ts}\n{credential_scope}\n{request_hash}"
        )

        # 6. 使用 SK 计算签名
        k_date = hmac_sha256(sk.encode("utf-8"), date)
        k_region = hmac_sha256(k_date, self.region)
        k_service = hmac_sha256(k_region, self.service)
        k_signing = hmac_sha256(k_service, "request")

        signature = hmac.new(
            k_signing,
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # 7. 将鉴权信息写入请求头
        self.headers["Authorization"] = (
            f"HMAC-SHA256 Credential={ak}/{credential_scope}, "
            f"SignedHeaders={signed_headers_str}, Signature={signature}"
        )