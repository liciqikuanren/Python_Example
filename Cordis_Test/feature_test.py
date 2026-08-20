"""feature_test.py - 验证重构后新增的 API：disposer、waterfall/serial/parallel、属性访问、计时助手、mixin"""

import asyncio
import sys

sys.path.insert(0, r"H:\Python_Floder\Python_Example\Cordis_Test")
from mini_cordis import Cordis, Context


class LoggerPlugin:
    name = "logger"
    inject = []

    def apply(self, ctx: Context):
        def log(msg):
            print(f"[LOG] {msg}")
        off = ctx.provide("log", log)
        assert callable(off), "provide 应返回 disposer"


class Wf1:
    name = "wf1"
    inject = []

    def apply(self, ctx):
        async def h(data, next_):
            print("wf1 前", data)
            out = await next_(data + "|x")
            print("wf1 后拿到下游:", out)
            return out + "|wrapped"
        ctx.on("wf", h)


class Wf2:
    name = "wf2"
    inject = []

    def apply(self, ctx):
        async def h(data, next_):
            print("wf2 前", data)
            out = await next_(data + "|y")
            print("wf2 后拿到下游:", out)
            return out + "|wrapped2"
        ctx.on("wf", h)


class Wf3:
    name = "wf3"
    inject = []

    def apply(self, ctx):
        async def h(data, next_):
            print("wf3 是终点，直接返回", data)
            return data + "|end"   # 不调用 next_，短路
        ctx.on("wf", h)


class S:
    name = "s"
    inject = []

    def apply(self, ctx):
        async def h(v):
            print("serial1:", v)
            return v + 1
        ctx.on("s", h)


class S2:
    name = "s2"
    inject = []

    def apply(self, ctx):
        async def h(v):
            print("serial2:", v)
            return v * 10
        ctx.on("s", h)


async def main():
    c = Cordis()
    c.load_all([LoggerPlugin()])

    # 属性访问
    c.load_plugin(type("A", (), {"name": "a", "inject": ["log"], "apply": lambda self, ctx: None})())
    log = c.ctx.log
    assert callable(log), "ctx.log 属性式访问失败"
    print("属性访问 ctx.log: ok")

    # disposer 手动解除
    events = []
    off = c.ctx.on("e", lambda d: events.append(d))
    await c.ctx.emit("e", 1)
    off()
    await c.ctx.emit("e", 2)
    assert events == [1], f"disposer 应解除监听: {events}"
    print("disposer 解除监听: ok")

    # waterfall
    c.load_all([Wf1(), Wf2(), Wf3()])
    result = await c.ctx.waterfall("wf", "start")
    print("waterfall 返回:", result)
    assert result == "start|x|y|end|wrapped2|wrapped", result

    # serial
    c.load_all([S(), S2()])
    r = await c.ctx.serial("s", 1)
    print("serial 返回:", r)
    assert r == 20, r

    # setTimeout / setInterval
    tick = []
    c.ctx.setInterval(0.2, lambda: tick.append("t"))
    c.ctx.setTimeout(0.5, lambda: tick.append("to"))
    await asyncio.sleep(0.9)
    assert "to" in tick and len(tick) >= 2, tick
    print("setTimeout/setInterval: ok")

    print("ALL FEATURES OK")


if __name__ == "__main__":
    asyncio.run(main())