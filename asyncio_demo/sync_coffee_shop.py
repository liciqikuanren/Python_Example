"""
同步版本的咖啡店模拟器

场景：咖啡店同时接了3个顾客的订单（咖啡、茶、拿铁），
      每个订单制作都需要一定时间。
      同步方式会一个接一个地顺序完成，顾客只能干等。

核心要点：
1. time.sleep() 是阻塞式等待 —— 整个程序停下来，什么都不做
2. 每个任务必须等前一个完成后才能开始
3. 总耗时 = 所有任务耗时之和
"""

import time  # 提供 time.sleep() 来模拟耗时操作


def make_drink(name: str, delay: float) -> str:
    """
    普通函数：制作饮品

    参数：
        name:  饮品名称
        delay: 制作所需时间（秒）

    返回值：
        制作完成后的提示字符串

    注意：
        - 使用 time.sleep() 模拟制作过程中的等待
        - time.sleep() 是阻塞的：调用期间整个程序"冻结"，
          不能处理任何其他事情
        - 这就是同步编程的特点：一件事做完才能做下一件
    """
    print(f"  ☕ 开始制作 {name}，预计需要 {delay} 秒...")

    # time.sleep() 会阻塞整个程序，delay 秒内什么都干不了
    time.sleep(delay)

    print(f"  ✅ {name} 制作完成！")
    return f"{name}（耗时 {delay}s）"


def main() -> None:
    """
    主函数：模拟咖啡店接单制作

    同步方式的核心流程：
        按顺序调用 make_drink()，每个调用都会阻塞到完成为止
    """
    print("=" * 50)
    print("🏪 同步咖啡店 — 开门营业！")
    print("=" * 50)

    # 3个订单，每个都有制作时间
    orders = [
        ("美式咖啡", 2.0),
        ("抹茶拿铁", 3.0),
        ("柠檬红茶", 1.5),
    ]

    print(f"\n📋 收到 {len(orders)} 个订单，开始逐一制作...\n")

    # 记录开始时间，用于计算总耗时
    start_time = time.time()

    results = []  # 存放所有订单的完成结果

    # ========== 同步核心逻辑 ==========
    # 用 for 循环逐个处理订单，每个 make_drink 都是阻塞调用
    for drink_name, delay in orders:
        # 直接调用普通函数，程序会停在这里等它返回
        result = make_drink(drink_name, delay)
        # 只有上一个完成，才会执行下一次循环
        results.append(result)
    # ========== 同步结束 ==========

    # 计算总耗时
    total_time = time.time() - start_time

    # 打印汇总
    print("\n" + "=" * 50)
    print("📊 订单汇总：")
    for i, result in enumerate(results, 1):
        print(f"  订单{i}: {result}")
    print(f"\n⏱️  总耗时: {total_time:.2f} 秒")
    print("=" * 50)
    print("💡 可以看到：总耗时 = 2.0 + 3.0 + 1.5 = 6.5 秒左右")
    print("   因为每个订单都是做完一个才能开始下一个\n")


if __name__ == "__main__":
    # 当直接运行此脚本时（python sync_coffee_shop.py），
    # 执行 main() 函数
    main()
