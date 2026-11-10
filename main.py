"""AstrBot 插件入口：只负责把三个语音识别适配器注册进框架。

适配器本身在 sources/ 里，导入即注册（register_provider_adapter）。
装好之后 AstrBot 的「语音转文字」提供商类型里会出现：
- 腾讯云 ASR（极速版）
- 豆包 ASR（录音文件）
- 讯飞 ASR（录音文件）
"""

from __future__ import annotations

from astrbot.api.star import Context, Star, register

from . import sources  # noqa: F401 - 导入触发 provider 注册


@register("astrbot_plugin_stt_cn", "void-HaoNan",
          "把腾讯云、豆包、讯飞的录音文件识别接进 AstrBot 的 STT 提供商", "0.1.0")
class SttCnPlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
