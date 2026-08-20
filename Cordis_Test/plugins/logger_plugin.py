"""提供 log 服务（无依赖）"""


class Plugin:
    name = "logger"
    inject = []

    def apply(self, ctx):
        def log(msg: str):
            print(f"[LOG] {msg}")

        ctx.provide("log", log)
        print("✅ Logger 插件已加载")
