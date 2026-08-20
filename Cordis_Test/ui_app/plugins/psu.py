"""电源插件：提供服务 psu + 每 3 秒 emit power_status（依赖 serial、log）"""


class Plugin:
    name = "psu"
    inject = ["serial", "log"]

    def apply(self, ctx):
        log = ctx.get("log")
        state = {"voltage": 12.0}

        def set_voltage(v: float) -> float:
            state["voltage"] = float(v)
            return state["voltage"]

        ctx.provide("psu", set_voltage)

        def status():
            return ctx.emit("power_status", {"source": "psu", "voltage": state["voltage"]})

        ctx.setInterval(3, status)
        ctx.effect(lambda: None, lambda: log("🔋 电源已移除"))