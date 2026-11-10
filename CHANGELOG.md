# 更新日志

## 0.1.0

- 新增腾讯云 ASR（`tencent_asr_api3`）：TC3-HMAC-SHA256 签名，调 SentenceRecognition。
- 新增豆包 ASR（`doubao_asr_file`）：`X-Api-Key` + `volc.seedasr.auc`，submit 后 query 轮询。
- 新增讯飞 ASR（`xunfei_iat_ws`）：语音听写大模型 V2.0 WebSocket，整段推流后收尾。
- 三个适配器都注册到 AstrBot 的语音转文字提供商类型；实测同一段音频三家都能返回完整文字。
- README 写清每家的控制台入口、要拿的字段、常见报错对照。
