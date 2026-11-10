"""讯飞语音听写大模型（中英）V2.0：WebSocket 协议。

AstrBot 的 STT 接口给的是整段音频，这里把整段 PCM 一次性推完再收尾，
返回最终文字；这样同一个认证信息既能给实时链路用，也能当文件识别用。
"""

from __future__ import annotations

import asyncio

from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.provider import STTProvider
from astrbot.core.provider.register import register_provider_adapter

from ._xunfei_iat import read_wav_pcm, transcribe


@register_provider_adapter(
    "xunfei_iat_ws",
    "讯飞语音听写大模型 V2.0（WebSocket）",
    provider_type=ProviderType.SPEECH_TO_TEXT,
    default_config_tmpl={"type": "xunfei_iat_ws", "enable": True,
                         "app_id": "", "api_key": "", "timeout": 30},
    provider_display_name="讯飞 ASR（听写 V2.0）",
)
class ProviderXunfeiIat(STTProvider):
    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)
        self.config = provider_config or {}
        self.app_id = str(self.config.get("app_id") or "").strip()
        raw = str(self.config.get("api_key") or "").strip()
        if ":" in raw:
            self.api_key, self.api_secret = [part.strip() for part in raw.split(":", 1)]
        else:
            self.api_key = raw
            self.api_secret = ""
        self.timeout = float(self.config.get("timeout") or 30)

    async def get_text(self, audio_url: str) -> str:
        if not (self.app_id and self.api_key and self.api_secret):
            raise ValueError("讯飞 ASR 缺少 AppID / APIKey / APISecret")
        pcm = read_wav_pcm(audio_url)
        return await asyncio.to_thread(transcribe, self.app_id, self.api_key,
                                       self.api_secret, pcm, None, None, None,
                                       self.timeout)
