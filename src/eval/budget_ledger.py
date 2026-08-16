"""EmpathyLens — 本地预算台账 (Week 9 风控新增)。
按日期累计记录每次 run_judge.py 执行的(估算)花费,供跑批前的硬顶检查使用。

⚠️ 已知局限：当前基于字符数/4 近似 token 数 × PRICING 做成本估算,不是 provider 返回的
真实 token 用量——因为现有 llm_client.call_model 目前只返回响应文本,不返回 usage 字段。
若能改造 llm_client 返回 usage(input_tokens/output_tokens),建议把 run_judge.py 里
调用 record() 的地方换成基于真实用量计算,误差会更小。这一点已在团队待办里，
在此之前，务必坚持"周六 checkpoint 三家后台余额截图存档"的人工核对，不要只信任本台账。

放置：src/eval/budget_ledger.py。冒烟：python -m src.eval.budget_ledger
"""
import json
from datetime import date
from pathlib import Path

LEDGER_PATH = Path("results/.budget_ledger.json")


def _load() -> dict:
    if LEDGER_PATH.exists():
        return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return {}


def _save(ledger: dict) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")


def today_spend(today: str | None = None) -> float:
    """今天(或指定日期 YYYY-MM-DD)已记录的估算花费(EUR)。"""
    today = today or date.today().isoformat()
    return _load().get(today, {}).get("total_eur", 0.0)


def record(amount_eur: float, note: str = "", today: str | None = None) -> float:
    """追加一笔估算花费到指定日期(默认今天)的台账，返回该日累计花费。
    amount_eur 允许为负数(如需要冲正一笔记错的估算)。"""
    today = today or date.today().isoformat()
    ledger = _load()
    day = ledger.setdefault(today, {"total_eur": 0.0, "entries": []})
    day["total_eur"] = round(day["total_eur"] + amount_eur, 4)
    day["entries"].append({"amount_eur": round(amount_eur, 4), "note": note})
    _save(ledger)
    return day["total_eur"]


def check_daily_cap(projected_additional_eur: float, daily_cap_eur: float,
                     today: str | None = None) -> tuple:
    """检查"今天已花 + 这次预计再花"是否会超过 daily_cap_eur。
    返回 (是否允许执行: bool, 今天已花金额: float)。调用方在允许执行后应自行调用
    record() 把这次的预估花费落账,不由本函数自动记账(避免"只查询不执行却被记账"的误差)。"""
    spent = today_spend(today)
    return (spent + projected_additional_eur) <= daily_cap_eur, spent


def summary(days: int = 7) -> str:
    """打印最近 N 天的台账摘要,供人工核对时快速浏览。"""
    ledger = _load()
    lines = [f"最近记录（共 {len(ledger)} 天有记录）："]
    for day in sorted(ledger.keys())[-days:]:
        lines.append(f"  {day}: €{ledger[day]['total_eur']:.2f}（{len(ledger[day]['entries'])} 笔）")
    return "\n".join(lines)


if __name__ == "__main__":
    # 冒烟：写一笔、读回、核对日累计、核对硬顶检查逻辑，不污染真实台账文件（用临时日期键）。
    test_day = "1970-01-01"
    before = today_spend(test_day)
    after = record(1.23, note="smoke-test", today=test_day)
    assert round(after - before, 2) == 1.23, "台账累加有误"

    ok, spent = check_daily_cap(0.01, daily_cap_eur=9999, today=test_day)
    assert ok
    ok2, _ = check_daily_cap(9999.0, daily_cap_eur=1.0, today=test_day)
    assert not ok2, "硬顶检查应拒绝明显超限的请求"

    print(f"✅ budget_ledger 自检通过（{test_day} 累计 €{after:.2f}）")
    print(summary())
