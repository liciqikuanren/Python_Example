"""
========================================
 案例4：带参数的装饰器（装饰器工厂）
========================================
如果装饰器本身需要参数（如 @repeat(3)），则需要
再嵌套一层函数：
  外层函数接收装饰器参数
  中层函数（decorator）接收被装饰函数
  内层函数（wrapper）接收原函数参数
"""

import functools


def repeat(times=2):
    """
    装饰器工厂：让被装饰函数重复执行指定次数。
    
    参数：
        times: 重复执行次数（默认 2）
    
    返回：
        decorator 函数（真正的装饰器）
    
    用法：
        @repeat(3)
        def func(): ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(times):
                print(f"[重复] 第 {i + 1}/{times} 次执行:")
                func(*args, **kwargs)
            print(f"  -- 共执行 {times} 次 --")
        return wrapper
    return decorator


@repeat(times=3)
def print_message(msg):
    """打印一条消息。"""
    print(f"  消息: {msg}")


@repeat(times=5)
def say_hi(name):
    """打个招呼。"""
    print(f"  嗨, {name}!")


def main():
    print("=" * 50)
    print("  案例4：带参数的装饰器")
    print("=" * 50)
    print()
    print_message("今天天气真好！")
    print()
    say_hi("小红")
    print()
    print("原理: @repeat(times=3) 等价于 repeat(times=3)(func)")
    print("即: 先调用 repeat(times=3) 返回 decorator,")
    print("    再将 decorator(func) 返回的 wrapper 绑定到函数名。")


if __name__ == "__main__":
    main()
