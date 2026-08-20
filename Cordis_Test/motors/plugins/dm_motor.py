"""DM 协议电机插件：每实例一台电机，自带断线检测与自动重连。

用法（在 main 里）：
    cordis.load_plugin(DmMotorPlugin(), key="dm.0",
                       config={"can_id": 0x300, "period": 0.5})
    motor = ctx.get("dm.0")   # motor.set_position(...) / motor.enable() / motor.online

与 dji_motor 的差异：DM 协议走"位置环"，控制接口是 set_position，
回帧内容也不同——体现同一总线上的不同协议、不同使用方法。
"""


class DmMotorController:
    """单台 DM 电机的控制句柄（DM 协议：位置环）。"""

    def __init__(self, can, can_id, log, name):
        self.can = can
        self.can_id = can_id
        self.log = log
        self.name = name
        self.kind = "dm"

        self.online = False
        self._ever_online = False
        self._since_reply = 99
        self._reply = False
        self.enabled = False
        self.angle = 0.0

    # ---- 协议：回帧解析 ----
    def on_frame(self, frame):
        self._reply = True

    # ---- 协议：控制 ----
    def enable(self):
        self.enabled = True

    def set_position(self, deg: float):
        self.angle = float(deg)

    def read(self) -> dict:
        return {"online": self.online, "enabled": self.enabled, "angle": self.angle}

    # ---- 心跳：断线检测 / 自动重连 ----
    def poll(self):
        sent = self.can.send(self.can_id, b"DM-QUERY")
        self._since_reply = self._since_reply + 1 if sent else 99

        if self._reply:
            self._reply = False
            self._since_reply = 0
            if not self.online:
                self._on_connect()
        elif self.online and self._since_reply > 2:
            self.online = False
            self.log(f"⚠️ {self.name} 断线")

    def _on_connect(self):
        self.online = True
        if self._ever_online:
            self.log(f"🔗 {self.name} 重连成功")
        else:
            self._ever_online = True
            self.log(f"🟢 {self.name} 已上线")


class Plugin:
    name = "dm_motor"
    inject = ["can", "log"]

    def apply(self, ctx):
        can = ctx.get("can")
        log = ctx.get("log")
        cfg = ctx.config or {}
        can_id = cfg.get("can_id", 0x300)
        name = ctx.name  # 实例 key，如 "dm.0"

        motor = DmMotorController(can, can_id, log, name)
        ctx.provide(ctx.name, motor)

        def setup():
            motor._dispose = can.on(can_id, motor.on_frame)

        def teardown():
            if motor._dispose:
                motor._dispose()

        ctx.effect(setup, teardown)
        ctx.setInterval(cfg.get("period", 0.5), motor.poll)
        log(f"✅ {name} 已挂载 (CAN {hex(can_id)})")