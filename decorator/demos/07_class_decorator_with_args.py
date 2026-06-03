"""
========================================
 案例7：带参数的类装饰器
========================================
类装饰器也可以带参数：__init__ 接收装饰器参数，
__call__ 接收被装饰函数并返回 wrapper。
常用于重试、超时、限流等场景。
"""

import functools
import time


class Retry:
    """
    类装饰器（带参数）：函数执行失败时自动重试。
    
    用法:
        @Retry(max_attempts=3, delay=0.5)
        def func(): ...
    """

    def __init__(self, max_attempts=3, delay=0.5):
        """
        参数：
            max_attempts: 最大重试次数（默认 3）
            delay: 每次重试间隔秒数（默认 0.5）
        """
        self.max_attempts = max_attempts
        self.delay = delay

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, self.max_attempts + 1):
                try:
                    print(f"  尝试第 {attempt} 次...")
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    print(f"  失败: {e}")
                    if attempt < self.max_attempts:
                        time.sleep(self.delay)
            print(f"  已超过最大重试次数 ({self.max_attempts})")
            raise last_exception
        return wrapper


# 用于演示的计数器
attempt_counter = 0


@Retry(max_attempts=4, delay=0.1)
def fetch_data():
    """
    模拟一个不稳定的数据获取函数。
    前 2 次调用会失败，第 3 次成功。
    """
    global attempt_counter
    attempt_counter += 1
    if attempt_counter < 3:
        raise ConnectionError("网络连接超时")
    return "数据获取成功!"


def main():
    global attempt_counter

    print("=" * 50)
    print("  案例7：带参数的类装饰器")
    print("=" * 50)
    print()
    print("模拟不稳定网络调用（前 2 次失败，第 3 次成功）:")
    print()
    attempt_counter = 0
    result = fetch_data()
    print(f"\n  最终结果: {result}")
    print()
    print("重试装饰器适用于:")
    print("  - 网络请求失败重试")
    print("  - 数据库连接重试")
    print("  - 文件读写重试")
    print("  - 任何临时性故障恢复")


if __name__ == "__main__":
    main()
