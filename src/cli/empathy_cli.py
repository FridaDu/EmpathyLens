"""
EmpathyLens — Week 4 MVP Command-Line Interface
EmpathyLens — Week 4 MVP 命令行程序

Location: src/cli/empathy_cli.py
位置:src/cli/empathy_cli.py

Usage / 用法 (run from project root / 在项目根目录运行):
    # Interactive single-input mode / 交互式单条输入模式
    python -m src.cli.empathy_cli
    python -m src.cli.empathy_cli --text "我妈又催我相亲了,烦死了。"
    python -m src.cli.empathy_cli --text "..." --modes zh de    # only some modes

    # Batch mode: run all 5 test inputs and save results
    # 批量模式:跑 5 条测试输入并保存结果
    python -m src.cli.empathy_cli --batch
    python -m src.cli.empathy_cli --batch --output results/

The program is intentionally thin: it ties together cultural_prompts.py and
the model API, and writes outputs in a Phase-2-ready format. No evaluation
logic here — that comes in Week 7+ when we build the evaluation pipeline.

程序刻意做薄:把 cultural_prompts.py 和模型 API 拼起来,以 Phase 2 可直接
读取的格式输出。这里不做评估逻辑 —— 评估在 Week 7+ 评估管道阶段。
"""

from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from src.prompts.cultural_prompts import CULTURAL_PROMPTS, PROMPT_VERSION


# ---------- Model configuration / 模型配置 -------------------------------
# Kept in one place so Week 5+ ablations can swap model/temperature easily.
# 集中在一处,Week 5+ 做消融可以一键切换 model/temperature。
DEFAULT_MODEL = "claude-opus-4-6"
DEFAULT_TEMPERATURE = 0.7   # framework leaves T choice to ablation (Week 7-9)
DEFAULT_MAX_TOKENS = 600    # longer than typical chat but allows full emotional response
# -----------------------------------------------------------------------

