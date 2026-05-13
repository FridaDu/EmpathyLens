"""
EmpathyLens MVP v0.3 - Tri-Provider, Flagship Tier
Author: Frida Du, Helena Cai

Models: All three providers' flagship-tier models, configured to match
real-world deployment of consumer emotional companionship products
(low-latency, non-thinking mode). Thinking mode is reserved for the
LLM-as-a-Judge evaluation stage in Week 8.

Models:
- OpenAI: gpt-5.4
- Anthropic: claude-opus-4-6
- DeepSeek: deepseek-v4-pro
"""

import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic

# 加载 .env 中所有的 API 密钥
load_dotenv()

# ---------- 三家 Client 初始化 ----------
openai_client = OpenAI()  # 自动读 OPENAI_API_KEY
anthropic_client = Anthropic()  # 自动读 ANTHROPIC_API_KEY
deepseek_client = OpenAI(  # DeepSeek 兼容 OpenAI 协议,只需换 base_url 和 key
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# ---------- 模型选择(三家 flagship-tier 对齐) ----------
MODELS = {
    "openai": "gpt-5.4",
    "anthropic": "claude-opus-4-6",
    "deepseek": "deepseek-v4-pro",
}

# ---------- 三种文化模式的 System Prompt(v0.1,后续会迭代) ----------
SYSTEM_PROMPTS = {
    "zh": (
        "你是一个理解中文情感表达习惯的陪伴助手。"
        "回应时避免过度直接的情感肯定,多用共同经验和适度的实用建议。"
    ),
    "de": (
        "Du bist ein einfühlsamer Begleiter, der die deutsche Direktheit respektiert. "
        "Vermeide überschwängliche Bestätigungen und biete bei Bedarf praktische Sichtweisen."
    ),
    "en": (
        "You are an empathetic companion. Respond with warmth, "
        "name the emotions explicitly, and validate the user's feelings clearly."
    ),
}

# ---------- 三段平行测试输入(同一情境的三语版本) ----------
TEST_INPUTS = {
    "zh": "最近工作压力很大,每天都很累,感觉自己快撑不住了。",
    "de": "Ich habe in letzter Zeit so viel Stress bei der Arbeit, ich bin völlig erschöpft.",
    "en": "I've been so stressed at work lately, I feel like I'm about to break down.",
}


def get_response(user_input: str, lang: str, provider: str) -> str:
    """对一段倾诉,用指定 provider 和文化模式生成响应。

    所有三家均显式关闭 thinking/reasoning 模式,
    以匹配主流情感陪伴产品的实际部署条件(低延迟、即时回应)。
    """
    system_prompt = SYSTEM_PROMPTS[lang]
    model = MODELS[provider]

    if provider == "openai":
        # GPT-5.4 通过 reasoning_effort 控制思考强度
        # "none" = 完全不思考,最接近商业产品的实时对话部署
        # 注:GPT-5 原版接受 "minimal",GPT-5.4 起改为 "none"
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            max_completion_tokens=400,
            reasoning_effort="none",
        )
        return response.choices[0].message.content

    elif provider == "anthropic":
        # Anthropic 默认关闭 thinking。不传 thinking 参数即关闭。
        response = anthropic_client.messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_input}],
            max_tokens=400,
        )
        return response.content[0].text

    elif provider == "deepseek":
        # DeepSeek V4 通过 extra_body 显式关闭 thinking
        response = deepseek_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            max_tokens=400,
            extra_body={"thinking": {"type": "disabled"}},
        )
        return response.choices[0].message.content

    else:
        raise ValueError(f"Unknown provider: {provider}")


def main():
    """跑通三家 × 三语,把所有结果存到 results/ 下。"""
    results = []
    providers = ["openai", "anthropic", "deepseek"]
    langs = ["zh", "de", "en"]

    for provider in providers:
        for lang in langs:
            print(f"\n=== {provider.upper()} | {lang.upper()} mode ===")
            user_input = TEST_INPUTS[lang]
            print(f"User: {user_input}")
            try:
                reply = get_response(user_input, lang, provider)
                print(f"AI:   {reply}")
                results.append({
                    "timestamp": datetime.now().isoformat(),
                    "provider": provider,
                    "model": MODELS[provider],
                    "thinking_mode": "disabled",
                    "lang": lang,
                    "user_input": user_input,
                    "ai_response": reply,
                    "status": "success",
                })
            except Exception as e:
                print(f"ERROR: {e}")
                results.append({
                    "timestamp": datetime.now().isoformat(),
                    "provider": provider,
                    "model": MODELS[provider],
                    "thinking_mode": "disabled",
                    "lang": lang,
                    "user_input": user_input,
                    "ai_response": None,
                    "status": "error",
                    "error_message": str(e),
                })

    project_root = Path(__file__).resolve().parent.parent.parent
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)
    out_path = results_dir / f"mvp_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Results saved to: {out_path}")
    print(f"✓ Total: {len(results)} runs ({sum(1 for r in results if r['status'] == 'success')} success)")


if __name__ == "__main__":
    main()