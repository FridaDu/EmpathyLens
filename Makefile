# EmpathyLens — 常用命令入口
#
# 为什么用 Makefile：评估管道的命令又长又带危险参数（Tier 3 会真花钱），
# 靠记忆敲容易出错。这里把安全的操作做成短命令，把危险的操作加上确认。
#
# 用法：make            → 列出所有可用命令
#       make validate   → 跑全部零成本校验
#
# 约定：以 "零成本" 标注的目标不发起任何 API 请求，可随意重复运行。

PYTHON := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
GEN_SANITY := results/week7_sanity_check_v1.json
GEN_FULL := results/full_gen_v1.json

.DEFAULT_GOAL := help
.PHONY: help install validate dry-run bi figures tier1 tier2 tier3 ledger clean docker-build docker-validate

help:  ## 列出所有可用命令
	@echo ""
	@echo "EmpathyLens — 可用命令："
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""

install:  ## 创建虚拟环境并安装依赖
	$(PYTHON) -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "✅ 完成。激活环境： source .venv/bin/activate"

validate:  ## 【零成本】跑全部本地校验（CI 跑的也是这些）
	$(PYTHON) -m src.validate_dataset
	$(PYTHON) -m src.eval.rubrics
	$(PYTHON) -m src.eval.assemble_judge_input
	$(PYTHON) -m src.prompts.registry
	$(PYTHON) -m src.eval.budget_ledger
	@echo "✅ 全部校验通过"

dry-run:  ## 【零成本】完整跑一遍评估管道逻辑，但不发任何 API 请求
	$(PYTHON) -m src.eval.run_judge --tier 1 --gen $(GEN_SANITY) --dry-run --out /tmp/dryrun_scores.json

bi:  ## 【零成本】导出 Tableau / Power BI 可用的扁平 CSV
	$(PYTHON) -m src.viz.export_for_bi

figures:  ## 【零成本】生成出版级静态图表
	$(PYTHON) -m src.viz.week8_plots

ledger:  ## 【零成本】查看本地 API 消费台账
	$(PYTHON) -m src.eval.budget_ledger

tier1:  ## 【会计费·少量】Tier 1 评估：单裁判 × 10 条子集
	$(PYTHON) -m src.eval.run_judge --tier 1 --gen $(GEN_SANITY)

tier2:  ## 【会计费·中等】Tier 2 评估：三裁判 × 10 条子集
	$(PYTHON) -m src.eval.run_judge --tier 2 --gen $(GEN_SANITY)

tier3:  ## 【会计费·全量！】Tier 3 锁定评估：三裁判 × 60 条，需人工确认余额
	@echo ""
	@echo "⚠️  Tier 3 是全量锁定评估，按协议整个项目周期内只计划跑一次。"
	@echo "    开跑前必须：登录三家平台后台核对实时余额，预留 ≥1.5 倍预估费用。"
	@echo ""
	@read -p "已完成人工余额核对了吗？输入 yes 继续：" ans; \
	if [ "$$ans" != "yes" ]; then echo "已取消。"; exit 1; fi
	$(PYTHON) -m src.eval.run_judge --tier 3 --gen $(GEN_FULL) \
		--balance-checked --max-cost-eur 15 --daily-cap-eur 20

clean:  ## 清理临时产物（不动 results/ 里的实验数据）
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -not -path "./.venv/*" -delete
	rm -rf /tmp/dryrun_scores.json /tmp/ci_bi
	@echo "✅ 已清理"

docker-build:  ## 构建 Docker 镜像
	docker build -t empathylens:latest .

docker-validate:  ## 在容器里跑零成本校验（验证环境可复现）
	docker run --rm empathylens:latest
