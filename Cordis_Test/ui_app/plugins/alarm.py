"""告警插件：注入 psu 服务 + 监听 temp_reading，超温断电并广播 alarm（依赖 psu、config、log）"""


class Plugin:
    name = "alarm"
    inject = ["psu", "config", "log"]

    def apply(self, ctx):
        psu = ctx.get("psu")
        cfg = ctx.get("config")
        log = ctx.get("log")

        async def on_temp(data):
            if data["value"] > cfg["temp_threshold"]:
                log(f"🚨 温度 {data['value']}°C 超阈值，紧急断电")
                psu(0.0)
                await ctx.emit("alarm", {
                    "source": "alarm",
                    "msg": f"温度过高 {data['value']}°C，已断电",
                })

        ctx.on("temp_reading", on_temp)
        ctx.effect(lambda: None, lambda: log("🚨 告警插件已移除"))