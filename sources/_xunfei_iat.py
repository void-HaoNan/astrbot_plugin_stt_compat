"""讯飞语音听写大模型（中英）V2.0 客户端。

接口：wss://iat.cn-huabei-1.xf-yun.com/v1
鉴权：appid + apiKey + apiSecret 做 HMAC-SHA256 签名，拼在 URL 上
音频：16k / 16bit / 单声道 PCM，最长 60 秒

你需要在讯飞开放平台做两件事（都要在控制台点，我没法替你注册）：
  1. 注册登录 https://console.xfyun.cn/app/myapp
  2. 创建应用 → 添加「语音听写大模型（中英）V2.0」服务 → 拿到 AppID / APIKey / APISecret

拿到后填进这里（或者我加到设置面板里）：
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import ssl
import time
import urllib.parse
from datetime import UTC, datetime

HOST = "iat.cn-huabei-1.xf-yun.com"
PATH = "/v1"
URL = "wss://" + HOST + PATH


def auth_url(api_key: str, api_secret: str) -> str:
    """按讯飞文档生成带签名的 wss 地址。"""
    date = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
    signature_origin = f"host: {HOST}\ndate: {date}\nGET {PATH} HTTP/1.1"
    signature_sha = hmac.new(api_secret.encode("utf-8"),
                             signature_origin.encode("utf-8"),
                             hashlib.sha256).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    authorization_origin = (f'api_key="{api_key}", algorithm="hmac-sha256", '
                            f'headers="host date request-line", signature="{signature}"')
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
    return URL + "?" + urllib.parse.urlencode({
        "host": HOST, "date": date, "authorization": authorization})


def transcribe(app_id: str, api_key: str, api_secret: str, pcm: bytes,
               hotwords: list | None = None, replaces: list | None = None,
               recent: list | None = None, timeout: float = 30.0,
               chunk: int = 2048, chunk_delay: float = 0.01) -> str:
    """把一段 16k/16bit/单声道 PCM 丢进去，返回识别文字。

    hotwords 形如 [("星露谷物语", 1.0)]，replaces 形如 [("新漏古", "星露谷")]，
    recent 是近期识别过的句子（给模型当语境）。
    """
    import websocket  # websocket-client，项目里已经有了

    context = {}
    if hotwords or replaces:
        bias = {}
        if hotwords:
            bias["hotword"] = [{"text": word, "weight": float(weight)}
                               for word, weight in hotwords]
        if replaces:
            bias["replaces"] = [{"from": src, "to": dst} for src, dst in replaces]
        context["bias"] = bias
    if recent:
        context["recent"] = {"history": [{"seq": index + 1, "text": text}
                                         for index, text in enumerate(recent[-5:])]}

    parameter = {
        "iat": {
            "domain": "spark_asr_v2",
            "language": "zh_cn",
            "accent": "mandarin",
            "dwa": "wpgs",          # 动态修正，能出中间结果
            "result": {"encoding": "utf8", "compress": "raw", "format": "json"},
        }
    }
    if context:
        parameter["iat"]["context"] = json.dumps(context, ensure_ascii=False)

    ws = websocket.create_connection(
        auth_url(api_key, api_secret), timeout=timeout,
        sslopt={"cert_reqs": ssl.CERT_NONE})
    # wpgs 动态修正：apd=追加、rpl=用 rg=[起,止] 替换已有的若干段。
    # 以前这里只会 append，导致「他他占他占了八…」这种中间结果全堆在一起。
    segments: dict = {}
    try:
        # 首帧
        first = {
            "header": {"app_id": app_id, "status": 0},
            "parameter": parameter,
            "payload": {"audio": {"encoding": "raw", "sample_rate": 16000,
                                  "channels": 1, "bit_depth": 16, "seq": 1,
                                  "status": 0, "audio": ""}},
        }
        ws.send(json.dumps(first))

        frame = max(1024, int(chunk))
        seq = 2
        sent = 0
        while sent < len(pcm):
            chunk_bytes = pcm[sent: sent + frame]
            sent += len(chunk_bytes)
            status = 2 if sent >= len(pcm) else 1
            ws.send(json.dumps({
                "header": {"app_id": app_id, "status": status},
                "payload": {"audio": {"encoding": "raw", "sample_rate": 16000,
                                      "channels": 1, "bit_depth": 16, "seq": seq,
                                      "status": status,
                                      "audio": base64.b64encode(chunk_bytes).decode("utf-8")}},
            }))
            seq += 1
            # 文档建议按 40ms 一包推（模拟实时），但整段音频一次性发完更快；
            # 延迟实测差好几秒，所以这里把间隔做成可调，默认很小。
            if chunk_delay > 0:
                time.sleep(chunk_delay)

        while True:
            raw = ws.recv()
            if not raw:
                break
            data = json.loads(raw)
            header = data.get("header") or {}
            if header.get("code") not in (None, 0):
                raise RuntimeError(f"讯飞返回错误 {header.get('code')}：{header.get('message')}")
            result = (data.get("payload") or {}).get("result") or {}
            text_b64 = result.get("text")
            if text_b64:
                text_json = json.loads(base64.b64decode(text_b64).decode("utf-8"))
                sn = int(text_json.get("sn") or 0)
                words = "".join(cw.get("w", "")
                                for ws_item in text_json.get("ws") or []
                                for cw in ws_item.get("cw") or [])
                pgs = str(text_json.get("pgs") or "apd")
                if pgs == "rpl":
                    # rg=[起, 止]：把这一段整体替换成这一帧的新文本
                    span = text_json.get("rg") or []
                    if len(span) == 2:
                        for old in range(int(span[0]), int(span[1]) + 1):
                            segments.pop(old, None)
                if sn and words:
                    segments[sn] = words
            if result.get("status") == 2 or header.get("status") == 2:
                break
    finally:
        try:
            ws.close()
        except Exception as error:  # noqa: BLE001 - 关连接失败不影响结果
            print(f"[xunfei] 关连接失败：{str(error)[:60]}", flush=True)
    return "".join(segments[key] for key in sorted(segments)).strip()


def read_wav_pcm(path: str) -> bytes:
    """读 16k 单声道 wav，取出裸 PCM。"""
    import wave

    with wave.open(path, "rb") as handle:
        if handle.getframerate() != 16000 or handle.getnchannels() != 1:
            raise ValueError(f"音频要 16k 单声道，现在是 {handle.getframerate()} Hz / "
                             f"{handle.getnchannels()} 声道")
        return handle.readframes(handle.getnframes())
