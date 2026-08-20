"""
db_demo.py - 案例：服务断开时的优雅降级（策略 2：断开发事件，依赖方降级）

依赖链：App(A) → Service(B) → Database(C)

- C 运行 5 秒后模拟断线，emit "db_down"
- B 收到后降级（healthy=False），并继续 emit "service_down"
- A 收到后停止工作

三层依次优雅退场，而不是等到 A 调用失效服务时才崩溃。
"""

import asyncio
from mini_cordis import Cordis, Context


# ---------- 插件 0：Logger 服务 ----------
class LoggerPlugin:
    name = "logger"
    inject = []

    def apply(self, ctx: Context):
        def log(msg: str):
            print(f"[LOG] {msg}")

        ctx.provide("log", log)
        print("✅ Logger 插件已加载")


# ---------- 插件 C：数据库（最底层服务）----------
class DatabasePlugin:
    name = "database"
    inject = []

    def apply(self, ctx: Context):
        loop = asyncio.get_running_loop()
        state = {"alive": True}   # 可变容器，闭包里改它不需要 nonlocal
        task = None

        def query(sql: str) -> str:
            # 策略 1 的基础：失效时明确报错，而不是返回垃圾数据
            if not state["alive"]:
                raise RuntimeError("数据库已断开")
            return f"[DB结果] {sql}"

        ctx.provide("query", query)

        async def monitor():
            # 模拟运行 5 秒后数据库突然断线
            await asyncio.sleep(5)
            state["alive"] = False
            await ctx.emit("db_down", "连接超时")   # ← 广播「我挂了」

        def setup():
            nonlocal task
            task = loop.create_task(monitor())

        def teardown():
            nonlocal task
            if task is not None:
                task.cancel()

        ctx.effect("database", setup, teardown)
        print("✅ Database 插件已加载（5 秒后模拟断线）")


# ---------- 插件 B：服务层（依赖 C）----------
class ServicePlugin:
    name = "service"
    inject = ["query", "log"]

    def apply(self, ctx: Context):
        query = ctx.get("query")
        log = ctx.get("log")
        healthy = {"on": True}

        def get_data() -> str:
            if not healthy["on"]:
                raise RuntimeError("服务已降级，无法提供数据")
            return query("SELECT * FROM users")

        ctx.provide("get_data", get_data)

        async def on_db_down(reason):
            healthy["on"] = False                       # ← 降级
            log(f"⚠️ B 收到 db_down({reason})，服务降级")
            await ctx.emit("service_down", "上游数据库断开")  # ← 继续向下游广播

        ctx.on("db_down", on_db_down)
        print("✅ Service 插件已加载")


# ---------- 插件 A：应用层（依赖 B）----------
class AppPlugin:
    name = "app"
    inject = ["get_data", "log"]

    def apply(self, ctx: Context):
        get_data = ctx.get("get_data")
        log = ctx.get("log")
        loop = asyncio.get_running_loop()
        running = True
        task = None

        async def work():
            nonlocal running
            while running:
                try:
                    log(f"📦 A 获取数据: {get_data()}")
                except RuntimeError as e:
                    log(f"❌ A 调用失败: {e}")
                await asyncio.sleep(2)

        def setup():
            nonlocal task
            task = loop.create_task(work())

        def teardown():
            nonlocal running, task
            running = False
            if task is not None:
                task.cancel()

        ctx.effect("app", setup, teardown)

        async def on_service_down(reason):
            nonlocal running
            running = False
            log(f"🛑 A 收到 service_down({reason})，停止工作")

        ctx.on("service_down", on_service_down)
        print("✅ App 插件已加载")


# ---------- 主程序 ----------
async def main():
    cordis = Cordis()

    # 按依赖链 C → B → A 顺序加载
    cordis.load_plugin(LoggerPlugin())
    cordis.load_plugin(DatabasePlugin())
    cordis.load_plugin(ServicePlugin())
    cordis.load_plugin(AppPlugin())

    # 运行 8 秒，观察断线 → 级联降级的全过程
    await asyncio.sleep(8)
    print("主程序结束")


if __name__ == "__main__":
    asyncio.run(main())
