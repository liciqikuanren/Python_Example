"""DJI 协议电机插件：每实例一台电机，自带断线检测与自动重连。

用法（在 main 里）：
    cordis.load_plugin(DjiMotorPlugin(), key="dji.0",
                       config={"can_id": 0x200, "period": 0.5})
    motor = ctx.get("dji.0")   # motor.set_speed(...) / motor.enable() / motor.online

断线重连：实例启动一个心跳协程（setInterval），周期发送 CAN 查询帧。
- 连续多次无回帧（电机掉电 / 总线拔出）→ 判定断线
- 心跳持续发送，一旦恢复回帧 → 判定重连成功
"""


class DjiMotorController:
    """单台 DJI 电机的控制句柄（DJI 协议：速度环）。"""

    def __init__(self, can, can_id, log, name):
        self.can = can
        self.can_id = can_id
        self.log = log
        self.name = name
        self.kind = "dji"

        self.online = False
        self._ever_online = False
        self._since_reply = 99   # 初始视为未收到过任何回应
        self._reply = False
        self.enabled = False
        self.rpm = 0.0

    # ---- 协议：回帧解析 ----
    def on_frame(self, frame):
        self._reply = True

    # ---- 协议：控制 ----
    def enable(self):
        self.enabled = True

    def set_speed(self, rpm: float):
        self.rpm = float(rpm)

    def read(self) -> dict:
        return {"online": self.online, "enabled": self.enabled, "rpm": self.rpm}

    # ---- 心跳：断线检测 / 自动重连 ----
    def poll(self):
        sent = self.can.send(self.can_id, b"DJI-QUERY")
        # 总线离线视为立即失联；否则按连续无回应判定
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
    name = "dji_motor"
    inject = ["can", "log"]

    def apply(self, ctx):
        can = ctx.get("can")
        log = ctx.get("log")
        cfg = ctx.config or {}
        can_id = cfg.get("can_id", 0x200)
        name = ctx.name  # 实例 key，如 "dji.0"

        motor = DjiMotorController(can, can_id, log, name)
        ctx.provide(ctx.name, motor)

        def setup():
            motor._dispose = can.on(can_id, motor.on_frame)

        def teardown():
            if motor._dispose:
                motor._dispose()

        ctx.effect(setup, teardown)
        ctx.setInterval(cfg.get("period", 0.5), motor.poll)
        log(f"✅ {name} 已挂载 (CAN {hex(can_id)})")