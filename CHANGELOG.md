# 更新日志

## 0.1.3

- 正式开源：仓库 `https://github.com/void-HaoNan/astrbot_plugin_stt_compat`，
  metadata 版本对齐到本文件（之前 metadata 停在 0.1.0）。
- 说明补一句适用场景：除了 AstrBot 自己用，直播中台也能按同一套字段和协议直连这三家
  （中台设置页「识别密钥」里填一样的密钥，就不用装 AstrBot）。

## 0.1.2

- 插件改名 `astrbot_plugin_stt_compat`，显示名改成「STT 提供商兼容」，说明它做的事。
- 密钥统一在插件设置里填，提供商页不再出现密钥框。


## 0.1.0

- 新增腾讯云 ASR（`tencent_asr_api3`）：TC3-HMAC-SHA256 签名，调 SentenceRecognition。
- 新增豆包 ASR（`doubao_asr_file`）：`X-Api-Key` + `volc.seedasr.auc`，submit 后 query 轮询。
- 新增讯飞 ASR（`xunfei_iat_ws`）：语音听写大模型 V2.0 WebSocket，整段推流后收尾。
- 三个适配器都注册到 AstrBot 的语音转文字提供商类型；实测同一段音频三家都能返回完整文字。
- README 写清每家的控制台入口、要拿的字段、常见报错对照。
