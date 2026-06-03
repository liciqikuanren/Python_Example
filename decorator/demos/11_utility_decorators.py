"""
========================================
 案例11：实用装饰器综合演示
========================================
将前面学到的技巧组合成真实项目中常用的装饰器：
计时、权限校验、类型检查、单例、命令注册。
"""

import functools
import time


# ========== 11.1 @timer ==========

def timer(func):
    """
    计时装饰器：测量函数执行耗时。
    适用于性能分析和接口耗时监控。
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"[计时] {func.__name__} 耗时: {elapsed * 1000:.2f} ms")
        return result
    return wrapper


@timer
def slow_function():
    """模拟一个耗时操作。"""
    time.sleep(0.1)
    return "完成"


# ========== 11.2 @type_check ==========

def type_check(*expected_types):
    """
    类型检查装饰器：验证函数参数类型。
    
    用法:
        @type_check(int, str)
        def func(a, b): ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i, (arg, expected) in enumerate(zip(args, expected_types)):
                if not isinstance(arg, expected):
                    raise TypeError(
                        f"参数 {i} 期望 {expected.__name__}，"
                        f"实际得到 {type(arg).__name__}"
                    )
            return func(*args, **kwargs)
        return wrapper
    return decorator


@type_check(int, int)
def divide(a, b):
    """整数除法。"""
    return a / b


# ========== 11.3 @singleton ==========

def singleton(cls):
    """
    单例模式装饰器：确保类只有一个实例。
    
    原理：用字典缓存类 -> 实例的映射。
    后续调用直接返回已有实例。
    """
    instances = {}

    @functools.wraps(cls, updated=())
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
            print(f"[单例] 创建 {cls.__name__} 实例")
        else:
            print(f"[单例] 复用 {cls.__name__} 实例")
        return instances[cls]

    return get_instance


@singleton
class Config:
    """配置类（全局唯一）。"""

    def __init__(self, env="development"):
        self.env = env
        print(f"  初始化配置: {env}")

    def get(self, key):
        return f"{key}_value"


# ========== 11.4 命令注册表 ==========

COMMANDS = {}

def command(name=None):
    """
    命令注册装饰器：将函数注册为可调用的命令。
    类似 Click / argparse 等 CLI 框架的实现思路。
    """
    def decorator(func):
        cmd_name = name or func.__name__
        COMMANDS[cmd_name] = func

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


@command("hello")
def cmd_hello(name):
    """打招呼命令。"""
    print(f"  你好，{name}！")

@command()
def help():
    """帮助命令。"""
    print("  可用命令: " + ", ".join(COMMANDS.keys()))


def main():
    print("=" * 50)
    print("  案例11：实用装饰器综合演示")
    print("=" * 50)

    print("\n--- @timer 耗时测量 ---")
    result = slow_function()
    print(f"  返回: {result}")

    print("\n--- @type_check 类型校验 ---")
    print(f"  10 / 3 = {divide(10, 3)}")
    try:
        divide(10, "hello")
    except TypeError as e:
        print(f"  校验拦截: {e}")

    print("\n--- @singleton 单例模式 ---")
    c1 = Config("production")
    c2 = Config("development")
    print(f"  c1 is c2: {c1 is c2}")

    print("\n--- @command 命令注册 ---")
    help()
    COMMANDS["hello"]("世界")


if __name__ == "__main__":
    main()
