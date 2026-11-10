"""导入即注册：三个提供商适配器都靠装饰器挂到 AstrBot 的 provider 注册表。"""

from . import doubao, tencent, xunfei  # noqa: F401
