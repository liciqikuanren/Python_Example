"""记录器插件：非 UI 消费者，监听 temp_reading / power_status（依赖 log）"""


class Plugin:
    name = "recorder"
    inject = ["log"]

    def apply(self, ctx):
        log = ctx.get("log")

        async def on_temp(data):
            log(f"📝 记录温度: {data['value']}°C")

        async def on_power(data):
            log(f"📝 记录电压: {data['voltage']}V")

        ctx.on("temp_reading", on_temp)
        ctx.on("power_status", on_power)