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

#: 控制台设置里的对应键：插件配置缺字段时从这里补（这份不会被 AstrBot 覆盖）
CONSOLE_KEYS = {
    "tencent_secret_id": "account.tencent_secret_id",
    "tencent_secret_key": "account.tencent_secret_key",
    "tencent_app_id": "account.tencent_app_id",
    "doubao_api_key": "account.doubao_api_key",
    "xunfei_app_id": "account.xunfei_app_id",
    "xunfei_api_key": "account.xunfei_api_key",
    "xunfei_api_secret": "account.xunfei_api_secret",
}


def _data_dirs() -> list:
    """控制台 data 目录的候选（和 douyin_live 插件的解析顺序一致，按优先级）。"""
    import os

    dirs = []
    env = str(os.environ.get("PYMSS_DATA_DIR") or "").strip()
    if env:
        dirs.append(env)
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "hub_dir.txt"), "r", encoding="utf-8-sig") as handle:
            hub_root = handle.read().strip().strip('"')
        if hub_root:
            dirs.append(os.path.join(hub_root, "data"))
    except OSError:
        pass
    dirs.append(os.path.join(os.path.expanduser("~"), "data"))   # 老机器兜底
    return dirs


def console_settings() -> dict:
    """读控制台的 settings.json（只读，读不到返回空）。

    AstrBot 的 data 在用户目录的 data 下，但**控制台的设置**在包内 data 目录，
    两个不是一回事：直接读 ~/data/settings.json 永远读不到（2026-11-14 踩过）。
    """
    import json
    import os

    for base in _data_dirs():
        path = os.path.join(base, "settings.json")
        try:
            with open(path, encoding="utf-8-sig") as handle:
                data = json.load(handle)
            if isinstance(data, dict) and data:
                return data
        except Exception:  # noqa: BLE001 - 这个目录没有就试下一个
            continue
    return {}


def fill_from_console(values: dict) -> list:
    """把空着的字段用控制台设置补上，返回补了哪些字段名。"""
    filled = []
    settings = console_settings()
    for name, key in CONSOLE_KEYS.items():
        if str(values.get(name) or "").strip():
            continue
        value = str(settings.get(key) or "").strip()
        if value:
            values[name] = value
            filled.append(name)
    return filled


#: 插件设置里要读的字段：三个密钥 + 三家各自的 AppID（AppID 不算密钥，但一起读省事）
SECRET_FIELDS = ("tencent_secret_id", "tencent_secret_key", "doubao_api_key",
                 "xunfei_app_id", "xunfei_api_key", "xunfei_api_secret",
                 "tencent_app_id")


@register("astrbot_plugin_stt_compat", "void-HaoNan",
          "STT 提供商兼容（腾讯云 / 豆包 / 讯飞 / 流式）", "0.2.3")
class SttCnPlugin(Star):
    def __init__(self, context: Context, config=None) -> None:
        super().__init__(context)
        values: dict[str, str] = {}
        try:
            source = config if config is not None else {}
            values = {name: str(source.get(name) or "") for name in SECRET_FIELDS}
        except Exception as error:  # noqa: BLE001 - 配置读不到也要让插件起来
            logger.warning(f"[stt_cn] 读插件配置失败：{error}")
        try:
            filled = fill_from_console(values)
            if filled:
                logger.info("[stt_cn] 以下字段取的控制台设置：%s" % "、".join(filled))
        except Exception as error:  # noqa: BLE001 - 兜底失败不影响插件
            logger.warning(f"[stt_cn] 读控制台设置失败：{error}")
        set_credentials(values)
        missing = [name for name, value in values.items() if not value]
        if missing:
            logger.info(
                "[stt_cn] 以下密钥为空：%s（可在插件设置页填，或写进 "
                "data/config/astrbot_plugin_stt_compat_config.json）" % "、".join(missing))
        else:
            logger.info("[stt_cn] 密钥已就绪：%d 项" % len(values))
