import json, re, time
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "triage-router"
INSTR = '判断用户输入的意图类别,只输出JSON:{"intent": "类别名"}'
TEST = r"E:\interview-assistant\finetune\test.jsonl"  # 路径不对就改这里


IM_END = "<|" + "im_end" + "|>"


def build_prompt(text):
    return f"<|im_start|>user\n{INSTR}\n{text}{IM_END}\n<|im_start|>assistant\n"


def extract_intent(text):
    m = re.search(r"\{[^{}]*\}", text)
    if not m:
        return None, False
    try:
        return json.loads(m.group(0)).get("intent"), True
    except json.JSONDecodeError:
        return None, False


def gold_intent(case):
    if case.get("intent") or case.get("label"):
        return case.get("intent") or case.get("label")
    out = case.get("output", "")
    try:
        return json.loads(out).get("intent")
    except (json.JSONDecodeError, TypeError):
        return None


def call_ollama(prompt):
    body = json.dumps({
        "model": MODEL,
        "raw": True,
        "stream": False,
        "prompt": prompt,
        "options": {"temperature": 0, "num_predict": 32},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["response"], (time.perf_counter() - t0) * 1000


def main():
    cases = [json.loads(l) for l in open(TEST, encoding="utf-8") if l.strip()]
    call_ollama(build_prompt("预热"))  # 预热：把模型加载时间移出统计
    n = correct = extractable = 0
    lat, errors = [], []
    for i, c in enumerate(cases, 1):
        text = c.get("text") or c.get("input")
        gold = gold_intent(c)
        out, dt = call_ollama(build_prompt(text))
        pred, ok = extract_intent(out)
        n += 1; extractable += ok; lat.append(dt)
        if pred == gold:
            correct += 1
        else:
            errors.append({"text": text, "gold": gold, "pred": pred})
        if i % 10 == 0:
            print(f"已完成 {i}/{len(cases)}", flush=True)
    lat.sort()
    print(f"\n样本数: {n}")
    print(f"JSON可提取率: {extractable/n:.0%}")
    print(f"准确率: {correct/n:.0%} ({correct}/{n})")
    print(f"延迟 p50: {lat[len(lat)//2]:.0f}ms  p95: {lat[int(len(lat)*0.95)]:.0f}ms")
    print("\n错例:")
    for e in errors:
        print(json.dumps(e, ensure_ascii=False))


if __name__ == "__main__":
    main()
