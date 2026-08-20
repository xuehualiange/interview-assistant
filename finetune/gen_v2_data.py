import json, os, re, time
from openai import OpenAI

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

INSTRUCTION = '判断用户输入的意图类别,只输出JSON:{"intent": "类别名"}'
BATCH = 20

BUCKETS = {
    "boundary_interview_prep": {
        "intent": "interview_prep",
        "target": 80,
        "desc": "句子提到了'简历',但用户真正想要的动作是准备面试、吃透简历应对面试、知道面试会问什么——动作落点在面试表现上。例:'我有了这个简历该怎么准备面试'(这类最容易被误判成resume_opt)",
    },
    "boundary_resume_opt": {
        "intent": "resume_opt",
        "target": 80,
        "desc": "句子提到了'面试',但用户真正想要的动作是修改、润色、优化简历文本本身——动作落点在简历上。例:'把简历里模拟面试这个项目再润色一下'(这类最容易被误判成interview_prep或mock_interview)",
    },
    "fragment_mock": {
        "intent": "mock_interview",
        "target": 80,
        "desc": "模拟面试进行中的破碎输入:编号答题片段(如'1.不清楚,返回格式不对会422…3.sse是单向连接…')、对某道题的零散回答、'再来一题/下一道/这题跳过/看看我掌握到什么程度'这类中途指令。特点:短、碎、无上下文,但明显是在答题或面试练习中",
    },
    "fragment_prep": {
        "intent": "interview_prep",
        "target": 80,
        "desc": "求职准备相关的破碎陈述:无上下文的半截话、自言自语式的职业陈述。例:'我想找ai应用开发工程师'、'我的实习都是学校里的生产实习,学的不好'。特点:不像完整请求,但话题明确是求职/面试准备",
    },
}

GEN_PROMPT = """你是数据构造助手,为"求职助手AI的意图分类器"生成训练样本。
四个意图类别:
- interview_prep: 准备面试(了解面试问题、吃透简历项目、面试话术、求职方向),动作落点在面试表现
- mock_interview: 进行模拟面试(出题、答题、点评回答)
- resume_opt: 修改/润色/优化简历文本本身,动作落点在简历文本
- out_of_scope: 与求职面试无关

现在只生成这一类:{name}
要求:{desc}

硬性规则:
1. 只生成"用户输入"这句话本身,不要标签、不要编号、不要解释
2. 每条 5~60 字,口语化,像真人随手打的
3. 句式、人称、详略尽量多样,不要模板化开头
4. 一次生成 {batch} 条,JSON 返回: {{"items": ["...", "..."]}}"""

def norm(s):
    return re.sub(r"[\s，。！？,.!?、…~～\-—_\"'“”‘’:：;；()（）\[\]{}]", "", s).lower()

seen = set()
for fn in ["train.jsonl", "test.jsonl"]:
    with open(fn, encoding="utf-8") as f:
        for line in f:
            seen.add(norm(json.loads(line)["input"]))

new_records, review_lines = [], []
for name, cfg in BUCKETS.items():
    got, tries = [], 0
    while len(got) < cfg["target"] and tries < 15:
        tries += 1
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": GEN_PROMPT.format(name=name, desc=cfg["desc"], batch=BATCH)}],
                temperature=1.0,
                response_format={"type": "json_object"},
            )
            items = json.loads(resp.choices[0].message.content)["items"]
        except Exception as e:
            print(f"{name} 第{tries}批失败: {e}")
            time.sleep(3)
            continue
        for it in items:
            it = str(it).strip()
            if not (3 <= len(it) <= 100):
                continue
            key = norm(it)
            if key in seen:
                continue
            seen.add(key)
            got.append(it)
        print(f"{name}: {len(got)}/{cfg['target']}")
        time.sleep(1)
    for it in got[: cfg["target"]]:
        new_records.append({
            "instruction": INSTRUCTION,
            "input": it,
            "output": json.dumps({"intent": cfg["intent"]}, ensure_ascii=False),
        })
    review_lines.append(f"\n===== {name} (标签: {cfg['intent']}) 共{len(got)}条 =====")
    review_lines += got

with open("triage_v2_new.jsonl", "w", encoding="utf-8") as f:
    for r in new_records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
with open("v2_review.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(review_lines))
print(f"完成: 新增 {len(new_records)} 条 -> triage_v2_new.jsonl, 核对清单 -> v2_review.txt")