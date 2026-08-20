"""配置插件：提供全局配置服务 config（无依赖）"""


class Plugin:
    name = "config"
    inject = []

    def apply(self, ctx):
        ctx.provide("config", {
            "port": "COM3",
            "temp_threshold": 70,
            "temp_interval": 2,
            "power_interval": 3,
        })