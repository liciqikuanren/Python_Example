"""泵插件：应用层消费者，分别控制 DJI（速度环）与 DM（位置环）电机。

不 inject 具体电机实例（数量动态），而是按命名前缀动态扫描 ctx 注册表：
    get("dji.0") / get("dji.1") ...   get("dm.0") / get("dm.1") ...
已卸载实例（get 返回 None）直接跳过；离线电机（motor.online == False）降级跳过。
各实例接口不同（DJI 用 set_speed，DM 用 set_position），按 kind 分别调用。
"""


class Plugin:
    name = "pump"
    inject = ["log"]

    def apply(self, ctx):
        log = ctx.get("log")
        cfg = ctx.config or {}
        targets = cfg.get("targets", [("dji.", 8), ("dm.", 8)])  # (前缀, 遍历数量)

        def cycle():
            for prefix, count in targets:
                for i in range(count):
                    name = f"{prefix}{i}"
                    motor = ctx.get(name)
                    if motor is None:
                        continue  # 未挂载 / 已卸载
                    if not motor.online:
                        log(f"泵: {name} 离线，跳过")
                        continue
                    if motor.kind == "dji":
                        motor.set_speed(500)   # DJI 速度环
                    else:
                        motor.set_position(90)  # DM 位置环
                    log(f"泵: 驱动 {name} → {motor.read()}")

        ctx.setInterval(1.0, cycle)
        log("✅ pump 已加载")