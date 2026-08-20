"""串口总线插件：提供服务 serial + 反向依赖感知（依赖 config、log）"""


class Plugin:
    name = "serial"
    inject = ["config", "log"]

    def apply(self, ctx):
        cfg = ctx.get("config")
        log = ctx.get("log")

        ctx.provide("serial", {"port": cfg["port"]})

        def on_new_user(plugin_name: str):
            log(f"🔌 {plugin_name} 接入了串口总线")

        ctx.on_depend("serial", on_new_user)
        ctx.effect(lambda: None, lambda: log("🔌 串口总线已移除"))
        log(f"🟢 串口总线就绪 (端口 {cfg['port']})")