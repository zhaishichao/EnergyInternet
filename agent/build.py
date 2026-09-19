"""组装子智能体与主控智能体。

6 个专职子智能体各司其职，主控 Supervisor 通过「子智能体即工具」实现
层级委派与多智能体协同，最终汇总输出。
"""
from __future__ import annotations

from agent.core import Agent, Supervisor, Tool
from data import mock_data as d


def _tool(name: str, desc: str, fn) -> Tool:
    return Tool(name=name, description=desc, func=fn)


# ---------------------------------------------------------------
# 子智能体
# ---------------------------------------------------------------
def load_forecaster() -> Agent:
    return Agent(
        name="load_forecaster",
        role="负荷预测与削峰填谷分析",
        system_prompt="擅长分析负荷曲线、识别峰谷时段，给出削峰填谷与需量管理建议。",
        tools=[
            _tool("get_load_curve", "获取区域典型日 24h 负荷曲线与峰谷特征。参数 region：园区A/园区B/工厂C。", d.get_load_curve),
            _tool("forecast_load", "预测区域明日 24h 负荷。参数 region 同上。", d.forecast_load),
        ],
    )


def renewable_agent() -> Agent:
    return Agent(
        name="renewable_agent",
        role="新能源出力预测与消纳分析",
        system_prompt="擅长分析光伏/风电出力特性与消纳情况，评估弃风弃光与绿电供应能力。",
        tools=[
            _tool("get_renewable_output", "获取区域光伏/风电 24h 出力与发电量。参数 region 同上。", d.get_renewable_output),
            _tool("get_load_curve", "获取区域典型日负荷曲线（用于匹配消纳）。参数 region 同上。", d.get_load_curve),
        ],
    )


def storage_agent() -> Agent:
    return Agent(
        name="storage_agent",
        role="储能充放电策略与峰谷套利",
        system_prompt="擅长制定储能充放电计划，在峰谷电价下最大化套利收益，并保证 SOC 在安全区间。",
        tools=[
            _tool("get_storage_status", "获取区域储能系统参数与当前 SOC。参数 region 同上。", d.get_storage_status),
            _tool("get_price_curve", "获取区域峰谷分时电价。参数 region 同上。", d.get_price_curve),
            _tool("get_load_curve", "获取区域负荷曲线。参数 region 同上。", d.get_load_curve),
            _tool("get_renewable_output", "获取区域新能源出力。参数 region 同上。", d.get_renewable_output),
        ],
    )


def dispatch_agent() -> Agent:
    return Agent(
        name="dispatch_agent",
        role="源网荷储协同调度与微电网优化",
        system_prompt="擅长统筹电源、电网、负荷、储能，输出协同调度方案，支撑虚拟电厂与微电网运行。",
        tools=[
            _tool("optimize_dispatch", "执行源网荷储协同调度计算，输出充放电计划、套利收益与削峰率。参数 region 同上。", d.optimize_dispatch),
            _tool("get_load_curve", "获取区域负荷曲线。参数 region 同上。", d.get_load_curve),
            _tool("get_renewable_output", "获取区域新能源出力。参数 region 同上。", d.get_renewable_output),
            _tool("get_storage_status", "获取储能系统状态。参数 region 同上。", d.get_storage_status),
            _tool("get_price_curve", "获取分时电价。参数 region 同上。", d.get_price_curve),
        ],
    )


def energy_saving_agent() -> Agent:
    return Agent(
        name="energy_saving_agent",
        role="能耗诊断与节能建议",
        system_prompt="擅长诊断用能结构、识别高耗能环节，给出可落地的节能改造与用能优化建议。",
        tools=[
            _tool("get_energy_consumption", "获取区域年度分项用电与节能提示。参数 region 同上。", d.get_energy_consumption),
            _tool("get_price_curve", "获取分时电价（用于评估移峰填谷价值）。参数 region 同上。", d.get_price_curve),
        ],
    )


def carbon_agent() -> Agent:
    return Agent(
        name="carbon_agent",
        role="碳排放核算与双碳路径",
        system_prompt="擅长碳排放核算、绿电匹配与减排路径规划，支撑碳达峰碳中和目标。",
        tools=[
            _tool("get_carbon_factors", "获取主要能源碳排放因子。", d.get_carbon_factors),
            _tool("get_energy_consumption", "获取区域年度分项用电。参数 region 同上。", d.get_energy_consumption),
            _tool("get_renewable_output", "获取区域新能源出力（用于绿电匹配）。参数 region 同上。", d.get_renewable_output),
        ],
    )


# ---------------------------------------------------------------
# 主控智能体
# ---------------------------------------------------------------
def build_supervisor() -> Supervisor:
    subagents = [
        load_forecaster(),
        renewable_agent(),
        storage_agent(),
        dispatch_agent(),
        energy_saving_agent(),
        carbon_agent(),
    ]
    return Supervisor(
        name="supervisor",
        role="能源互联网智能体总控",
        system_prompt=(
            "你是能源互联网智能体总控，面向「源网荷储」协同与能源节约场景，帮助用户优化电力与能源配置。\n"
            "工作方式：\n"
            "1. 概念性、知识性、纯问答类问题（如「什么是虚拟电厂」）请直接输出 finish 回答，不必调用工具；\n"
            "2. 需要数据或专业分析的能源问题，选择合适的子智能体委派（可委派多个再汇总）；\n"
            "3. 委派时给出清晰、具体的 task 指令，并在汇总时整合各子智能体的结论。"
        ),
        subagents=subagents,
    )


# 启动时构建一次（子智能体为无状态对象，可复用）
supervisor = build_supervisor()