# TODO (Week 8): extract a multi-provider llm_client (openai/anthropic/deepseek)
#   for the evaluation pipeline. Week 4 CLI only needs one provider.
# TODO (Week 8): 抽一个多-provider 的 llm_client 供评估管道用。Week 4 只需单一 provider。
def call_model(system_prompt: str, user_text: str,
               model: str = DEFAULT_MODEL,
               temperature: float = DEFAULT_TEMPERATURE,
               max_tokens: int = DEFAULT_MAX_TOKENS) -> dict:
    """Call the Anthropic API once. Returns dict with response text + metadata.
    调用 Anthropic API 一次,返回响应文本 + 元数据 dict。

    The API client is imported lazily so the CLI is still useful for inspecting
    prompts even without ANTHROPIC_API_KEY set (e.g. on a teammate's machine).
    API 客户端延迟导入,这样即使没设 ANTHROPIC_API_KEY 也能用 CLI 检查 prompt
    (比如组员机器上看)。
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic SDK not installed. Run: pip install anthropic\n"
            "anthropic SDK 未安装,请运行:pip install anthropic"
        )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable not set.\n"
            "ANTHROPIC_API_KEY 环境变量未设置。\n"
            "  export ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = Anthropic()
    t_start = time.time()
    # Thinking mode is OFF (Anthropic defaults to no extended thinking unless
    # the `thinking` param is passed). Matches Week 2 decision (methodology_notes §2).
    # thinking 模式关闭(Anthropic 不传 thinking 参数即默认关闭),符合 Week 2 决策。
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_text}],
    )
    latency = time.time() - t_start

    # Concatenate text blocks (per API spec, content can be a list)
    # 拼接 text block(API 规范中 content 是 list)
    response_text = "".join(
        block.text for block in msg.content if block.type == "text"
    )

    return {
        "response_text": response_text,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking_mode": "disabled",
        "stop_reason": msg.stop_reason,
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
        "latency_sec": round(latency, 2),
    }


def run_one_input(user_text: str, modes: list,
                  model: str = DEFAULT_MODEL,
                  temperature: float = DEFAULT_TEMPERATURE) -> dict:
    """Run one user input through all requested cultural modes.
    把一条用户输入跑过所有请求的文化模式。

    Returns a dict that can be JSON-serialized; this is the canonical record
    format that the Phase 2 evaluation pipeline will consume.
    返回可 JSON 序列化的 dict;这是 Phase 2 评估管道将消费的标准记录格式。
    """
    record = {
        "user_text": user_text,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "temperature": temperature,
        "responses": {},   # mode -> response dict
    }

    for mode in modes:
        if mode not in CULTURAL_PROMPTS:
            print(f"[WARN] Unknown mode '{mode}', skipping. / 未知模式,跳过。",
                  file=sys.stderr)
            continue
        try:
            result = call_model(
                system_prompt=CULTURAL_PROMPTS[mode],
                user_text=user_text,
                model=model,
                temperature=temperature,
            )
            record["responses"][mode] = result
        except Exception as e:
            # Don't crash the whole batch if one mode fails — capture and continue.
            # 一个模式失败不要让整个批次崩溃,记录后继续。
            record["responses"][mode] = {"error": str(e)}
            print(f"[ERROR] mode={mode}: {e}", file=sys.stderr)

    return record


# ---------- Pretty-printing for terminal / 终端美化输出 -------------------

MODE_LABELS = {
    "zh": "🇨🇳 中文模式 (Chinese, calibrated)",
    "de": "🇩🇪 Deutsch (German, calibrated)",
    "en": "🇺🇸 English (uncalibrated baseline)",   # framework §3.3.2
}


def print_record(record: dict) -> None:
    """Print one record to stdout in a side-by-side-friendly format.
    把一条记录以便于横向对比的格式打印到 stdout。"""
    width = 78
    print()
    print("═" * width)
    print(f"📝 USER INPUT / 用户输入:")
    print(f"   {record['user_text']}")
    print(f"   [model={record['model']}  T={record['temperature']}  "
          f"prompt_v={record['prompt_version']}]")
    print("═" * width)

    for mode, resp in record["responses"].items():
        print()
        print("─" * width)
        print(f"  {MODE_LABELS.get(mode, mode)}")
        print("─" * width)
        if "error" in resp:
            print(f"  ⚠️  ERROR: {resp['error']}")
            continue
        print(resp["response_text"])
        print()
        print(f"   ⓘ  {resp['input_tokens']} in / {resp['output_tokens']} out "
              f"tokens  ·  {resp['latency_sec']}s  ·  stop={resp['stop_reason']}")
    print()
    print("═" * width)


# ---------- Main / 主入口 ------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="EmpathyLens Week 4 MVP — three cultural modes for emotional support.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--text", type=str, default=None,
        help="User input to respond to. If omitted, will prompt interactively. "
             "用户输入,留空则进入交互式输入。",
    )
    parser.add_argument(
        "--modes", nargs="+", default=["zh", "de", "en"],
        choices=["zh", "de", "en"],
        help="Which cultural modes to run. Default: all three. "
             "要跑哪些文化模式,默认三种都跑。",
    )
    parser.add_argument(
        "--batch", action="store_true",
        help="Run the 5 test inputs from src/tests/test_inputs.py and save results. "
             "跑 src/tests/test_inputs.py 中的 5 条测试并保存结果。",
    )
    parser.add_argument(
        "--output", type=str, default="results",
        help="Output directory for batch results (default: results/). "
             "批量结果输出目录,默认 results/。",
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"Model id (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--temperature", type=float, default=DEFAULT_TEMPERATURE,
        help=f"Sampling temperature (default: {DEFAULT_TEMPERATURE}).",
    )
    parser.add_argument(
        "--no-print", action="store_true",
        help="Suppress terminal output (batch mode still writes JSON). "
             "不打印终端输出,批量模式仍写 JSON。",
    )
    args = parser.parse_args()

    # ----- Batch mode -----
    if args.batch:
        from src.tests.test_inputs import TEST_INPUTS
        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
        # Naming aligned with existing convention: mvp_run_<YYYYMMDD_HHMMSS>.json
        # 命名对齐已有规范:mvp_run_<YYYYMMDD_HHMMSS>.json
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        all_records = []

        print(f"▶️  Running {len(TEST_INPUTS)} test inputs × {len(args.modes)} modes ...")
        print(f"   Output: {out_dir}/mvp_run_{run_id}.json")
        print()

        for i, item in enumerate(TEST_INPUTS, 1):
            print(f"[{i}/{len(TEST_INPUTS)}] {item['id']} ({item['lang']}, {item['kind']})")
            record = run_one_input(
                user_text=item["text"],
                modes=args.modes,
                model=args.model,
                temperature=args.temperature,
            )
            # Attach the test-item metadata so the JSON is self-contained.
            # 把测试项的元数据附加上,JSON 自包含。
            record["test_item"] = {
                "id": item["id"],
                "lang": item["lang"],
                "kind": item["kind"],
                "anchor": item["anchor"],
                "note": item["note"],
            }
            all_records.append(record)
            if not args.no_print:
                print_record(record)

        out_path = out_dir / f"mvp_run_{run_id}.json"
        out_path.write_text(
            json.dumps(all_records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n✅ Saved {len(all_records)} records to {out_path}")
        return

    # ----- Interactive / single-input mode -----
    user_text = args.text
    if user_text is None:
        print("Enter user input (single line) / 请输入一条用户倾诉:")
        try:
            user_text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        if not user_text:
            print("Empty input, exiting. / 输入为空,退出。")
            return

    record = run_one_input(
        user_text=user_text,
        modes=args.modes,
        model=args.model,
        temperature=args.temperature,
    )
    if not args.no_print:
        print_record(record)


if __name__ == "__main__":
    main()