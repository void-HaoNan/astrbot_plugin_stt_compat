# -*- coding: utf-8 -*-
"""热重载不能再炸：同一个进程里把适配器模块重新导入一次，注册必须幂等。

2026-11-14 真事故：AstrBot 的 provider 注册表是全局的，面板点「重载」会重新执行
插件的模块，`@register_provider_adapter` 再跑一遍就抛「doubao_asr_file 已经注册」，
整个插件加载失败。这里用 importlib.reload 模拟一次重载。
"""
import importlib
import os
import shutil
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

failures = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if not ok:
        failures.append(f"{name}：{detail}" if detail else name)


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="stt_reload_")
    pkg = os.path.join(tmp, "stt_probe")
    shutil.copytree(os.path.join(PLUGIN, "sources"), os.path.join(pkg, "sources"))
    with open(os.path.join(pkg, "__init__.py"), "w", encoding="utf-8") as handle:
        handle.write("")
    sys.path.insert(0, tmp)
    try:
        mod = importlib.import_module("stt_probe.sources.doubao")
        check("首次导入成功", mod is not None)
        try:
            importlib.reload(mod)
            reloaded = True
            detail = ""
        except Exception as error:  # noqa: BLE001 - 就是要抓这个
            reloaded = False
            detail = f"{type(error).__name__}: {error}"
        check("重新导入（模拟热重载）不抛错", reloaded, detail)

        # 注册表里应该只有一份同名适配器
        from astrbot.core.provider.register import provider_cls_map

        meta = provider_cls_map.get("doubao_asr_file")
        check("注册表里能查到 doubao_asr_file", meta is not None)
        check("重载后映射指向最新类",
              meta is not None and getattr(meta.cls_type, "__module__", "").startswith("stt_probe"),
              getattr(getattr(meta, "cls_type", None), "__module__", ""))
    finally:
        sys.path.remove(tmp)
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print("失败：")
        for item in failures:
            print(" -", item)
        return 1
    print("stt_compat：首次导入 + 热重载都不再触发重复注册")
    return 0


if __name__ == "__main__":
    sys.exit(main())
