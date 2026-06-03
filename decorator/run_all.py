"""
运行所有装饰器演示案例。
用法: python run_all.py
"""

import subprocess
import sys
import os

demo_dir = os.path.join(os.path.dirname(__file__), "demos")

demo_files = sorted(
    f for f in os.listdir(demo_dir)
    if f.endswith(".py") and f != "__init__.py"
)

print("=" * 50)
print("  Python 装饰器 —— 全部案例演示")
print("=" * 50)
print()

for i, filename in enumerate(demo_files, 1):
    filepath = os.path.join(demo_dir, filename)
    print(f"\n{'=' * 50}")
    print(f"  运行案例 {i}/{len(demo_files)}: {filename}")
    print(f"{'=' * 50}")
    result = subprocess.run([sys.executable, filepath], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("错误:", result.stderr)

print("=" * 50)
print("  全部演示完成！")
print("=" * 50)
