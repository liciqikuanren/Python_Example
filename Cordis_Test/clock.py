"""
clock.py - 案例：插件通过事件总线通信（emit / on）

ClockPlugin 每 2 秒 emit 一次 "clock_tick" 事件，
DisplayPlugin 监听该事件并打印时间，二者全程不直接引用对方。
"""

import asyncio
import time
from mini_cordis import Cordis, Context


# ---------- 插件 1：Logger 服务 ----------
class LoggerPlugin:
    name = "logger"
    inject = []

    def apply(self, ctx: Context):
        def log(msg: str):
            print(f"[LOG] {msg}")

        ctx.provide("log", log)
        print("✅ Logger 插件已加载")


# ---------- 插件 2：Clock（事件的发送方）----------
class ClockPlugin:
    name = "clock"
    inject = []  # 不依赖任何服务，只负责广播

    def apply(self, ctx: Context):
        loop = asyncio.get_running_loop()
        running = True
        task = None

        async def tick():
            nonlocal running
            while running:
                # 触发事件：把当前时间广播出去，不关心谁在听
                await ctx.emit("clock_tick", time.strftime("%H:%M:%S"))
                await asyncio.sleep(2)

        def setup():
            nonlocal task
            task = loop.create_task(tick())

        def teardown():
            nonlocal running, task
            running = False
            if task is not None:
                task.cancel()

        ctx.effect("clock", setup, teardown)
        print("✅ Clock 插件已加载")


# ---------- 插件 3：Display（事件的接收方）----------
class DisplayPlugin:
    name = "display"
    inject = ["log"]

    def apply(self, ctx: Context):
        log = ctx.get("log")

        async def on_clock_tick(data):
            log(f"⏰ 收到时钟事件: {data}")

        ctx.on("clock_tick", on_clock_tick)
        print("✅ Display 插件已加载")


# ---------- 主程序 ----------
async def main():
    cordis = Cordis()

    cordis.load_plugin(LoggerPlugin())
    cordis.load_plugin(ClockPlugin())
    cordis.load_plugin(DisplayPlugin())

    # 运行 7 秒观察事件广播
    await asyncio.sleep(7)

    print("\n--- 卸载 Clock 插件 ---")
    cordis.unload_plugin("clock")

    # 再跑 4 秒，确认事件已停止
    await asyncio.sleep(4)
    print("主程序结束")


if __name__ == "__main__":
    asyncio.run(main())
