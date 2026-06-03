"""
========================================
 案例2：处理参数和返回值
========================================
实际函数通常有参数和返回值。通用的装饰器需要使用
*args 和 **kwargs 来接收任意参数，并返回原函数的
执行结果。
"""


def logging_decorator(func):
    """
    通用日志装饰器：记录函数的调用信息、参数和返回值。
    
    使用 *args 接收任意数量位置参数，
    使用 **kwargs 接收任意数量关键字参数，
    用变量 result 保存返回值并返回。
    """
    def wrapper(*args, **kwargs):
        print(f"[日志] 调用函数: {func.__name__}")
        print(f"[日志] 位置参数: {args}")
        print(f"[日志] 关键字参数: {kwargs}")
        result = func(*args, **kwargs)
        print(f"[日志] 返回值: {result!r}")
        return result
    return wrapper


@logging_decorator
def add(a, b):
    """计算两数之和。"""
    return a + b


@logging_decorator
def greet(name, greeting="你好"):
    """向指定的人问好。"""
    return f"{greeting}, {name}!"


def main():
    print("=" * 50)
    print("  案例2：处理参数和返回值")
    print("=" * 50)
    print()
    result = add(3, 5)
    print(f"  add 结果: {result}")
    print()
    result = greet("小明", greeting="Hello")
    print(f"  greet 结果: {result}")
    print()
    print("关键：wrapper(*args, **kwargs) 接收所有参数，")
    print("再用 result = func(*args, **kwargs) 调用原函数并保留返回值。")


if __name__ == "__main__":
    main()
