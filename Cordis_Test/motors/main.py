"""
motors/main.py - CAN 总线多电机系统动态演示（纯 asyncio 控制台）

演示内容：
1. 一台 USB-CAN 共享总线（can 插件 + 热插拔重连能力）
2. 同一总线上 DJI 与 DM 两种协议，各两台电机（dji_motor / dm_motor 多实例）
3. pump 插件分别控制 DJI（速度环）与 DM（位置环），运行中自动发现/降级
4. 断线重连：单台电机掉电（device 离线）、USB 拔出（总线离线）后各自自动恢复
5. 动态增删：运行中挂载 dji.2、卸载 dm.1
"""

import asyncio
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
PLUGINS_DIR = HERE / "plugins"
sys.path.insert(0, str(HERE.parent))

from mini_cordis import Cordis, scan_plugins


async def main():
    cordis = Cordis()

    # 扫描一次，按 name 取插件实例
    all_plugins = scan_plugins(PLUGINS_DIR)
    by_name = {p.name: p for p in all_plugins}

    # ---- 基础：日志 + 共享 CAN 总线 ----
    cordis.load_plugin(by_name["logger"])
    cordis.load_plugin(by_name["can"])

    # 拿到 can 服务，供后续模拟事件用
    can = cordis.ctx.get("can")

    # ---- 静态 2 DJI + 2 DM ----
    cordis.load_plugin(by_name["dji_motor"], key="dji.0", config={"can_id": 0x200})
    cordis.load_plugin(by_name["dji_motor"], key="dji.1", config={"can_id": 0x201})
    cordis.load_plugin(by_name["dm_motor"], key="dm.0", config={"can_id": 0x300})
    cordis.load_plugin(by_name["dm_motor"], key="dm.1", config={"can_id": 0x301})

    # ---- pump（应用层）：前缀扫描动态发现电机 ----
    cordis.load_plugin(by_name["pump"], config={"targets": [("dji.", 8), ("dm.", 8)]})

    await asyncio.sleep(2)

    # ---- 1. 单台电机掉电 -> 断线 -> 自动重连 ----
    print("\n=== ① dji.1 电机掉电 ===")
    can.set_device_online(0x201, False)
    await asyncio.sleep(4)
    print("\n=== ① dji.1 电机恢复 ===")
    can.set_device_online(0x201, True)
    await asyncio.sleep(4)

    # ---- 2. USB-CAN 拔出 -> 全部电机断线 -> 重新插入自动重连 ----
    print("\n=== ② USB-CAN 拔出 ===")
    can.sim_usb(False)
    await asyncio.sleep(4)
    print("\n=== ② USB-CAN 重新插入 ===")
    can.sim_usb(True)
    await asyncio.sleep(4)

    # ---- 3. 动态增删 ----
    print("\n=== ③ 动态挂载 dji.2 ===")
    cordis.load_plugin(by_name["dji_motor"], key="dji.2", config={"can_id": 0x202})
    await asyncio.sleep(3)
    print("\n=== ③ 动态卸载 dm.1 ===")
    cordis.unload_plugin("dm.1")
    await asyncio.sleep(3)

    print("\n主程序结束")


if __name__ == "__main__":
    asyncio.run(main())