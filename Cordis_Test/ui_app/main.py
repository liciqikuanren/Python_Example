"""
ui_app/main.py - 多插件仪器上位机仿真（PyQt6 + asyncio 双线程）

插件以独立文件放在 plugins/ 目录下，由 scan_plugins() 动态扫描加载。

插件拓扑（依赖方向）：
    config ──┐
    logger ──┼──▶ serial ──▶ temp、psu
             └────────────────▶ psu 提供 "psu" 服务 ──▶ alarm

事件流（一对多广播）：
    temp_reading ──▶ recorder + alarm + UI
    power_status  ──▶ recorder + UI
    alarm         ──▶ UI

线程模型：主线程跑 Qt（UI），后台线程跑 asyncio（业务），Qt 信号桥接。
"""

import asyncio
import importlib.util
import os
import sys
import threading
from pathlib import Path

# 让控制台按 UTF-8 输出，避免 Windows GBK 控制台打印 emoji 报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
PLUGINS_DIR = HERE / "plugins"
# mini_cordis 在上一级目录
sys.path.insert(0, str(HERE.parent))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from mini_cordis import Cordis, validate_plugin


def scan_plugins(directory: Path) -> list:
    """扫描目录，动态导入所有插件模块，返回插件实例列表。

    约定：每个模块暴露一个名为 Plugin 的类。
    """
    plugins = []
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            module_name = path.stem
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"无法为 {path} 创建模块规格")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin = module.Plugin()
            validate_plugin(plugin)
            plugins.append(plugin)
        except Exception as e:
            print(f"⚠️ 加载插件失败 {path.name}: {e}")
    return plugins


def run_backend(cordis: Cordis, stop: threading.Event):
    """后台线程：asyncio 事件循环里加载业务插件并跑 12 秒。"""

    async def main_async():
        plugins = scan_plugins(PLUGINS_DIR)
        # 乱序传入，load_all 会自动按依赖排序加载（含 ui，但 UI 已在主线程单独加载，会被去重跳过）
        cordis.load_all([
            p for p in plugins if p.name != "ui"
        ])

        # 运行 12 秒，观察数据流与告警
        await asyncio.sleep(12)

        # 拔出串口：级联卸载 alarm -> psu -> temp
        print("\n--- 拔出串口总线（级联卸载）---")
        await cordis.ctx.emit("system", "🔌 拔出串口总线，级联卸载温度/电源/告警插件")
        cordis.unload_plugin("serial")

        while not stop.is_set():
            await asyncio.sleep(0.1)

    asyncio.run(main_async())


def main():
    app = QApplication(sys.argv)
    cordis = Cordis()

    # 1. 主线程先加载 UI 插件（叶子，先订阅事件）
    ui = next(p for p in scan_plugins(PLUGINS_DIR) if p.name == "ui")
    cordis.load_plugin(ui)

    # 2. 后台线程跑业务插件
    stop = threading.Event()
    backend = threading.Thread(target=run_backend, args=(cordis, stop), daemon=True)
    backend.start()

    # 无头冒烟测试钩子：AUTO_QUIT_MS 可自动退出
    auto_quit = os.environ.get("AUTO_QUIT_MS")
    if auto_quit:
        QTimer.singleShot(int(auto_quit), app.quit)

    # 3. Qt 主循环
    app.aboutToQuit.connect(stop.set)
    code = app.exec()
    backend.join(timeout=2)
    return code


if __name__ == "__main__":
    raise SystemExit(main())