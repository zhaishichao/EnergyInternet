"""框架与数据逻辑测试（不依赖真实大模型，用 StubLLM 验证全链路）。

运行：python tests/test_agent.py   或   pytest tests/
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent.core as core
from agent.build import build_supervisor
from agent.core import parse_json
from data import mock_data as d


# ---------------------------------------------------------------
# 模拟 LLM：按智能体名返回预设的工具调用脚本，验证 ReAct 循环
# ---------------------------------------------------------------
class StubLLM:
    def __init__(self, plans: dict):
        self.plans = plans  # {agent_name: [(tool_name, args), ...]}
        self.calls = {}  # {agent_name: 已调用工具次数}

    def _agent(self, messages) -> str:
        sys_msg = messages[0]["content"]
        for name in self.plans:
            if f"「{name}」" in sys_msg:
                return name
        return ""

    async def complete(self, messages) -> str:
        name = self._agent(messages)
        seq = self.plans.get(name, [])
        called = self.calls.get(name, 0)
        if called < len(seq):
            tool, args = seq[called]
            self.calls[name] = called + 1
            return json.dumps({"action": "tool", "tool": tool, "args": args}, ensure_ascii=False)
        return json.dumps({"action": "finish", "plan": "完成"}, ensure_ascii=False)

    async def stream(self, messages):
        for ch in ["结论", "（", "测试", "）"]:
            yield ch


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------
def test_parse_json():
    assert parse_json('{"action":"tool","tool":"x","args":{"a":1}}')["tool"] == "x"
    assert parse_json('```json\n{"action":"finish"}\n```')["action"] == "finish"
    assert parse_json('好的。{"action":"finish","plan":"p"} 以上')["plan"] == "p"
    assert parse_json("乱码") == {}


def test_mock_data():
    curve = d.load_curve("园区A")
    assert len(curve) == 24 and max(curve) == 120.0
    assert d.get_price_curve("园区A").startswith("区域")
    assert "储能" in d.get_storage_status("园区A")
    out = d.optimize_dispatch("园区A")
    assert "削峰" in out and "套利" in out
    assert set(d.get_overview("园区A")) >= {"load", "pv", "wind", "price", "pv_cap", "wind_cap"}


def test_agent_tool_loop():
    """单个子智能体：调用领域工具 → 合成答案 → 发出事件。"""
    async def _t():
        core.llm = StubLLM({"load_forecaster": [("get_load_curve", {"region": "园区A"})]})
        agent = build_supervisor().subagents[0]  # load_forecaster
        events = []

        async def emit(e):
            events.append(e)

        answer = await agent.run("分析园区A负荷", emit, stream_text=True)
        assert answer == "结论（测试）"
        types = [e["type"] for e in events]
        assert types.count("tool") == 1 and "tool_result" in types and "text" in types

    run(_t())


def test_supervisor_delegation():
    """主控智能体：委派子智能体（subAgent），子智能体再调用工具。"""
    async def _t():
        core.llm = StubLLM({
            "supervisor": [("ask_load_forecaster", {"task": "预测园区A负荷"})],
            "load_forecaster": [("forecast_load", {"region": "园区A"})],
        })
        supervisor = build_supervisor()
        events = []

        async def emit(e):
            events.append(e)

        answer = await supervisor.run("帮我预测园区A的负荷", emit, stream_text=True)
        assert answer == "结论（测试）"
        tools = [e for e in events if e["type"] == "tool"]
        # 主控调用 ask_load_forecaster，子智能体调用 forecast_load
        assert any(e["tool"] == "ask_load_forecaster" for e in tools)
        assert any(e["tool"] == "forecast_load" for e in tools)
        assert any(e["type"] == "text" for e in events)

    run(_t())


def test_supervisor_registry():
    """主控应注册 6 个子智能体委派工具。"""
    sup = build_supervisor()
    assert len(sup.subagents) == 6
    assert {t.name for t in sup.tools} == {f"ask_{a.name}" for a in sup.subagents}


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 个测试通过。")
