# 更新日志

## 0.2.4

撤掉 0.2.3 里「读控制台设置」的接入（2026-11-14）：

这个插件是通用件，不该依赖某个中台程序的 settings.json。0.2.3 那段按
PYMSS_DATA_DIR / hub_dir.txt 找控制台配置的逻辑全部移除，只保留：

- 构造函数注入的 AstrBot 插件配置（0.2.0 的修法）；
- 注入配置缺字段时读 data/config/astrbot_plugin_stt_compat_config.json 兜底；
- 适配器注册幂等（0.2.2，面板重载不再报「已经注册」）。

腾讯 AppID 请在插件设置页填写；它是 AstrBot 自己管理的配置，外部改文件
会在 AstrBot 重启时被内存配置覆盖（实测）。
## 0.2.3

腾讯 AppID 自动补齐（2026-11-14）：

AstrBot 会用它内存里的配置覆盖 data/config/..._config.json，外部写进去的值重启就没
（实测），所以改成**插件配置缺字段时回退读控制台设置**：

- 定位顺序与控制台一致：PYMSS_DATA_DIR → 插件目录 hub_dir.txt → 用户目录 data；
- 映射 ccount.tencent_app_id / secret_id / secret_key / doubao_api_key / xunfei_*；
- 启动日志明确「以下字段取的控制台设置：…」「密钥已就绪：7 项」。

实测：重启后日志 密钥已就绪：7 项，不再提示 tencent_app_id 为空。
## 0.2.2

热重载不再炸（2026-11-14）：

AstrBot 的 provider 注册表是全局的，面板点「重载」会重新执行插件模块，
@register_provider_adapter 再跑一遍就抛「doubao_asr_file 已经注册」，
整个插件加载失败。新增 sources/registry.py：名字已存在时不抛错，把注册表里的
元数据原位换成新类（cls_type/desc/显示名），热重载后的新代码真正生效。

	ests/test_reload.py：同进程 importlib.reload 适配器模块，验证不抛错且映射指向新类。

## 0.2.1

- 腾讯云新增 **AppID** 字段（`_conf_schema.json` / `main.py` / `sources/tencent.py`）。
  原因：实时语音识别 V2 的地址是 `wss://asr.cloud.tencent.com/asr/v2/<appid>?...`，
  AppID 在 URL 路径里；原来只存 SecretId/SecretKey，所以腾讯只能走文件接口。
  AppID 是 130 开头的账号级 ID，和密钥在同一个「API 密钥管理」页面。
- `sources/tencent.py` 加 `stream_ready()`：三个值齐了才算能走流式。

## 0.2.0

- **修：运行时报「豆包 ASR 缺少 API Key」**。根因是插件用 `context.get_config()` 取密钥，
  而 AstrBot 4.x 的这个接口返回的是 **全局配置**，不是插件配置；现在改成接收构造函数注入的
  `config: AstrBotConfig`。
- 新增文件兜底：注入的配置缺字段时，自动读
  `data/config/astrbot_plugin_stt_compat_config.json`（带 mtime 缓存），密钥漏配也能跑。
- 启动日志会打印「密钥已就绪：N 项」或「以下密钥为空：…」，不再静默失败。

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
