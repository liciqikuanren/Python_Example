"""
========================================
 案例10：Python 内置装饰器
========================================
Python 自带了一些非常有用的装饰器，掌握它们
可以写出更简洁、更 Pythonic 的代码。
"""

import functools
from dataclasses import dataclass


# ========== 10.1 @staticmethod ==========

class MathUtils:
    """数学工具类。"""

    @staticmethod
    def add(a, b):
        """静态方法：两数相加，不依赖实例状态。"""
        return a + b

    @staticmethod
    def multiply(a, b):
        """静态方法：两数相乘。"""
        return a * b


# ========== 10.2 @classmethod ==========

class Counter:
    """计数器类，演示类方法和类属性。"""
    total = 0  # 类属性，所有实例共享

    def __init__(self, name):
        self.name = name
        Counter.total += 1

    @classmethod
    def from_string(cls, data):
        """类方法：从字符串创建实例。"""
        name = data.strip().upper()
        return cls(name)

    @classmethod
    def get_total(cls):
        """类方法：获取总实例数。"""
        return cls.total


# ========== 10.3 @property ==========

class Temperature:
    """温度类，演示 @property 的 getter/setter。"""

    def __init__(self, celsius=0):
        self._celsius = celsius  # _ 前缀表示内部属性

    @property
    def celsius(self):
        """摄氏度 getter。"""
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        """摄氏度 setter（带校验）。"""
        if value < -273.15:
            raise ValueError("温度不能低于绝对零度 (-273.15°C)")
        self._celsius = value

    @property
    def fahrenheit(self):
        """华氏度（只读，由摄氏度计算得出）。"""
        return self._celsius * 9 / 5 + 32

    def __repr__(self):
        return f"Temperature({self._celsius:.1f}°C / {self.fahrenheit:.1f}°F)"


# ========== 10.4 @dataclass ==========

@dataclass
class Book:
    """数据类装饰器自动生成 __init__、__repr__、__eq__。"""
    title: str
    author: str
    year: int
    price: float = 0.0


# ========== 10.5 @functools.lru_cache ==========

@functools.lru_cache(maxsize=128)
def fibonacci(n):
    """
    带缓存的斐波那契数列计算。
    @lru_cache 自动缓存函数结果，避免重复计算。
    没有缓存时 fib(35) 需要数千万次递归调用。
    """
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def main():
    print("=" * 50)
    print("  案例10：Python 内置装饰器")
    print("=" * 50)

    print("\n--- @staticmethod ---")
    print(f"  3 + 4 = {MathUtils.add(3, 4)}")
    print(f"  5 * 6 = {MathUtils.multiply(5, 6)}")
    print("  静态方法无需实例即可调用")

    print("\n--- @classmethod ---")
    c1 = Counter("a")
    c2 = Counter("b")
    c3 = Counter.from_string("  c  ")
    print(f"  总实例数: {Counter.get_total()}")

    print("\n--- @property ---")
    t = Temperature(25)
    print(f"  初始: {t}")
    t.celsius = 30
    print(f"  修改后: {t}")
    print(f"  华氏度: {t.fahrenheit:.1f}°F")
    try:
        t.celsius = -300  # 触发校验
    except ValueError as e:
        print(f"  校验生效: {e}")

    print("\n--- @dataclass ---")
    book = Book(title="Python 编程", author="张三", year=2024, price=59.0)
    book2 = Book(title="Python 编程", author="张三", year=2024, price=59.0)
    print(f"  {book}")
    print(f"  book == book2: {book == book2}  (自动生成 __eq__)")

    print("\n--- @functools.lru_cache ---")
    import time
    start = time.perf_counter()
    result = fibonacci(35)
    elapsed = time.perf_counter() - start
    print(f"  fibonacci(35) = {result}")
    print(f"  耗时: {elapsed * 1000:.3f} ms")
    print("  lru_cache 让重复递归调用几乎零开销")


if __name__ == "__main__":
    main()
