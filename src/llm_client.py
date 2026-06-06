"""EmpathyLens — unified multi-provider LLM client (Week 8 任务,提前做).
统一调用三家:Claude / GPT / DeepSeek。thinking 全部关闭(对齐 methodology_notes §2)。
冒烟测试: python -m src.llm_client"""
import os
from dotenv import load_dotenv

load_dotenv()  # 读取 .env 里的三家 API key

DEFAULT_MODEL = "claude-opus-4-6"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 600

# 锁定的三家旗舰模型 (methodology_notes §1)
MODELS = {
    "anthropic": "claude-opus-4-6",
    "openai":    "gpt-5.4",
    "deepseek":  "deepseek-v4-pro",
}


def call_model(prompt, system, model=DEFAULT_MODEL,
               temperature=DEFAULT_TEMPERATURE, max_tokens=DEFAULT_MAX_TOKENS):
    """Route to the right provider by model name; return response text (str).
    按 model 名路由到对应厂商,返回回复文本。thinking 一律关闭。"""
    if model.startswith("claude"):
        return _call_anthropic(prompt, system, model, temperature, max_tokens)
    if model.startswith("gpt"):
        return _call_openai(prompt, system, model, max_tokens)   # GPT 不传 temperature
    if model.startswith("deepseek"):
        return _call_deepseek(prompt, system, model, temperature, max_tokens)
    raise ValueError(f"未知 model: {model}(应以 claude / gpt / deepseek 开头)")


def _call_anthropic(prompt, system, model, temperature, max_tokens):
    # Anthropic Messages API. Thinking OFF by default (不传 thinking 参数即可).
    import anthropic
    client = anthropic.Anthropic()                       # 读 ANTHROPIC_API_KEY
    resp = client.messages.create(
        model=model, system=system,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature, max_tokens=max_tokens,
    )
    return resp.content[0].text


def _call_openai(prompt, system, model, max_tokens):
    # OpenAI Responses API:reasoning 模型推荐路径,避开 Chat Completions 的 none+max_completion_tokens bug.
    # thinking off = effort "none";输出上限用 max_output_tokens;GPT-5.x 不支持 temperature,故不传.
    from openai import OpenAI
    client = OpenAI()                                    # 读 OPENAI_API_KEY
    resp = client.responses.create(
        model=model,
        instructions=system,                            # Responses API 用 instructions 当系统提示
        input=prompt,
        reasoning={"effort": "none"},                   # thinking off
        max_output_tokens=max_tokens,
    )
    text = resp.output_text
    if not text:
        raise RuntimeError("GPT 返回空:多半是 max_tokens 太小被 reasoning 吃光,调大 max_tokens 再试。")
    return text


def _call_deepseek(prompt, system, model, temperature, max_tokens):
    # DeepSeek V4 = OpenAI 兼容接口,只换 base_url;thinking 默认开,这里显式关闭(关了 temperature 才生效).
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],
                    base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": prompt}],
        temperature=temperature, max_tokens=max_tokens,
        extra_body={"thinking": {"type": "disabled"}},  # 关闭思考
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    # 冒烟测试:每家发一句最简单的,验证 key + 调用都通.
    sys_prompt = "You are terse. Reply in at most 5 words."
    for name, m in MODELS.items():
        try:
            out = call_model("Say hello.", sys_prompt, model=m)
            print(f"✅ {name} ({m}): {out!r}")
        except Exception as e:
            print(f"❌ {name} ({m}): {type(e).__name__}: {e}")