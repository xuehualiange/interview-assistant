import json
import re
import sys
import time
from pathlib import Path

# finetune/ 下运行时可 import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from openai import OpenAI

from app.agent import TRIAGE_SYSTEM_PROMPT
from app.config import get_settings

TEST = Path(__file__).resolve().parent / "test.jsonl"

# 在生产 prompt 基础上扩展第四类，与微调模型 / intent_taxonomy.md 对齐
_OUT_OF_SCOPE_BLOCK = """\
- out_of_scope：与求职/面试/简历完全无关的输入——闲聊、系统能力问询、让 AI 写无关内容等。
  判定标准：求职相关的陈述/碎碎念按话题归类（如「想找 AI 应用开发岗」「学到的东西都用不上，急」→ interview_prep）；
  只有与求职完全无关的内容才进 out_of_scope。
  典型信号词：天气、笑话、你是谁、写首诗、记得上次吗、帮我订餐、翻译 unrelated 内容（均与求职无关）。
  正例：今天北京天气怎么样？ / 你是谁，用的什么模型？ / 新的对话还记得上次讲了什么么？ /
  帮我写一首关于夏天的诗 / 我心情很差，陪我聊聊天（与求职无关的纯情感倾诉）。
  易混淆：求职相关的自言自语、半截陈述、带情绪的碎碎念 → 按话题归类，不归 out_of_scope。"""

TRIAGE_EVAL_SYSTEM_PROMPT = TRIAGE_SYSTEM_PROMPT.replace(
    "以下三个值之一", "以下四个值之一"
).replace(
    "- resume_opt：简历优化、简历修改、CV润色、简历诊断、ATS优化",
    "- resume_opt：简历优化、简历修改、CV润色、简历诊断、ATS优化\n"
    + _OUT_OF_SCOPE_BLOCK,
).replace(
    '{"intent": "...", "confidence": 0.0~1.0, "reason": "简短中文理由"}',
    '{"intent": "interview_prep|mock_interview|resume_opt|out_of_scope", '
    '"confidence": 0.0~1.0, "reason": "简短中文理由"}',
)

# 价格（元/百万 tokens），跑完按 DeepSeek 官网当时价格核对
PRICE_IN, PRICE_OUT = 2.0, 8.0

settings = get_settings()
client = OpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
)


def get_text(c):
    return c.get("text") or c.get("input")


def get_gold(c):
    if "output" in c:
        try:
            return json.loads(c["output"]).get("intent")
        except Exception:
            pass
    return c.get("intent") or c.get("label")


def extract_intent(text):
    m = re.search(r"\{[^{}]*\}", text)
    if not m:
        return None, False
    try:
        return json.loads(m.group(0)).get("intent"), True
    except json.JSONDecodeError:
        return None, False


def call_deepseek(text):
    """与生产 Triage DeepSeek 路径对齐：system prompt + user 输入，json_mode。"""
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": TRIAGE_EVAL_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0,
        max_tokens=128,
        response_format={"type": "json_object"},
    )
    dt = (time.perf_counter() - t0) * 1000
    return resp.choices[0].message.content, dt, resp.usage


def main():
    cases = [json.loads(l) for l in open(TEST, encoding="utf-8") if l.strip()]
    n = correct = extractable = 0
    tok_in = tok_out = 0
    lat, errors = [], []
    for i, c in enumerate(cases, 1):
        text, gold = get_text(c), get_gold(c)
        try:
            out, dt, usage = call_deepseek(text)
        except Exception as e:
            print(f"[{i}] API失败: {e}", flush=True)
            continue
        pred, ok = extract_intent(out)
        n += 1
        extractable += ok
        lat.append(dt)
        tok_in += usage.prompt_tokens
        tok_out += usage.completion_tokens
        if pred == gold:
            correct += 1
        else:
            errors.append({"text": text, "gold": gold, "pred": pred})
        if i % 10 == 0:
            print(f"已完成 {i}/{len(cases)}", flush=True)
        time.sleep(0.2)
    lat.sort()
    cost = tok_in / 1e6 * PRICE_IN + tok_out / 1e6 * PRICE_OUT
    print(f"\n样本数: {n}")
    print(f"JSON可提取率: {extractable/n:.0%}")
    print(f"准确率: {correct/n:.0%} ({correct}/{n})")
    print(f"延迟 p50: {lat[len(lat)//2]:.0f}ms  p95: {lat[int(len(lat)*0.95)]:.0f}ms")
    print(f"Token: 输入 {tok_in} / 输出 {tok_out}")
    print(f"本次成本: CNY {cost:.4f}（单价以官网为准）")
    print("\n错例:")
    for e in errors:
        print(json.dumps(e, ensure_ascii=False))


if __name__ == "__main__":
    main()
