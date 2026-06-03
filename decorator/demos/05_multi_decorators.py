"""
========================================
 案例5：多个装饰器叠加
========================================
多个装饰器可以叠加使用，顺序是：
  @outer
  @inner
  def func(): ...
等价于 func = outer(inner(func))

即装饰器从下往上"应用"，执行时从上往下"包裹"。
"""

import functools


def bold(func):
    """给文本加粗。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return f"<b>{result}</b>"
    return wrapper


def italic(func):
    """给文本添加斜体。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return f"<i>{result}</i>"
    return wrapper


def underline(func):
    """给文本添加下划线。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return f"<u>{result}</u>"
    return wrapper


@bold
@italic
@underline
def format_text(text):
    """先加下划线，再加斜体，最后加粗。"""
    return text


def main():
    print("=" * 50)
    print("  案例5：多个装饰器叠加")
    print("=" * 50)
    print()
    result = format_text("Hello, World!")
    print(f"  结果: {result}")
    print()
    print("装饰顺序（从下到上）:")
    print("  1. @underline  -> <u>text</u>")
    print("  2. @italic     -> <i><u>text</u></i>")
    print("  3. @bold       -> <b><i><u>text</u></i></b>")
    print()
    print("执行顺序（从上到下）:")
    print("  bold -> italic -> underline -> 原函数")


if __name__ == "__main__":
    main()
