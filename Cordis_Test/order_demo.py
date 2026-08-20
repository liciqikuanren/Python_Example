"""
order_demo.py - 案例：按依赖顺序自动加载 + 级联逆序卸载

依赖链：app → service → db（app 依赖 service，service 依赖 db）

1. load_all 乱序传入 [app, service, db]，框架自动按 db → service → app 加载
2. unload_plugin("db")：只点名卸载最底层的 db，
   框架自动级联卸载依赖它的 service、app（按 app → service → db 逆序）
"""

import asyncio
from mini_cordis import Cordis, Context


# ---------- 最底层：数据库 ----------
class DBPlugin:
    name = "db"
    inject = []

    def apply(self, ctx: Context):
        ctx.provide("db", "数据库连接")
        ctx.effect("db", lambda: None, lambda: print("  ↪ 卸载 db"))
        print("✅ db 已加载")


# ---------- 中间层：服务（依赖 db）----------
class ServicePlugin:
    name = "service"
    inject = ["db"]

    def apply(self, ctx: Context):
        ctx.provide("service", f"服务(基于 {ctx.get('db')})")
        ctx.effect("service", lambda: None, lambda: print("  ↪ 卸载 service"))
        print("✅ service 已加载")


# ---------- 顶层：应用（依赖 service）----------
class AppPlugin:
    name = "app"
    inject = ["service"]

    def apply(self, ctx: Context):
        ctx.effect("app", lambda: None, lambda: print("  ↪ 卸载 app"))
        print(f"✅ app 已加载，拿到: {ctx.get('service')}")


# ---------- 主程序 ----------
async def main():
    cordis = Cordis()

    print("--- load_all（故意乱序传入 [app, service, db]）---")
    cordis.load_all([AppPlugin(), DBPlugin(), ServicePlugin()])

    print("\n--- unload_plugin('db')：只卸载最底层，自动级联上层 ---")
    cordis.unload_plugin("service")


if __name__ == "__main__":
    asyncio.run(main())
