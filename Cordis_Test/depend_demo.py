"""
depend_demo.py - 案例：正向依赖记录 + 反向依赖感知

- Logger 提供 "log" 服务，并通过 on_depend 感知谁在引用自己
- Timer / Greeter 依赖 "log"
- 演示框架如何记录正向依赖（谁依赖谁）和反向感知（被谁引用）
"""

import asyncio
from mini_cordis import Cordis, Context


# ---------- 插件 1：Logger（服务提供方，感知被谁引用）----------
class LoggerPlugin:
    name = "logger"
    inject = []

    def apply(self, ctx: Context):
        def log(msg: str):
            print(f"[LOG] {msg}")

        ctx.provide("log", log)

        # 注册“被引用”感知：每当有插件开始依赖 "log" 时触发
        def on_new_user(plugin_name: str):
            log(f"👀 有人开始引用 log：{plugin_name}")

        ctx.on_depend("log", on_new_user)
        print("✅ Logger 插件已加载")


# ---------- 插件 2：Timer（依赖 log）----------
class TimerPlugin:
    name = "timer"
    inject = ["log"]

    def apply(self, ctx: Context):
        log = ctx.get("log")
        log("Timer 初始化完成")
        print("✅ Timer 插件已加载")


# ---------- 插件 3：Greeter（依赖 log）----------
class GreeterPlugin:
    name = "greeter"
    inject = ["log"]

    def apply(self, ctx: Context):
        log = ctx.get("log")
        log("Greeter 初始化完成")
        print("✅ Greeter 插件已加载")


# ---------- 主程序 ----------
async def main():
    cordis = Cordis()

    cordis.load_plugin(LoggerPlugin())
    cordis.load_plugin(TimerPlugin())
    cordis.load_plugin(GreeterPlugin())

    ctx = cordis.ctx

    print("\n--- 依赖关系查询 ---")
    print(f"谁依赖 log:         {ctx.get_dependents('log')}")
    print(f"谁引用 logger:      {sorted(ctx.who_uses_me('logger'))}")
    print(f"timer 依赖哪些服务: {ctx.get_dependencies('timer')}")
    print(f"log 的提供者:       {ctx.get_owner('log')}")

    print("\n--- 卸载 timer 后再查 ---")
    cordis.unload_plugin("timer")
    print(f"谁依赖 log:         {ctx.get_dependents('log')}")


if __name__ == "__main__":
    asyncio.run(main())
