"""纯函数校验：腾讯 TC3 签名、讯飞签名、wav 时长。不联网。"""

import base64
import hashlib
import hmac
import io
import os
import sys
import wave

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def test_tc3_signature():
    from sources.tencent import tc3_headers

    payload = b'{"Action":"test"}'
    headers = tc3_headers("AKIDTEST", "SECRETTEST", payload, now=1700000000)
    assert headers["X-TC-Action"] == "SentenceRecognition"
    assert headers["X-TC-Region"] == "ap-shanghai"
    assert headers["Authorization"].startswith("TC3-HMAC-SHA256 Credential=AKIDTEST/")

    # 同样的输入必须得到同样的签名（稳定、可复现）
    again = tc3_headers("AKIDTEST", "SECRETTEST", payload, now=1700000000)
    assert again["Authorization"] == headers["Authorization"]


def test_xunfei_signature():
    from sources._xunfei_iat import auth_url

    url = auth_url("APIKEY", "APISECRET")
    assert url.startswith("wss://iat.cn-huabei-1.xf-yun.com/v1?")
    for part in ("authorization=", "date=", "host="):
        assert part in url


def test_wav_seconds():
    from sources.base import wav_seconds

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as speaker:
        speaker.setnchannels(1)
        speaker.setsampwidth(2)
        speaker.setframerate(16000)
        speaker.writeframes(b"\x00\x00" * 16000)
    assert abs(wav_seconds(buffer.getvalue()) - 1.0) < 0.01


if __name__ == "__main__":
    test_tc3_signature()
    test_xunfei_signature()
    test_wav_seconds()
    print("PASS 签名与音频工具校验")
