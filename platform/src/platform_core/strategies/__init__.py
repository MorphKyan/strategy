"""平台策略扩展包。

按蓝图 C1 规范：新策略一律一个文件一个策略放在本包内，
在 `strategy.py` 末尾 import 并注册进 `BUILTIN_STRATEGIES`；
`strategy.py` 本体只保留基类、上下文、注册表与既有 risk parity 家族。
"""
