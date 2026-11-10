"""公共工具：读音频、签名、从 JSON 里按路径取字段。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import wave

from astrbot.api import logger


def read_audio(path: str) -> bytes:
    """读音频文件；silk/amr 这类格式要求 AstrBot 先转成 wav，这里只做兜底提示。"""
    if not path or not os.path.isfile(path):
        raise FileNotFoundError(f"音频文件不存在：{path}")
    with open(path, "rb") as handle:
        data = handle.read()
    if not data:
        raise ValueError("音频文件是空的")
    return data


def wav_seconds(data: bytes) -> float:
    """wav 时长（秒）；不是 wav 就返回 0，部分接口要求带 duration。"""
    try:
        import io

        with wave.open(io.BytesIO(data)) as speaker:
            rate = speaker.getframerate() or 1
            return speaker.getnframes() / float(rate)
    except Exception:  # noqa: BLE001 - 非 wav 时不当错误
        return 0.0


def json_path(data, path: str):
    """按 a.b.0.c 取值；取不到返回 None。"""
    current = data
    for part in str(path or "").split("."):
        if not part:
            continue
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def tencent_query(params: dict) -> str:
    items = sorted((str(k), str(v)) for k, v in params.items() if v not in (None, ""))
    return "&".join(f"{k}={v}" for k, v in items)


def sign_tencent(secret_key: str, host: str, path: str, params: dict) -> str:
    """签名：把排序后的参数串用 HMAC-SHA1 算签名，再 base64 整个 URL。"""
    sign_text = tencent_query(params)
    digest = hmac.new(secret_key.encode("utf-8"), sign_text.encode("utf-8"), hashlib.sha1).digest()
    signature = base64.b64encode(digest).decode("utf-8")
    full = f"{host}{path}?{sign_text}&signature={signature}"
    return base64.b64encode(full.encode("utf-8")).decode("utf-8")


def sign_xunfei(app_id: str, secret_key: str, timestamp: str) -> str:
    """讯飞 LFASR 的签名：md5(appid+ts) 再 HMAC-SHA1，最后 base64。"""
    base_text = hashlib.md5((app_id + timestamp).encode("utf-8")).hexdigest()
    digest = hmac.new(secret_key.encode("utf-8"), base_text.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def dump(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)[:300]
    except Exception:  # noqa: BLE001 - 只用于日志
        return str(obj)[:300]


def log(message: str) -> None:
    logger.info("[stt_cn] " + message)


#: 插件配置里填的密钥（AstrBot 插件配置支持 secret 打码），提供商配置里可以不再存明文
CREDENTIALS: dict = {}


def set_credentials(values: dict) -> None:
    CREDENTIALS.clear()
    CREDENTIALS.update(values or {})


def cred(*names: str) -> str:
    for name in names:
        value = str(CREDENTIALS.get(name) or '').strip()
        if value:
            return value
    return ''
