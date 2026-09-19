"""能源领域模拟数据与工具函数。

数据贴近我国电力系统现状：峰谷电价、新能源渗透、双碳目标等。
所有函数均为纯函数（同步、无副作用），后续可替换为真实数据接口
（如 SCADA / 电力交易中心 / 用能监测平台），无需改动 Agent 框架。
"""
from __future__ import annotations

from typing import Dict, List, Tuple

# ---------------------------------------------------------------
# 区域定义
# ---------------------------------------------------------------
REGIONS: Dict[str, Dict] = {
    "园区A": {"类型": "产业园区", "负荷峰值MW": 120, "光伏装机MWp": 40, "风电装机MW": 18},
    "园区B": {"类型": "商业综合体", "负荷峰值MW": 80, "光伏装机MWp": 25, "风电装机MW": 6},
    "工厂C": {"类型": "离散制造工厂", "负荷峰值MW": 60, "光伏装机MWp": 15, "风电装机MW": 0},
}

# 典型日 24h 负荷形状（双峰：早峰 + 晚峰，归一化到峰值）
LOAD_PROFILE = [
    0.45, 0.42, 0.40, 0.39, 0.40, 0.45,
    0.60, 0.75, 0.85, 0.92, 0.95, 0.90,
    0.85, 0.80, 0.78, 0.76, 0.78, 0.88,
    0.98, 1.00, 0.95, 0.85, 0.70, 0.55,
]

# 光伏出力形状（白天钟形，归一化到装机容量）
PV_PROFILE = [
    0, 0, 0, 0, 0, 0.05, 0.15, 0.30, 0.48, 0.65, 0.80, 0.88,
    0.90, 0.85, 0.75, 0.60, 0.42, 0.25, 0.10, 0.02, 0, 0, 0, 0,
]

# 风电出力形状（波动，归一化到装机容量）
WIND_PROFILE = [
    0.55, 0.60, 0.62, 0.58, 0.50, 0.45, 0.40, 0.38, 0.35, 0.33, 0.36, 0.40,
    0.44, 0.50, 0.55, 0.58, 0.62, 0.66, 0.70, 0.72, 0.68, 0.64, 0.60, 0.57,
]

# 峰谷电价（元/kWh）：谷 / 平 / 峰 / 尖峰
PRICE = (
    [0.32] * 7 +            # 00-06 谷
    [0.68] +                # 07 平
    [1.05] * 3 +            # 08-10 峰
    [1.30] * 2 +            # 11-12 尖峰
    [1.05] * 6 +            # 13-18 峰
    [1.30] * 2 +            # 19-20 尖峰
    [1.05] + [0.68] + [0.32]  # 21 峰 / 22 平 / 23 谷
)

# 园区储能系统参数
STORAGE = {"额定容量MWh": 20, "额定功率MW": 5, "当前SOC": 0.4, "充放电效率": 0.92, "最低SOC": 0.1}

# 年度分项用电（万 kWh）及节能提示
ENERGY: Dict[str, List[Tuple[str, int, str]]] = {
    "园区A": [
        ("暖通空调", 5040, "占比偏高，建议优化制冷策略与冰蓄冷"),
        ("生产设备", 3600, ""),
        ("数据中心", 2160, "PUE 1.8，有液冷/自然冷源优化空间"),
        ("照明", 960, "可改造 LED + 智能控制"),
        ("水泵/风机", 240, "可上变频调速"),
    ],
    "园区B": [
        ("暖通空调", 2700, "商业综合体空调占主导，可做负荷聚合参与需求响应"),
        ("照明", 1200, "可加装传感器联动"),
        ("电梯/动力", 900, ""),
        ("数据中心", 600, ""),
        ("其它", 600, ""),
    ],
    "工厂C": [
        ("生产设备", 5400, "离散制造，可做分时排产移峰"),
        ("空压机", 1350, "泄漏率高，建议改造"),
        ("暖通空调", 900, ""),
        ("照明", 675, ""),
        ("其它", 675, ""),
    ],
}

