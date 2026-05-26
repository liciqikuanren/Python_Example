"""
异步版本的咖啡店模拟器（使用 asyncio）

场景和同步版一样：咖啡店接了3个订单，每个订单制作需要一定时间。
但这次用 asyncio 实现 — 制作一杯咖啡的等待时间里，可以去制作另一杯！

核心要点：
1. async def 定义异步函数（协程），替代普通 def 函数
2. await asyncio.sleep() 替代 time.sleep() —— 它是非阻塞的
3. asyncio.gather() 并发运行多个协程
4. 普通函数如何改造成 async 函数
5. 阻塞操作（如 time.sleep）必须替换为非阻塞版本
"""

import asyncio  # Python 标准异步库，提供事件循环、协程调度等


# ============================================================
# 异步函数定义
# ============================================================

async def make_drink(name: str, delay: float) -> str:
    """
    异步函数：制作饮品

    和同步版相比，这个函数有三个关键变化：

    【变化1】函数定义加了 async 关键字
        - async def 表示这是一个"异步函数"（也叫协程 coroutine）
        - 它不能像普通函数那样直接调用，必须用 await 或 asyncio.gather()
        - 直接调用 make_drink("咖啡", 2) 只会得到一个协程对象，不会执行！

    【变化2】time.sleep() 换成了 await asyncio.sleep()
        - time.sleep() 是阻塞的：整个程序停下来
        - asyncio.sleep() 是非阻塞的：告诉事件循环"我要等 delay 秒，
          这段时间你可以去跑别的任务"
        - await 关键字的意思是"等待这个异步操作完成，但允许切换到其他任务"

    【变化3】函数仍然是按顺序写的，但执行时可以"并发"
        - 代码看起来是线性的，但 await 点就是"让出控制权"的地方
        - 当事件循环遇到 await 时，会切换到另一个等待中的任务

    参数和返回值和同步版完全一样，只是加了 async/await 语法
    """
    print(f"  ☕ 开始制作 {name}，预计需要 {delay} 秒...")

    # 【关键区别】
    # time.sleep(delay)       ← 同步版：阻塞，整个程序冻结
    # await asyncio.sleep(delay)  ← 异步版：非阻塞，让出CPU去跑其他任务
    #
    # 你可以把 await asyncio.sleep() 理解为：
    # "我去等 delay 秒，但别闲着，帮我看看有没有其他任务要做"
    await asyncio.sleep(delay)

    print(f"  ✅ {name} 制作完成！")
    return f"{name}（耗时 {delay}s）"


# ============================================================
# 普通函数改造成 async 函数的示例
# ============================================================

def print_menu_sync() -> None:
    """
    普通函数：打印菜单（同步版）
    这是最常见的普通函数形式
    """
    print("  📜 今日菜单：")
    print("     美式咖啡 - ¥15")
    print("     抹茶拿铁 - ¥22")
    print("     柠檬红茶 - ¥18")


async def print_menu() -> None:
    """
    异步函数：打印菜单

    如何把普通函数改造成 async 函数？

    【方法】只需在 def 前面加 async，并在函数体中确保：
    1. 如果有耗时操作（sleep、网络请求等），替换为 await 版本
    2. 如果没有耗时操作（如纯打印），可以保留普通代码，
       但需要加一行 await asyncio.sleep(0) 来让出控制权

    这里 print() 本身没有耗时，所以不需要 await，
    但加上了 async 让它能被 await 调用
    """
    print("  📜 今日菜单：")
    print("     美式咖啡 - ¥15")
    print("     抹茶拿铁 - ¥22")
    print("     柠檬红茶 - ¥18")


# ============================================================
# 主函数
# ============================================================

async def main() -> None:
    """
    异步主函数

    和同步版相比的核心变化：

    【变化1】def main() → async def main()
        因为 main 内部需要 await 异步函数，所以它自己也必须是异步的

    【变化2】for 循环逐个调用 → asyncio.gather() 并发调用
        同步版：for order in orders: result = make_drink(...)  # 一个一个来
        异步版：results = await asyncio.gather(*tasks)         # 一起开始，谁先完事谁返回

    asyncio.gather() 的作用：
        - 接收多个协程对象作为参数
        - 把它们"打包"交给事件循环并发执行
        - 等所有协程都完成后，按输入顺序返回结果列表
        - 类似"同时开始所有任务，全部做完再汇总"
    """
    print("=" * 50)
    print("🏪 异步咖啡店 — 开门营业！")
    print("=" * 50)

    # 调用异步函数打印菜单（因为 main 是 async 的，所以可以 await）
    await print_menu()

    # 3个订单（和同步版一样）
    orders = [
        ("美式咖啡", 2.0),
        ("抹茶拿铁", 3.0),
        ("柠檬红茶", 1.5),
    ]

    print(f"\n📋 收到 {len(orders)} 个订单，同时开始制作...\n")

    # 记录开始时间
    start_time = asyncio.get_event_loop().time()

    # ========== 异步核心逻辑 ==========

    # 步骤1：创建所有任务（注意：这里还没开始执行！）
    # 直接把异步函数调用的结果放入列表，得到的是协程对象
    tasks = []
    for drink_name, delay in orders:
        # make_drink(drink_name, delay) 返回一个协程对象
        # 此时任务还没开始跑，只是创建好了"待执行"的对象
        task = make_drink(drink_name, delay)
        tasks.append(task)

    # 步骤2：用 gather() 并发执行所有任务
    # gather 会把所有任务交给事件循环，让它们"同时"开始运行
    # 当事件循环遇到 await asyncio.sleep() 时，
    # 会自动切换到另一个正在等待的任务
    #
    # 效果：3个订单"同时"开始制作，各自等待各自的时间
    # 总耗时 ≈ 最长的那个任务的时间（3.0 秒），而不是相加
    results = await asyncio.gather(*tasks)

    # 注：也可以用 asyncio.create_task() 来创建任务
    # 区别：
    #   gather(*tasks)    — 创建并等待全部完成，一次性提交
    #   create_task()     — 立即调度一个任务后台运行，可以单独取消或检查状态
    # ========== 异步结束 ==========

    # 计算总耗时
    total_time = asyncio.get_event_loop().time() - start_time

    # 打印汇总
    print("\n" + "=" * 50)
    print("📊 订单汇总：")
    for i, result in enumerate(results, 1):
        print(f"  订单{i}: {result}")
    print(f"\n⏱️  总耗时: {total_time:.2f} 秒")
    print("=" * 50)
    print("💡 可以看到：总耗时 ≈ 3.0 秒（最长的那个订单）")
    print("   因为所有订单是同时开始制作的！\n")


if __name__ == "__main__":
    # async 函数不能直接调用，必须通过 asyncio.run() 启动
    # asyncio.run() 的作用：
    #   1. 创建一个事件循环（Event Loop）
    #   2. 把 main() 交给事件循环执行
    #   3. 等 main() 完成后关闭事件循环
    #
    # 这是 Python 3.7+ 推荐的入口方式
    asyncio.run(main())
