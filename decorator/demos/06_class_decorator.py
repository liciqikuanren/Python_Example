"""
========================================
 案例6：基于类的装饰器
========================================
除了用函数实现装饰器，还可以用类来实现。
类装饰器通过 __init__ 接收被装饰函数，
通过 __call__ 实现每次调用时的增强逻辑。
"""

import functools


class CountCalls:
    """
    类装饰器：统计函数被调用的次数。
    
    利用 __init__ 保存被装饰函数和计数器，
    利用 __call__ 使实例可被调用。
    functools.update_wrapper 负责复制元信息。
    """

    def __init__(self, func):
        self.func = func
        self.count = 0
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"[计数] {self.func.__name__} 已被调用 {self.count} 次")
        return self.func(*args, **kwargs)


@CountCalls
def say_hi():
    """打个招呼。"""
    print("  嗨!")


@CountCalls
def say_bye():
    """说再见。"""
    print("  拜拜!")


def main():
    print("=" * 50)
    print("  案例6：基于类的装饰器")
    print("=" * 50)
    print()
    print("--- 多次调用 say_hi ---")
    say_hi()
    say_hi()
    say_hi()
    print()
    print("--- 多次调用 say_bye ---")
    say_bye()
    say_bye()
    print()
    print(f"  say_hi 共被调用 {say_hi.count} 次")
    print(f"  say_bye 共被调用 {say_bye.count} 次")
    print()
    print("类装饰器的优点是可以用 self 维护状态（如计数器）。")


if __name__ == "__main__":
    main()