# 碳排放因子（kgCO2/kWh）
CARBON_FACTORS = {
    "电网平均": 0.5703,
    "燃煤发电": 0.892,
    "天然气": 0.202,
    "光伏(全生命周期)": 0.048,
    "风电(全生命周期)": 0.011,
    "绿电": 0.0,
}


# ---------------------------------------------------------------
# 基础曲线
# ---------------------------------------------------------------
def load_curve(region: str) -> List[float]:
    peak = REGIONS[region]["负荷峰值MW"]
    return [round(peak * r, 1) for r in LOAD_PROFILE]


def pv_curve(region: str) -> List[float]:
    cap = REGIONS[region]["光伏装机MWp"]
    return [round(cap * r, 1) for r in PV_PROFILE]


def wind_curve(region: str) -> List[float]:
    cap = REGIONS[region]["风电装机MW"]
    return [round(cap * r, 1) for r in WIND_PROFILE]


# ---------------------------------------------------------------
# 领域工具函数（返回可读文本，供 LLM 阅读）
# ---------------------------------------------------------------
def get_load_curve(region: str = "园区A") -> str:
    """获取某区域典型日 24 小时负荷曲线与峰谷特征。"""
    curve = load_curve(region)
    peak_h, valley_h = curve.index(max(curve)), curve.index(min(curve))
    gap = max(curve) - min(curve)
    return (
        f"区域：{region}（{REGIONS[region]['类型']}）\n"
        f"24 小时负荷(MW)：{curve}\n"
        f"峰值 {max(curve)} MW（{peak_h} 时），谷值 {min(curve)} MW（{valley_h} 时）\n"
        f"峰谷差 {gap:.1f} MW，峰谷差率 {gap / max(curve) * 100:.1f}%"
    )


def forecast_load(region: str = "园区A") -> str:
    """预测某区域明日 24 小时负荷（考虑气温上浮）。"""
    curve = load_curve(region)
    # 高温导致午间负荷上浮 5%，其余时段微调
    forecast = [round(v * (1.05 if 10 <= h <= 16 else 1.0), 1) for h, v in enumerate(curve)]
    peak_h = forecast.index(max(forecast))
    return (
        f"区域：{region} 明日负荷预测(MW)：{forecast}\n"
        f"受高温影响，10-16 时负荷上浮约 5%，预计峰值 {max(forecast)} MW 出现在 {peak_h} 时，"
        f"建议提前安排削峰资源。"
    )


def get_renewable_output(region: str = "园区A") -> str:
    """获取某区域光伏/风电 24 小时出力与可消纳电量。"""
    pv, wind = pv_curve(region), wind_curve(region)
    pv_energy = sum(pv)
    wind_energy = sum(wind)
    return (
        f"区域：{region}（光伏 {REGIONS[region]['光伏装机MWp']} MWp，风电 {REGIONS[region]['风电装机MW']} MW）\n"
        f"光伏 24h 出力(MW)：{pv}\n风电 24h 出力(MW)：{wind}\n"
        f"全天光伏发电量约 {pv_energy:.0f} MWh，风电发电量约 {wind_energy:.0f} MWh，"
        f"合计 {pv_energy + wind_energy:.0f} MWh"
    )


def get_storage_status(region: str = "园区A") -> str:
    """获取某区域储能系统参数与当前状态。"""
    s = STORAGE
    soc = s["当前SOC"]
    return (
        f"区域：{region} 园区储能系统\n"
        f"额定容量 {s['额定容量MWh']} MWh，额定功率 {s['额定功率MW']} MW，"
        f"当前 SOC {soc * 100:.0f}%（可用电量 {soc * s['额定容量MWh']:.0f} MWh）\n"
        f"充放电效率 {s['充放电效率'] * 100:.0f}%，最低 SOC {s['最低SOC'] * 100:.0f}%"
    )


