"""AstrBot 插件入口：注册三个语音识别适配器，并把插件配置里的密钥交给它们。

密钥统一填在插件配置页（AstrBot 支持 secret 打码），提供商配置里只留类型和 id，
这样面板里不会出现明文的 SecretId / SecretKey。
"""

from __future__ import annotations

from astrbot.api.star import Context, Star, register

from . import sources
from .sources.base import set_credentials

SECRET_FIELDS = ("tencent_secret_id", "tencent_secret_key", "doubao_api_key",
                 "xunfei_app_id", "xunfei_api_key", "xunfei_api_secret")


@register("astrbot_plugin_stt_compat", "void-HaoNan",
          "STT 提供商兼容（腾讯云 / 豆包 / 讯飞）", "0.1.1")
class SttCnPlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        try:
            config = context.get_config()
            values = {name: str(config.get(name) or "") for name in SECRET_FIELDS}
            set_credentials(values)
        except Exception:  # noqa: BLE001 - 读不到配置就退回提供商配置里的值
            pass
