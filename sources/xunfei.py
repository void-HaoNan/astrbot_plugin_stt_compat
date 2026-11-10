"""讯飞语音听写大模型（中英）V2.0：WebSocket 协议。

用户需要填三个值：APPID、APIKey、APISecret。
"""

from __future__ import annotations

import asyncio

from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.provider import STTProvider
from astrbot.core.provider.register import register_provider_adapter

from ._xunfei_iat import read_wav_pcm, transcribe
from .base import cred


@register_provider_adapter(
    "xunfei_iat_ws",
    "讯飞语音听写 V2.0（只填 AppID / APIKey / APISecret）",
    provider_type=ProviderType.SPEECH_TO_TEXT,
    default_config_tmpl={"type": "xunfei_iat_ws", "enable": True,
                         "app_id": {"description": "讯飞 AppID", "hint": "在 console.xfyun.cn 我的应用 → 应用详情里复制 APPID（8 位左右）。", "type": "string", "secret": False, "default": ""},
                         "api_key": {"description": "讯飞 APIKey", "hint": "同一个应用里的 APIKey，和 APISecret 配对做 HMAC-SHA256 签名；不要把 APPID 复制到这里。", "type": "string", "secret": True, "default": ""},
                         "api_secret": {"description": "讯飞 APISecret", "hint": "同一个应用里的 APISecret，只显示一次；填错了会报 appId illegal 或 26610。", "type": "string", "secret": True, "default": ""},
                         "timeout": 30},
    provider_display_name="讯飞 ASR（听写 V2.0）",
)
class ProviderXunfeiIat(STTProvider):
    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)
        self.config = provider_config or {}
        self.app_id = cred("xunfei_app_id") or str(self.config.get("app_id") or "").strip()
        self.api_key = cred("xunfei_api_key") or str(self.config.get("api_key") or "").strip()
        self.api_secret = cred("xunfei_api_secret") or str(self.config.get("api_secret") or "").strip()
        # 兼容早期 api_key="APIKey:APISecret" 的写法
        raw = str(self.config.get("api_key") or "").strip()
        if raw and ":" in raw and not self.api_secret:
            self.api_key, self.api_secret = [part.strip() for part in raw.split(":", 1)]
        self.timeout = float(self.config.get("timeout") or 30)

    async def get_text(self, audio_url: str) -> str:
        if not (self.app_id and self.api_key and self.api_secret):
            raise ValueError("讯飞 ASR 需要填 AppID、APIKey、APISecret")
        pcm = read_wav_pcm(audio_url)
        return await asyncio.to_thread(transcribe, self.app_id, self.api_key,
                                       self.api_secret, pcm, None, None, None,
                                       self.timeout)
