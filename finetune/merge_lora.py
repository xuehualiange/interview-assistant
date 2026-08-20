import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE = r"E:\models\Qwen3-1.7B-Base"
ADAPTER = r"E:\interview-assistant\finetune\triage_lora_v2"
OUT = r"E:\models\triage-router-v2"

print("加载 base 模型...")
model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16)

print("加载 LoRA 并合并进 base...")
model = PeftModel.from_pretrained(model, ADAPTER)
model = model.merge_and_unload()

print("保存合并后的完整模型...")
model.save_pretrained(OUT)

# tokenizer 用 adapter 里那份,带训练时的对话模板和 eos 配置
tok = AutoTokenizer.from_pretrained(ADAPTER)
tok.save_pretrained(OUT)

print("完成 ->", OUT)