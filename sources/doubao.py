"""豆包（火山引擎）大模型录音文件识别：X-Api-Key + volc.seedasr.auc，submit 后 query 轮询。"""

from __future__ import annotations

import asyncio
import base64
import json
import uuid

from astrbot.api import logger
from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.provider import STTProvider
from .registry import register_adapter

from .base import cred, log, read_audio

BASE = "https://openspeech.bytedance.com/api/v3/auc/bigmodel"
RESOURCE = "volc.seedasr.auc"


@register_adapter(
    "doubao_asr_file",
    "豆包（火山引擎）大模型录音文件识别（X-Api-Key）",
    provider_type=ProviderType.SPEECH_TO_TEXT,
    default_config_tmpl={"type": "doubao_asr_file", "enable": True,
                         "resource_id": RESOURCE, "timeout": 60},
    provider_display_name="豆包 ASR（录音文件）",
)
class ProviderDoubaoFile(STTProvider):
    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)
        self.config = provider_config or {}
        self.api_key = cred("doubao_api_key") or str(self.config.get("api_key") or "").strip()
        self.resource_id = str(self.config.get("resource_id") or RESOURCE)
        self.timeout = float(self.config.get("timeout") or 60)

    def _headers(self, request_id: str) -> dict:
        return {"X-Api-Key": self.api_key, "X-Api-Resource-Id": self.resource_id,
                "X-Api-Request-Id": request_id, "Content-Type": "application/json"}

    async def get_text(self, audio_url: str) -> str:
        import aiohttp

        if not self.api_key:
            raise ValueError("豆包 ASR 缺少 API Key")
        data = read_audio(audio_url)
        request_id = str(uuid.uuid4())
        payload = {"user": {"uid": "astrbot"},
                   "audio": {"format": "wav", "data": base64.b64encode(data).decode("ascii")},
                   "request": {"model_name": "bigmodel", "enable_itn": True,
                               "enable_punc": True, "show_utterances": True}}
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{BASE}/submit", headers=self._headers(request_id),
                                    data=json.dumps(payload).encode("utf-8")) as response:
                submit_body = await response.text()
                status = response.headers.get("X-Api-Status-Code", "")
            if status and status not in ("20000000", "20000001", "20000002"):
                raise RuntimeError(f"豆包 submit 失败 {status}: {submit_body[:200]}")
            for _ in range(int(self.timeout / 0.5)):
                await asyncio.sleep(0.5)
                async with session.post(f"{BASE}/query", headers=self._headers(request_id),
                                        data=b"{}") as response:
                    body = await response.text()
                    code = response.headers.get("X-Api-Status-Code", "")
                if code in ("20000000", ""):
                    result = (json.loads(body or "{}").get("result") or {})
                    text = result.get("text") or ""
                    if text:
                        log(f"豆包识别：{str(text)[:60]}")
                        return str(text).strip()
                elif code.startswith(("45", "55")):
                    raise RuntimeError(f"豆包 query 失败 {code}: {body[:200]}")
        raise TimeoutError("豆包 ASR 等待结果超时")