def get_price_curve(region: str = "园区A") -> str:
    """获取某区域峰谷分时电价。"""
    return (
        f"区域：{region} 分时电价（元/kWh）\n"
        "谷段 23:00-07:00：0.32\n平段 07:00-08:00、22:00-23:00：0.68\n"
        "峰段 08:00-11:00、13:00-19:00、21:00-22:00：1.05\n"
        "尖峰段 11:00-13:00、19:00-21:00：1.30\n"
        "最大峰谷价差 0.98 元/kWh，具备储能套利空间。"
    )


def get_energy_consumption(region: str = "园区A") -> str:
    """获取某区域年度分项用电与节能提示。"""
    items = ENERGY[region]
    total = sum(v for _, v, _ in items)
    lines = [f"区域：{region} 年度总用电约 {total} 万 kWh，分项如下："]
    for name, kwh, note in items:
        tip = f"（{note}）" if note else ""
        lines.append(f"- {name}：{kwh} 万 kWh（{kwh / total * 100:.0f}%）{tip}")
    return "\n".join(lines)


def get_carbon_factors() -> str:
    """获取主要能源碳排放因子。"""
    lines = ["主要排放因子（kgCO2/kWh）："]
    for name, val in CARBON_FACTORS.items():
        lines.append(f"- {name}：{val}")
    lines.append("参考：全国电网平均排放因子约 0.5703 kgCO2/kWh。")
    return "\n".join(lines)


def optimize_dispatch(region: str = "园区A") -> str:
    """源网荷储协同调度：基于负荷/风光/电价计算储能充放电计划与收益。"""
    load, pv, wind, price = load_curve(region), pv_curve(region), wind_curve(region), list(PRICE)
    s = STORAGE
    cap, power, eff, min_soc = s["额定容量MWh"], s["额定功率MW"], s["充放电效率"], s["最低SOC"]

    net = [round(load[h] - pv[h] - wind[h], 1) for h in range(24)]  # 净负荷（从电网购电）
    plan = [0.0] * 24
    energy = s["当前SOC"] * cap
    used: set = set()

    # 电价最低时段充电，最高时段放电（规则贪心）
    for h in sorted(range(24), key=lambda x: price[x]):
        if energy >= cap:
            break
        charge = min(power, (cap - energy) / eff)
        plan[h] = round(charge, 2)
        energy += charge * eff
        used.add(h)
    for h in sorted(range(24), key=lambda x: -price[x]):
        if energy <= min_soc * cap or h in used:
            continue
        discharge = min(power, energy - min_soc * cap)
        plan[h] = round(-discharge, 2)
        energy -= discharge

    def grid_cost(curve):
        return sum(max(v, 0) * price[h] for h, v in enumerate(curve))

    orig_cost, opt_cost = grid_cost(net), grid_cost([net[h] + plan[h] for h in range(24)])
    orig_peak = max(max(net), 0)
    opt_peak = max(max(net[h] + plan[h] for h in range(24)), 0)

    schedule = "，".join(f"{h}时{'+' if plan[h] > 0 else ''}{plan[h]:.1f}MW" for h in range(24) if plan[h] != 0)
    return (
        f"区域：{region} 源网荷储协同调度结果\n"
        f"充放电计划(MW，正为充电/负为放电)：{schedule}\n"
        f"优化前购电成本 {orig_cost:.1f} 元/MW·h 等效，优化后 {opt_cost:.1f}，"
        f"节省 {orig_cost - opt_cost:.1f}（峰谷套利）\n"
        f"削峰：{orig_peak:.1f} MW → {opt_peak:.1f} MW，削峰率 {(orig_peak - opt_peak) / orig_peak * 100:.1f}%"
    )


# ---------------------------------------------------------------
# 概览数据（供前端可视化面板）
# ---------------------------------------------------------------
def get_overview(region: str = "园区A") -> Dict:
    return {
        "region": region,
        "type": REGIONS[region]["类型"],
        "load": load_curve(region),
        "pv": pv_curve(region),
        "wind": wind_curve(region),
        "price": list(PRICE),
        "storage": dict(STORAGE),
    }
