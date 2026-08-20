"""监听 greet 事件，打印问候语（依赖 log）"""


class Plugin:
    name = "greeter"
    inject = ["log"]

    def apply(self, ctx):
        log = ctx.get("log")

        async def on_greet(data):
            log(f"👋 收到问候: {data}")

        ctx.on("greet", on_greet)
        print("✅ Greeter 插件已加载")
