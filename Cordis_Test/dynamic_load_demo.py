"""
dynamic_load_demo.py - 案例：从外部目录动态加载插件（框架内置 scan_plugins / load_dir）

- 用 cordis.load_dir 扫描 plugins/ 目录，自动按依赖顺序加载（乱序扫描也没关系）
- load_dir 内部复用框架的 scan_plugins（约定每个模块暴露 Plugin 类并校验）
- 演示运行时卸载 + 重新从磁盘加载
"""

import asyncio
import importlib.util
from pathlib import Path

from mini_cordis import Cordis, scan_plugins

HERE = Path(__file__).parent
PLUGINS_DIR = HERE / "plugins"


async def main():
    cordis = Cordis()

    print("--- load_dir 扫描 plugins/ 目录并加载 ---")
    loaded = cordis.load_dir(PLUGINS_DIR)
    print(f"已加载: {loaded}")

    print("\n--- 运行 3 秒后触发 greet 事件 ---")
    await asyncio.sleep(3)
    await cordis.ctx.emit("greet", "Hello from dynamic load!")

    print("\n--- 运行中卸载 timer 插件 ---")
    await asyncio.sleep(4)
    cordis.unload_plugin("timer")

    print("\n--- 重新从磁盘加载 timer 插件 ---")
    fresh = scan_plugins(PLUGINS_DIR)
    timer = next(p for p in fresh if p.name == "timer")
    cordis.load_plugin(timer)

    await asyncio.sleep(4)
    print("主程序结束")


if __name__ == "__main__":
    asyncio.run(main())