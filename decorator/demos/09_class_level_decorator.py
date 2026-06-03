"""
========================================
 案例9：装饰器装饰整个类
========================================
装饰器不仅可以装饰函数，还可以装饰类。
类装饰器接收一个类，返回一个（通常是增强后的）类。
常见用途：自动添加方法、注册类、修改属性等。
"""


def add_repr(cls):
    """
    类装饰器：为类自动添加 __repr__ 方法。
    
    参数：
        cls: 被装饰的类
    
    返回：
        增加了 __repr__ 的同一个类
    """
    def __repr__(self):
        items = ", ".join(
            f"{k}={v!r}" for k, v in self.__dict__.items()
        )
        return f"{cls.__name__}({items})"

    cls.__repr__ = __repr__
    return cls


# ----- 示例：注册表类装饰器 -----

REGISTRY = {}

def register_class(name=None):
    """
    类装饰器工厂：将类自动注册到全局注册表中。
    常用于插件系统、ORM 模型注册、配置项等。
    """
    def decorator(cls):
        key = name or cls.__name__
        REGISTRY[key] = cls
        print(f"[注册] '{key}' -> {cls.__name__}")
        return cls
    return decorator


@add_repr
class Point:
    """二维坐标点。"""

    def __init__(self, x, y):
        self.x = x
        self.y = y


@add_repr
class Person:
    """人物类。"""

    def __init__(self, name, age):
        self.name = name
        self.age = age


@register_class("json_parser")
class JsonHandler:
    pass


@register_class()
class XmlHandler:
    pass


def main():
    print("=" * 50)
    print("  案例9：装饰器装饰整个类")
    print("=" * 50)
    print()
    print("--- @add_repr 自动生成 __repr__ ---")
    p = Point(3.5, 7.2)
    print(f"  {p!r}")
    person = Person("张三", 28)
    print(f"  {person!r}")
    print()
    print("--- @register_class 自动注册 ---")
    print(f"  注册表: {REGISTRY}")
    print()
    print("类装饰器的典型应用:")
    print("  - 自动添加 __repr__ / __str__")
    print("  - 注册到工厂/插件系统")
    print("  - 数据验证 / ORM 模型映射")
    print("  - 单例模式")


if __name__ == "__main__":
    main()
