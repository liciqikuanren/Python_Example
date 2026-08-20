import asyncio
import time
from mini_cordis import Cordis, Context, Plugin


# ---------- 插件 1：Logger 服务 ----------
class LoggerPlugin:
    name = "logger"
    inject = []  # 无依赖

    def apply(self, ctx: Context):
        def log(msg: str):
            print(f"[LOG] {msg}")

        # 提供 log 服务
        ctx.provide("log", log)
        print("✅ Logger 插件已加载")


# ---------- 插件 2：Timer 插件（依赖 Logger） ----------
class TimerPlugin:
    name = "timer"
    inject = ["log"]  # 依赖 log 服务

    def apply(self, ctx: Context):
        log = ctx.get("log")
        loop = asyncio.get_running_loop()
        running = True
        task = None  # 声明在 apply 作用域，供 setup/teardown 共享

        # 定时器协程
        async def tick():
            nonlocal running
            while running:
                log(f"当前时间: {time.strftime('%H:%M:%S')}")
                await asyncio.sleep(2)

        # 启动定时器（副作用）
        def setup():
            nonlocal task
            task = loop.create_task(tick())

        def teardown():
            nonlocal running, task
            running = False
            if task is not None:
                task.cancel()
            log("⏹️ 定时器已停止")

        ctx.effect("timer", setup, teardown)
        print("✅ Timer 插件已加载")


# ---------- 插件 3：Greeter 插件（监听事件） ----------
class GreeterPlugin:
    name = "greeter"
    inject = ["log"]  # 依赖 log

    def apply(self, ctx: Context):
        log = ctx.get("log")

        async def on_greet(data):
            log(f"👋 收到问候: {data}")

        # 注册事件监听（副作用已内置在 ctx.on 中）
        ctx.on("greet", on_greet)
        print("✅ Greeter 插件已加载")


# ---------- 主程序 ----------
async def main():
    cordis = Cordis()

    # 1. 按顺序加载插件（依赖关系决定顺序）
    cordis.load_plugin(LoggerPlugin())
    cordis.load_plugin(TimerPlugin())
    cordis.load_plugin(GreeterPlugin())

    # 2. 模拟业务：3秒后触发一次 greet 事件
    await asyncio.sleep(3)
    await cordis.ctx.emit("greet", "Hello from main!")

    # 3. 6秒后卸载 timer 插件
    await asyncio.sleep(6)
    print("\n--- 卸载 Timer 插件 ---")
    cordis.unload_plugin("timer")

    # 4. 继续运行 5 秒观察效果
    await asyncio.sleep(5)
    print("主程序结束")


if __name__ == "__main__":
    asyncio.run(main())
