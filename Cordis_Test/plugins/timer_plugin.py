"""定时器：每 2 秒用 log 打印当前时间（依赖 log）"""

import asyncio
import time


class Plugin:
    name = "timer"
    inject = ["log"]

    def apply(self, ctx):
        log = ctx.get("log")
        loop = asyncio.get_running_loop()
        running = True
        task = None

        async def tick():
            nonlocal running
            while running:
                log(f"当前时间: {time.strftime('%H:%M:%S')}")
                await asyncio.sleep(2)

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
