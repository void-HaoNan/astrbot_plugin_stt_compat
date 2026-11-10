"""腾讯云 ASR：SentenceRecognition（API 3.0，TC3-HMAC-SHA256 签名）。

凭证只有 SecretId / SecretKey（访问管理 → API 密钥管理），不需要 AppID。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.provider import STTProvider
from astrbot.core.provider.register import register_provider_adapter

from .base import log, read_audio

HOST = "asr.tencentcloudapi.com"
SERVICE = "asr"
ACTION = "SentenceRecognition"
VERSION = "2019-06-14"
REGION = "ap-shanghai"


def _hmac(key: bytes, text: str) -> bytes:
    return hmac.new(key, text.encode("utf-8"), hashlib.sha256).digest()


def tc3_headers(secret_id: str, secret_key: str, payload: bytes, now: int | None = None) -> dict:
    """算 TC3-HMAC-SHA256 签名，返回请求头。"""
    timestamp = int(now if now is not None else time.time())
    date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
    signed_headers = "content-type;host"
    canonical_headers = ("content-type:application/json; charset=utf-8\n"
                         f"host:{HOST}\n")
    hashed_payload = hashlib.sha256(payload).hexdigest()
    canonical_request = (f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{hashed_payload}")
    scope = f"{date}/{SERVICE}/tc3_request"
    string_to_sign = ("TC3-HMAC-SHA256\n" + str(timestamp) + "\n" + scope + "\n" +
                      hashlib.sha256(canonical_request.encode("utf-8")).hexdigest())
    secret_date = _hmac(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = _hmac(secret_date, SERVICE)
    secret_signing = _hmac(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (f"TC3-HMAC-SHA256 Credential={secret_id}/{scope}, "
                     f"SignedHeaders={signed_headers}, Signature={signature}")
    return {"Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": HOST,
            "X-TC-Action": ACTION,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": VERSION,
            "X-TC-Region": REGION}


@register_provider_adapter(
    "tencent_asr_api3",
    "腾讯云语音识别（SentenceRecognition / API 3.0）",
    provider_type=ProviderType.SPEECH_TO_TEXT,
    default_config_tmpl={"type": "tencent_asr_api3", "enable": True,
                         "api_key": "", "backup_api_key": "",
                         "engine_model_type": "16k_zh", "timeout": 30},
    provider_display_name="腾讯云 ASR（API 3.0）",
)
class ProviderTencentAPI3(STTProvider):
    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)
        self.config = provider_config or {}
        raw = str(self.config.get("api_key") or "").strip()
        if ":" in raw:
            self.secret_id, self.secret_key = [part.strip() for part in raw.split(":", 1)]
        else:
            self.secret_id = raw
            self.secret_key = str(self.config.get("backup_api_key") or "").strip()
        self.engine = str(self.config.get("engine_model_type") or "16k_zh")
        self.timeout = float(self.config.get("timeout") or 30)

    async def get_text(self, audio_url: str) -> str:
        import aiohttp

        if not (self.secret_id and self.secret_key):
            raise ValueError("腾讯云 ASR 缺少 SecretId / SecretKey")
        data = read_audio(audio_url)
        payload = json.dumps({
            "EngSerViceType": self.engine,
            "SourceType": 1,
            "VoiceFormat": "wav",
            "Data": base64.b64encode(data).decode("ascii"),
            "ProjectId": 0,
            "SubServiceType": 2,
        }).encode("utf-8")
        headers = tc3_headers(self.secret_id, self.secret_key, payload)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"https://{HOST}", data=payload, headers=headers) as response:
                body = await response.text()
        result = json.loads(body or "{}")
        response_data = result.get("Response") or {}
        error = response_data.get("Error")
        if error:
            raise RuntimeError(f"腾讯云 ASR 失败：{error.get('Code')} {error.get('Message')}")
        text = str(response_data.get("Result") or "").strip()
        log(f"腾讯云识别：{text[:60]}")
        return text
