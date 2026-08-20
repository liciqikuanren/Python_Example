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
        # ---- 依赖关系追踪 ----
        self._dependencies: Dict[str, List[str]] = {}   # 插件名 -> 它 inject 的服务名
        self._dependents: Dict[str, List[str]] = {}     # 服务名 -> 依赖它的插件名列表
        self._service_owners: Dict[str, str] = {}       # 服务名 -> 提供者插件名
        self._provided: Dict[str, List[str]] = {}       # 插件名 -> 它提供的服务名列表
        self._depend_hooks: Dict[str, List[Callable[[str], None]]] = {}  # 服务名 -> 回调

    # ---- 服务管理 ----
    def provide(self, name: str, service: Any):
        owner = self._current_plugin or "unknown"

        # 服务注册本身也作为可逆副作用：卸载时自动从登记簿移除
        def _setup():
            self._services[name] = service

        def _teardown():
            self._services.pop(name, None)

        self.effect(owner, _setup, _teardown)

        # 记录服务归属（依赖图元数据）
        self._service_owners[name] = owner
        self._provided.setdefault(owner, []).append(name)

    def get(self, name: str) -> Any:
        return self._services.get(name)

    # ---- 依赖关系查询 ----
    def get_dependents(self, service_name: str) -> List[str]:
        """谁依赖了这个服务（返回插件名列表）"""
        return list(self._dependents.get(service_name, []))

    def get_dependencies(self, plugin_name: str) -> List[str]:
        """这个插件依赖了哪些服务"""
        return list(self._dependencies.get(plugin_name, []))

    def get_owner(self, service_name: str) -> str | None:
        """这个服务是谁提供的（插件名）"""
        return self._service_owners.get(service_name)

    def who_uses_me(self, plugin_name: str) -> set[str]:
        """谁在引用我（通过我提供的任一服务）"""
        users: set[str] = set()
        for svc in self._provided.get(plugin_name, []):
            users.update(self._dependents.get(svc, []))
        return users

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

    def on_depend(self, service_name: str, hook: Callable[[str], None]):
        """每当有插件开始依赖 service_name 时，调用 hook(依赖者插件名)。作为副作用注册。"""
        owner = self._current_plugin or "unknown"

        def _setup():
            self._depend_hooks.setdefault(service_name, []).append(hook)

        def _teardown():
            hooks = self._depend_hooks.get(service_name, [])
            if hook in hooks:
                hooks.remove(hook)

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


def validate_plugin(plugin: Plugin) -> None:
    """校验插件是否符合规范，不符合抛 ValueError。

    检查项：
    1. name 存在且为非空字符串
    2. inject 存在且为字符串列表
    3. apply 存在且可调用
    """
    name = getattr(plugin, "name", None)
    if not isinstance(name, str) or not name:
        raise ValueError("插件缺少有效的 name（非空字符串）")

    inject = getattr(plugin, "inject", None) or []
    if not isinstance(inject, list) or not all(isinstance(d, str) for d in inject):
        raise ValueError(f"插件 {name} 的 inject 必须是字符串列表")

    if not callable(getattr(plugin, "apply", None)):
        raise ValueError(f"插件 {name} 缺少可调用的 apply 方法")


# ---------- 4. 核心加载器 ----------
class Cordis:
    def __init__(self):
        self.ctx = Context()
        self._loaded: List[str] = []  # 记录加载顺序，用于逆序卸载

    def load_plugin(self, plugin: Plugin):
        """加载插件：校验规范 -> 检查依赖 -> 记录依赖关系 -> 执行 apply"""
        validate_plugin(plugin)

        # 检查依赖是否满足
        for dep in plugin.inject:
            if self.ctx.get(dep) is None:
                raise RuntimeError(f"缺少依赖服务: {dep}")

        if plugin.name in self.ctx._dependencies:
            raise RuntimeError(f"插件已加载: {plugin.name}")

        # 正向：记录该插件依赖了哪些服务
        self.ctx._dependencies[plugin.name] = list(plugin.inject)

        # 反向：记录“谁依赖了这个服务”，并通知已注册的监听者
        for dep in plugin.inject:
            self.ctx._dependents.setdefault(dep, []).append(plugin.name)
            for hook in self.ctx._depend_hooks.get(dep, []):
                hook(plugin.name)

        # 将副作用归属到当前插件，执行 apply
        self.ctx._current_plugin = plugin.name
        try:
            plugin.apply(self.ctx)
        finally:
            self.ctx._current_plugin = None

        self._loaded.append(plugin.name)

    def unload_plugin(self, plugin_name: str):
        """卸载插件及其所有（传递）依赖者，按逆序逐个撤销。

        例如依赖链 app -> service -> db，调用 unload_plugin("db")
        会级联卸载 app、service、db（按 app -> service -> db 逆序）。
        """
        affected = self._transitive_dependents(plugin_name) | {plugin_name}
        for name in reversed(list(self._loaded)):
            if name in affected:
                self._unload_one(name)

    def _transitive_dependents(self, plugin_name: str) -> set[str]:
        """返回所有直接/间接依赖 plugin_name 的插件名集合"""
        result: set[str] = set()
        stack = list(self.ctx.who_uses_me(plugin_name))
        while stack:
            dep = stack.pop()
            if dep in result:
                continue
            result.add(dep)
            stack.extend(self.ctx.who_uses_me(dep))
        return result

    def _unload_one(self, plugin_name: str):
        """卸载单个插件（不级联），并清理依赖图"""
        # 撤销副作用（含服务移除、事件监听、后台任务等）
        self.ctx.revert_effects_for(plugin_name)

        # 清理正向记录
        self.ctx._dependencies.pop(plugin_name, None)

        # 清理我提供的服务及其归属
        for svc in self.ctx._provided.pop(plugin_name, []):
            self.ctx._service_owners.pop(svc, None)
            self.ctx._dependents.pop(svc, None)

        # 从反向索引里移除“我作为依赖者”的记录
        for deps in self.ctx._dependents.values():
            if plugin_name in deps:
                deps.remove(plugin_name)

        # 从加载顺序里移除
        if plugin_name in self._loaded:
            self._loaded.remove(plugin_name)

    def load_all(self, plugins: List[Plugin]):
        """批量加载：自动按依赖顺序（被依赖者先加载）。

        反复扫描剩余插件，依赖已满足的就加载，直到全部加载完；
        若某一轮无任何进展，说明存在循环依赖或缺少依赖。
        """
        remaining = list(plugins)
        while remaining:
            progress = False
            for plugin in remaining[:]:
                if any(self.ctx.get(dep) is None for dep in plugin.inject):
                    continue  # 依赖还没就绪，等下一轮
                self.load_plugin(plugin)
                remaining.remove(plugin)
                progress = True
            if not progress:
                unresolved = ", ".join(
                    f"{p.name}(缺 {[d for d in p.inject if self.ctx.get(d) is None]})"
                    for p in remaining
                )
                raise RuntimeError(f"无法确定加载顺序（循环依赖或缺少依赖）: {unresolved}")

    def unload_all(self):
        """批量卸载：按加载顺序的逆序（后加载的先卸载）"""
        while self._loaded:
            self._unload_one(self._loaded[-1])
