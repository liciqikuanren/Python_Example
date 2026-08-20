"""
dynamic_load_demo.py - 案例：从外部目录动态加载插件（importlib）

- 扫描 plugins/ 目录下的 .py 文件，按文件名动态导入
- 每个插件模块约定暴露一个 Plugin 类
- 用 load_all 自动按依赖顺序加载（乱序扫描也没关系）
- 演示运行时卸载 + 重新从磁盘加载
"""

import asyncio
import importlib.util
from pathlib import Path

from mini_cordis import Cordis, validate_plugin

HERE = Path(__file__).parent
PLUGINS_DIR = HERE / "plugins"


def scan_plugins(directory: Path):
    """扫描目录，动态导入所有插件模块，返回插件实例列表"""
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
            plugin = module.Plugin()   # 约定：每个模块暴露 Plugin 类
            validate_plugin(plugin)    # 校验规范，不合格则跳过
            plugins.append(plugin)
        except Exception as e:
            print(f"⚠️ 加载插件失败 {path.name}: {e}")
    return plugins


async def main():
    cordis = Cordis()

    print("--- 动态扫描 plugins/ 目录并加载 ---")
    plugins = scan_plugins(PLUGINS_DIR)
    cordis.load_all(plugins)   # 自动按依赖顺序加载

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
