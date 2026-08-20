"""温度传感器插件：每 temp_interval 秒 emit 一次 temp_reading（依赖 serial、config、log）"""

import math
import time


class Plugin:
    name = "temp"
    inject = ["serial", "config", "log"]

    def apply(self, ctx):
        cfg = ctx.get("config")
        log = ctx.get("log")

        def read():
            value = round(45 + 45 * math.sin(time.time() / 2), 1)
            return ctx.emit("temp_reading", {"source": "temp", "value": value})

        # setInterval 自动注册为可逆副作用，卸载时自动停
        ctx.setInterval(cfg["temp_interval"], read)
        ctx.effect(lambda: None, lambda: log("🌡️ 温度传感器已移除"))