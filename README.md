# astrbot_plugin_stt_cn

把 **腾讯云、豆包（火山引擎）、讯飞** 的语音识别接入 AstrBot 的「语音转文字」提供商列表。

装好之后，AstrBot 面板 → 提供商 → 语音转文字 里会多出三种类型：

| 类型 id | 显示名 | 协议 |
| --- | --- | --- |
| `tencent_asr_api3` | 腾讯云 ASR（API 3.0） | SentenceRecognition，TC3-HMAC-SHA256 签名 |
| `doubao_asr_file` | 豆包 ASR（录音文件） | 大模型录音文件识别，submit + query |
| `xunfei_iat_ws` | 讯飞 ASR（听写 V2.0） | 语音听写大模型 WebSocket |

三种都按「整段音频进、文字出」工作，因此 AstrBot 的语音消息、我们的直播链路都能直接用。

---

## 一、先搞清楚每个平台要哪几个值

这是最容易踩坑的地方：每家平台都有「总密钥」和「语音服务密钥」两套，用错了就报签名错误或资源未授权。

### 腾讯云

| 字段 | 从哪拿 | 说明 |
| --- | --- | --- |
| `SecretId` | [API 密钥管理](https://console.cloud.tencent.com/cam/capi) | 点「新建密钥」，这是给接口签名用的 |
| `SecretKey` | 同上 | 和 SecretId 成对，只显示一次，务必存好 |
| ~~AppID~~ | — | **API 3.0 不需要 AppID**，只要 SecretId + SecretKey |

操作顺序：先到 [语音识别控制台](https://console.cloud.tencent.com/asr) 开通「语音识别」（一句话识别/录音识别都在这下面），再去 API 密钥管理建密钥。  
云 API 的签名是 TC3-HMAC-SHA256，服务名 `asr`，接口 `SentenceRecognition`。

### 豆包（火山引擎）

| 字段 | 从哪拿 | 说明 |
| --- | --- | --- |
| `API Key` | [语音技术控制台](https://console.volcengine.com/speech/app) → 应用详情 | 36 位 UUID，作为 `X-Api-Key` 请求头 |
| `资源 ID` | 控制台开通的服务 | 大模型录音文件识别：`volc.seedasr.auc` |

注意：**访问控制里的 AccessKeyId / SecretAccessKey 是云资源 OpenAPI 用的，语音识别不认**，别拿那个。  
如果控制台给的是「AppID + Access Token」而不是 API Key，则改用 `X-Api-App-Key` + `X-Api-Access-Key` 那套请求头（本插件当前按 API Key 实现，见 FAQ）。

### 讯飞

| 字段 | 从哪拿 | 说明 |
| --- | --- | --- |
| `APPID` | [讯飞开放平台](https://console.xfyun.cn/app/myapp) → 我的应用 → 应用详情 | 应用级，8 位左右 |
| `APIKey` | 同上 | 和 APISecret 一起做 HMAC-SHA256 签名 |
| `APISecret` | 同上 | 不要把 APPID 当成 APIKey 复制 |

服务要在应用里勾选 **语音听写大模型（中英）V2.0**（WebSocket 服务，`wss://iat.cn-huabei-1.xf-yun.com/v1`）。

---

## 二、在 AstrBot 里配置

1. 把本插件放进 `data/plugins/astrbot_plugin_stt_cn`。
2. 重启 AstrBot，日志出现 `Loading model tencent_asr_api3 ...` 等三行即注册成功。
3. 面板 → 提供商 → 新增「语音转文字」提供商，按下面填：

**腾讯云**
```json
{ "type": "tencent_asr_api3", "api_key": "SecretId", "backup_api_key": "SecretKey",
  "engine_model_type": "16k_zh" }
```

**豆包**
```json
{ "type": "doubao_asr_file", "api_key": "36 位 API Key",
  "resource_id": "volc.seedasr.auc" }
```

**讯飞**
```json
{ "type": "xunfei_iat_ws", "app_id": "APPID", "api_key": "APIKey",
  "backup_api_key": "APISecret" }
```

4. 在「语音转文字」设置里把默认提供商选成新建的那一个。

---

## 三、常见报错对照

| 报错 | 原因 | 处理 |
| --- | --- | --- |
| 腾讯云 `4002 签名错误` | SecretId / SecretKey 不配对，或用了旧版极速版签名 | 确认同一账号同一时间生成；本插件走 API 3.0 的 TC3 签名，不要用旧版参数 |
| 腾讯云 `4001 engine_type: is required` | 用了旧版极速版接口却少传参数 | 用 `tencent_asr_api3`，不要用极速版 |
| 豆包 `requested resource not granted` | 该应用没开通对应资源，或资源 ID 写错 | 控制台开通「大模型录音文件识别」，资源 ID `volc.seedasr.auc` |
| 豆包 `load grant: requested grant not found` | 把 IAM 的 AK/SK 当成了语音 Token | 用语音控制台应用里的 API Key |
| 讯飞 `appId illegal` | APPID 不对，或应用没勾选对应服务 | 在同一个应用里勾选语音听写大模型 V2.0，确认 APPID |
| 讯飞 `26610` | 参数/签名不对 | 检查 APIKey 与 APISecret 是否配反 |

---

## 四、两种模式怎么选

- **文件识别**：腾讯云 API 3.0、豆包 submit+query、讯飞 WebSocket 一次性推完整段，AstrBot 直接当 STT 提供商使用。
- **实时识别**：腾讯云实时语音识别、豆包流式大模型、讯飞听写 V2.0 都支持 WebSocket 流式；AstrBot 的 STT 接口目前只接受整段音频，所以实时模式适合接在自建链路里，本插件的讯飞实现已经复用同一套认证，可以按帧喂音频。

---

## 五、本地校验

```bash
python -X utf8 tests/test_sign.py
```

会检查 TC3 签名、讯飞签名和音频长度计算，不联网。

## 六、更新日志

见 [CHANGELOG.md](CHANGELOG.md)。

## 七、许可

MIT，见 [LICENSE](LICENSE)。
