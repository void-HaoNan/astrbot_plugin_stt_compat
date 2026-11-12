"""AstrBot 插件入口：注册语音识别适配器，并把插件配置里的密钥交给它们。

2026-11-12 修：以前用 `context.get_config()` 取密钥——那是 **AstrBot 全局配置**，
不是插件配置，所以拿到的永远是空值，运行时报「豆包 ASR 缺少 API Key」。
AstrBot 4.x 的正确做法是接收构造函数注入的 `config: AstrBotConfig`。
同时保留「按文件兜底」：万一注入的 config 缺字段，`sources/base.cred()` 会去读
`data/config/astrbot_plugin_stt_compat_config.json`。
"""

from __future__ import annotations

from astrbot.api import logger
from astrbot.api.star import Context, Star, register

from . import sources
from .sources.base import set_credentials

SECRET_FIELDS = ("tencent_secret_id", "tencent_secret_key", "doubao_api_key",
                 "xunfei_app_id", "xunfei_api_key", "xunfei_api_secret")


@register("astrbot_plugin_stt_compat", "void-HaoNan",
          "STT 提供商兼容（腾讯云 / 豆包 / 讯飞 / 流式）", "0.2.0")
class SttCnPlugin(Star):
    def __init__(self, context: Context, config=None) -> None:
        super().__init__(context)
        values: dict[str, str] = {}
        try:
            source = config if config is not None else {}
            values = {name: str(source.get(name) or "") for name in SECRET_FIELDS}
        except Exception as error:  # noqa: BLE001 - 配置读不到也要让插件起来
            logger.warning(f"[stt_cn] 读插件配置失败：{error}")
        set_credentials(values)
        missing = [name for name, value in values.items() if not value]
        if missing:
            logger.info(
                "[stt_cn] 以下密钥为空：%s（可在插件设置页填，或写进 "
                "data/config/astrbot_plugin_stt_compat_config.json）" % "、".join(missing))
        else:
            logger.info("[stt_cn] 密钥已就绪：%d 项" % len(values))
