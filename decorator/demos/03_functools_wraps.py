"""
========================================
 案例3：@functools.wraps 保留元信息
========================================
装饰器返回的 wrapper 函数会"覆盖"原函数，导致
__name__、__doc__、__module__ 等属性丢失。
@functools.wraps 可以将原函数的元信息复制到
wrapper 上，保持透明性。
"""

import functools


def bad_decorator(func):
    """没有使用 @functools.wraps 的装饰器。"""
    def wrapper(*args, **kwargs):
        """我是 wrapper 的文档字符串。"""
        print(f"[bad] 调用: {func.__name__}")
        return func(*args, **kwargs)
    return wrapper


def good_decorator(func):
    """使用了 @functools.wraps 的装饰器。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """我是 wrapper 的文档字符串。"""
        print(f"[good] 调用: {func.__name__}")
        return func(*args, **kwargs)
    return wrapper


@bad_decorator
def bad_greet(name):
    """向指定的人问好（bad 版本）。"""
    return f"你好, {name}!"


@good_decorator
def good_greet(name):
    """向指定的人问好（good 版本）。"""
    return f"你好, {name}!"


def main():
    print("=" * 50)
    print("  案例3：@functools.wraps 保留元信息")
    print("=" * 50)
    print()
    print("--- 未使用 @functools.wraps ---")
    print(f"  __name__: {bad_greet.__name__}")  # 输出 wrapper
    print(f"  __doc__:  {bad_greet.__doc__}")   # 输出 wrapper 的文档
    print()
    print("--- 使用 @functools.wraps ---")
    print(f"  __name__: {good_greet.__name__}")  # 输出 good_greet
    print(f"  __doc__:  {good_greet.__doc__}")   # 输出原始文档
    print()
    print("结论：始终使用 @functools.wraps(func) 是一个好习惯。")


if __name__ == "__main__":
    main()
