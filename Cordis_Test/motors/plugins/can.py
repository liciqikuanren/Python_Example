"""USB-CAN 适配器插件：提供共享 CAN 总线服务，自带热插拔重连能力。

- 所有协议（DJI/DM）共用这一路总线：电机用 can.on(can_id, handler) 订阅自己
  的帧，用 can.send(can_id, data) 发帧。
- USB 热插拔：main 里可用 can.sim_usb(False/True) 模拟拔出/重新插入。
  适配器自身的监视循环会感知 USB 链路变化，重新初始化总线（断线时收发失败，
  电机的心跳自然会检测到并各自重连）。

模拟约定：send() 成功且设备在线时，总线会"回帧"触发对应 can_id 的监听器；
设备离线（set_device_online(..., False)）则发而不回，用于模拟单台电机掉电。
"""

import asyncio


class CanBus:
    """共享 CAN 总线（模拟 USB-CAN 适配器）。"""

    def __init__(self):
        self.online = True          # 总线是否在线（USB 链路状态）
        self.usb_present = True     # 模拟的 USB 插入状态（由 sim_usb 控制）
        self._listeners = {}        # can_id -> [handler]
        self._muted = set()         # 模拟"设备不响应"的 can_id 集合

    # ---- 设备接口 ----
    def on(self, can_id: int, handler):
        """订阅某个 CAN ID 的回帧；返回解除订阅的 disposer。"""
        self._listeners.setdefault(can_id, []).append(handler)

        def off():
            listeners = self._listeners.get(can_id, [])
            if handler in listeners:
                listeners.remove(handler)

        return off

    def send(self, can_id: int, data: bytes) -> bool:
        """发送一帧。总线离线返回 False（发送失败）；设备离线则发出但无回帧。"""
        if not self.online:
            return False
        if can_id in self._muted:
            return True
        loop = asyncio.get_running_loop()
        loop.call_soon(self._deliver, can_id)
        return True

    def _deliver(self, can_id: int):
        for handler in self._listeners.get(can_id, []):
            try:
                handler({"id": can_id})
            except Exception as e:
                print(f"[can] 回帧处理出错: {e!r}")

    # ---- 模拟钩子（供 main 驱动演示） ----
    def set_device_online(self, can_id: int, flag: bool):
        """模拟某台设备在线/离线（如电机掉电）。"""
        if flag:
            self._muted.discard(can_id)
        else:
            self._muted.add(can_id)

    def sim_usb(self, present: bool):
        """模拟 USB 插入状态（true=插入）。拔插由插件监视循环处理。"""
        self.usb_present = present


class Plugin:
    name = "can"
    inject = ["log"]

    def apply(self, ctx):
        log = ctx.get("log")
        bus = CanBus()

        # USB 热插拔监视：检测 usb_present 变化，重新初始化总线
        def monitor():
            present = bus.usb_present
            if present == bus.online:
                return
            bus.online = present
            if present:
                log("🔌 USB-CAN 重新插入，总线重新初始化")
            else:
                log("🔌 USB-CAN 已拔出，总线离线")

        ctx.provide("can", bus)
        ctx.setInterval(0.1, monitor)
        ctx.effect(lambda: None, lambda: log("CAN 总线插件已移除"))
        log("🟢 USB-CAN 总线就绪")