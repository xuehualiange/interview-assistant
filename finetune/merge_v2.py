"""合并 v1 训练集 + v2 增量样本。"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
train_v1 = BASE / "train.jsonl"
v2_new = BASE / "triage_v2_new.jsonl"
out = BASE / "train_v2.jsonl"

records = []
for fn in (train_v1, v2_new):
    for line in fn.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))

out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
print(f"合并完成: {len(records)} 条 -> {out.name}")
