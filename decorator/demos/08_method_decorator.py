"""
========================================
 案例8：装饰器用于类方法
========================================
装饰器同样适用于类中的实例方法和类方法。
注意：实例方法的第一个参数是 self（或 cls），
它和其他参数一样通过 *args 传递。
"""

import functools


def method_logger(func):
    """
    用于类方法的日志装饰器。
    在类方法中，args[0] 就是 self（实例本身）。
    这里用 type(self).__name__ 获取类名。
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        print(f"[方法日志] 调用 {type(self).__name__}.{func.__name__}")
        return func(self, *args, **kwargs)
    return wrapper


class ShoppingCart:
    """购物车类。"""

    def __init__(self):
        self.items = []

    @method_logger
    def add_item(self, item):
        """添加商品。"""
        self.items.append(item)
        print(f"  + 添加: {item}")

    @method_logger
    def remove_item(self, item):
        """移除商品。"""
        if item in self.items:
            self.items.remove(item)
            print(f"  - 移除: {item}")
        else:
            print(f"  ! 未找到: {item}")

    def show_items(self):
        """显示购物车（未加装饰器，作为对照）。"""
        print(f"  购物车: {self.items}")


def main():
    print("=" * 50)
    print("  案例8：装饰器用于类方法")
    print("=" * 50)
    print()
    cart = ShoppingCart()
    cart.add_item("苹果")
    cart.add_item("香蕉")
    cart.add_item("橘子")
    cart.show_items()
    print()
    cart.remove_item("香蕉")
    cart.show_items()
    print()
    print("注意：@method_logger 的 wrapper(self, *args, **kwargs)")
    print("中显式写了 self 参数，这样更清晰。也可以只用 *args，")


if __name__ == "__main__":
    main()
