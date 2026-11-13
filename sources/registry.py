"""适配器注册的幂等包装。

AstrBot 的 `provider_cls_map` 是全局注册表，插件热重载时模块会被重新导入，
`@register_provider_adapter` 再跑一遍就会抛「检测到...已经注册」，整个插件加载失败
（2026-11-14 实测：面板上点一次重载，日志就是 Failed to import plugin）。

这里包一层：名字已存在时把注册表里的元数据原位换成新类——
既不报错，热重载后的新代码也能真正生效，而不是继续跑旧类。
"""
from __future__ import annotations

from astrbot.api import logger
from astrbot.core.provider.register import (
    provider_cls_map,
    provider_registry,
    register_provider_adapter,
)


def register_adapter(provider_type_name: str, desc: str, **kwargs):
    """和 `register_provider_adapter` 用法一致，但可重复执行。"""

    def decorator(cls):
        try:
            return register_provider_adapter(provider_type_name, desc, **kwargs)(cls)
        except ValueError:
            # 已经注册过：热重载场景，原位更新
            meta = provider_cls_map.get(provider_type_name)
            if meta is not None:
                meta.cls_type = cls
                meta.desc = desc
                display = kwargs.get("provider_display_name")
                if display:
                    meta.provider_display_name = display
                logger.info("[stt_compat] 适配器 %s 已存在，原位换成新类（热重载）",
                            provider_type_name)
            else:
                # 名字不在 map 里但被拒：理论上不会发生，补一条免得下次排查摸黑
                logger.warning("[stt_compat] 适配器 %s 注册被拒，注册表里也找不到",
                               provider_type_name)
            return cls
        except Exception as error:  # noqa: BLE001 - 注册失败不能让整个插件起不来
            logger.warning("[stt_compat] 适配器 %s 注册失败：%s", provider_type_name, error)
            return cls

    return decorator


__all__ = ["register_adapter", "provider_registry"]
