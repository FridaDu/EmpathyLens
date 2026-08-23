#!/usr/bin/env bash
#
# EmpathyLens — pre-flight check before any billable evaluation run.
#
# 为什么存在：Tier 3 全量评估按协议整个项目周期只跑一次，跑之前有一串必须确认的
# 前置条件（密钥在不在、有没有误提交、磁盘够不够、上次跑到哪了、今天已经花了多少）。
# 靠人肉逐条回想容易漏，漏一条的代价是又一次预算事故。这个脚本把清单固化下来。
#
# 用法：
#   ./scripts/preflight.sh              # 检查通用前置条件
#   ./scripts/preflight.sh --tier3      # 额外检查 Tier 3 专属条件（更严格）
#
# 退出码：0 = 全部通过；1 = 有阻断性问题；2 = 有警告但不阻断。

set -euo pipefail   # 出错即停、未定义变量报错、管道中任一环失败都算失败

# ── 输出着色（非终端环境自动降级为无色，避免日志里塞满转义字符）────────────
if [ -t 1 ]; then
    RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'
    BOLD=$'\033[1m'; RESET=$'\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BOLD=''; RESET=''
fi

FAILURES=0
WARNINGS=0

pass() { printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$1"; }
warn() { printf '  %s!%s %s\n' "$YELLOW" "$RESET" "$1"; WARNINGS=$((WARNINGS + 1)); }
fail() { printf '  %s✗%s %s\n' "$RED" "$RESET" "$1"; FAILURES=$((FAILURES + 1)); }

TIER3=false
[ "${1:-}" = "--tier3" ] && TIER3=true

# 切到项目根目录（脚本可能从任意位置被调用）
cd "$(dirname "$0")/.."

printf '\n%sEmpathyLens pre-flight check%s\n' "$BOLD" "$RESET"
printf '%s\n' "────────────────────────────────────────"

# ── 1. 运行环境 ───────────────────────────────────────────────────────────
printf '\n%sEnvironment%s\n' "$BOLD" "$RESET"

if [ -x .venv/bin/python ]; then
    pass "virtualenv present ($(.venv/bin/python --version 2>&1))"
    PY=.venv/bin/python
elif command -v python3 >/dev/null 2>&1; then
    warn "no .venv — falling back to system $(python3 --version 2>&1)"
    PY=python3
else
    fail "no usable Python interpreter found"
    PY=""
fi

if [ -n "$PY" ]; then
    for mod in openai anthropic pandas; do
        if "$PY" -c "import $mod" 2>/dev/null; then
            pass "python module: $mod"
        else
            fail "missing python module: $mod  (pip install -r requirements.txt)"
        fi
    done
fi

# ── 2. 密钥与安全 ─────────────────────────────────────────────────────────
printf '\n%sSecrets%s\n' "$BOLD" "$RESET"

if [ -f .env ]; then
    pass ".env present"
    # 只检查键是否存在且非空，绝不打印任何密钥内容
    for key in OPENAI_API_KEY ANTHROPIC_API_KEY DEEPSEEK_API_KEY; do
        if grep -qE "^${key}=.+" .env; then
            pass "$key is set"
        else
            warn "$key missing or empty in .env"
        fi
    done
else
    fail ".env not found — copy .env.example and fill in your keys"
fi

# 关键安全检查：.env 绝不能进版本库
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    fail ".env is TRACKED BY GIT — your API keys may be exposed. Remove it from the index."
else
    pass ".env is not tracked by git"
fi

if grep -qxF '.env' .gitignore 2>/dev/null; then
    pass ".env is listed in .gitignore"
else
    warn ".env not found in .gitignore"
fi

# ── 3. 数据与产物 ─────────────────────────────────────────────────────────
printf '\n%sData%s\n' "$BOLD" "$RESET"

for f in data/dataset_draft.json results/full_gen_v1.json; do
    if [ -f "$f" ]; then
        pass "$f ($(wc -c < "$f" | tr -d ' ') bytes)"
    else
        fail "missing: $f"
    fi
done

if [ -w results ] 2>/dev/null; then
    pass "results/ is writable"
else
    fail "results/ is not writable"
fi

# 磁盘余量：断点续跑会反复写盘，空间不足会在跑到一半时炸掉
AVAIL_MB=$(df -m . | awk 'NR==2 {print $4}')
if [ "$AVAIL_MB" -gt 500 ]; then
    pass "disk space: ${AVAIL_MB} MB available"
else
    warn "low disk space: ${AVAIL_MB} MB — a long run may fail midway"
fi

# ── 4. 预算台账 ───────────────────────────────────────────────────────────
printf '\n%sBudget%s\n' "$BOLD" "$RESET"

LEDGER=results/.budget_ledger.json
if [ -f "$LEDGER" ]; then
    TODAY=$(date +%Y-%m-%d)
    SPENT=$(grep -A2 "\"$TODAY\"" "$LEDGER" 2>/dev/null \
            | grep -o '"total_eur": *[0-9.]*' | head -1 | grep -o '[0-9.]*$' || true)
    if [ -n "${SPENT:-}" ]; then
        warn "already spent ~EUR ${SPENT} today (per local ledger)"
    else
        pass "no spend recorded today"
    fi
else
    pass "no ledger yet (first run)"
fi

# ── 5. Tier 3 专属检查 ────────────────────────────────────────────────────
if [ "$TIER3" = true ]; then
    printf '\n%sTier 3 specific%s\n' "$BOLD" "$RESET"

    # 单价是否还是未校准的占位符——这正是上次预算失控的根因之一
    if grep -q "TODO: 用真实账单校准" src/eval/run_judge.py 2>/dev/null; then
        fail "PRICING still uncalibrated (see TODO in src/eval/run_judge.py)"
    else
        pass "PRICING appears calibrated"
    fi

    # 已有评分文件意味着这是续跑，不是全新开始——提醒一下，避免误判进度
    if [ -f results/scores_full_gen_v1.json ]; then
        warn "results/scores_full_gen_v1.json exists — this will RESUME, not restart"
    else
        pass "no prior scores file (fresh run)"
    fi

    printf '\n  %sReminder:%s balances on all three provider dashboards must be\n' "$BOLD" "$RESET"
    printf '  checked by a human, with >=1.5x the estimated cost available.\n'
fi

# ── 汇总 ──────────────────────────────────────────────────────────────────
printf '\n%s\n' "────────────────────────────────────────"
if [ "$FAILURES" -gt 0 ]; then
    printf '%s✗ %d blocking issue(s), %d warning(s)%s\n\n' "$RED" "$FAILURES" "$WARNINGS" "$RESET"
    exit 1
elif [ "$WARNINGS" -gt 0 ]; then
    printf '%s! passed with %d warning(s)%s\n\n' "$YELLOW" "$WARNINGS" "$RESET"
    exit 2
else
    printf '%s✓ all checks passed%s\n\n' "$GREEN" "$RESET"
    exit 0
fi
