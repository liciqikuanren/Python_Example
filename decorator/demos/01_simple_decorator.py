"""
========================================
 案例1：最简单的装饰器
========================================
装饰器本质上是一个接收函数并返回新函数的高阶函数。
这个案例演示最基础的装饰器写法——在函数调用前后
插入额外操作，但不处理参数和返回值。
"""


def simple_decorator(func):
    """
    最简单的装饰器：在函数调用前后打印日志。
    
    参数：
        func: 被装饰的原始函数
    
    返回：
        wrapper 函数，在调用 func 前后执行额外操作
    """
    def wrapper():
        print("[装饰器] 在函数调用前执行额外操作")
        func()
        print("[装饰器] 在函数调用后执行额外操作")
    return wrapper


@simple_decorator
def say_hello():
    """一个简单的打招呼函数。"""
    print("  Hello, World!")


@simple_decorator
def say_goodbye():
    """一个简单的告别函数。"""
    print("  Goodbye!")


def main():
    print("=" * 50)
    print("  案例1：最简单的装饰器")
    print("=" * 50)
    print()
    say_hello()
    print()
    say_goodbye()
    print()
    print("装饰器 @simple_decorator 等价于:")
    print("  say_hello = simple_decorator(say_hello)")


if __name__ == "__main__":
    main()
