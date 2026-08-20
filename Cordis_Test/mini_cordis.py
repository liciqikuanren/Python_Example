"""
mini_cordis.py - 一个极简的 Cordis 风格插件框架
"""

from typing import Dict, List, Any, Callable, Protocol
import asyncio


# ---------- 1. 副作用（Effect） ----------
class Effect:
    """可逆副作用：记录一个操作及其撤销方法"""
    def __init__(self, owner: str, setup: Callable[[], None], teardown: Callable[[], None]):
        self.owner = owner
        self._setup = setup
        self._teardown = teardown

    def apply(self):
        self._setup()

    def revert(self):
        self._teardown()


# ---------- 2. 上下文（Context） ----------
class Context:
    """插件运行环境：服务注册 + 副作用记录 + 事件总线"""
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._effects: List[Effect] = []
        self._event_listeners: Dict[str, List[Callable]] = {}
        self._current_plugin: str | None = None

    # ---- 服务管理 ----
    def provide(self, name: str, service: Any):
        self._services[name] = service

    def get(self, name: str) -> Any:
        return self._services.get(name)

    # ---- 副作用注册 ----
    def effect(self, owner: str, setup: Callable[[], None], teardown: Callable[[], None]):
        effect = Effect(owner, setup, teardown)
        effect.apply()
        self._effects.append(effect)

    # ---- 事件总线 ----
    def on(self, event: str, handler: Callable):
        """注册事件监听（作为副作用，归属当前插件）"""
        owner = self._current_plugin or "unknown"

        def _setup():
            self._event_listeners.setdefault(event, []).append(handler)

        def _teardown():
            listeners = self._event_listeners.get(event, [])
            if handler in listeners:
                listeners.remove(handler)

        self.effect(owner, _setup, _teardown)

    async def emit(self, event: str, data: Any = None):
        """触发事件"""
        for handler in self._event_listeners.get(event, []):
            # 简单并发执行
            await handler(data)

    # ---- 卸载插件 ----
    def revert_effects_for(self, owner: str):
        """撤销指定插件的所有副作用（卸载）"""
        remaining = []
        for effect in self._effects:
            if effect.owner == owner:
                effect.revert()
            else:
                remaining.append(effect)
        self._effects = remaining


# ---------- 3. 插件协议（Protocol） ----------
class Plugin(Protocol):
    name: str
    inject: List[str]  # 依赖的服务名列表

    def apply(self, ctx: Context):
        ...


# ---------- 4. 核心加载器 ----------
class Cordis:
    def __init__(self):
        self.ctx = Context()

    def load_plugin(self, plugin: Plugin):
        """加载插件：检查依赖 -> 执行 apply"""
        # 检查依赖是否满足
        for dep in plugin.inject:
            if self.ctx.get(dep) is None:
                raise RuntimeError(f"缺少依赖服务: {dep}")

        # 将副作用归属到当前插件，执行 apply
        self.ctx._current_plugin = plugin.name
        try:
            plugin.apply(self.ctx)
        finally:
            self.ctx._current_plugin = None

    def unload_plugin(self, plugin_name: str):
        """卸载插件（通过名称）"""
        self.ctx.revert_effects_for(plugin_name)
