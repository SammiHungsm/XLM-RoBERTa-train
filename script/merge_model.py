import torch
from peft import PeftModel
from transformers import AutoModelForTokenClassification, AutoTokenizer

# ==========================================
# 修正設定
# ==========================================
# 1. 必須用回訓練時的那個 Large Model
base_model_name = "Davlan/xlm-roberta-large-ner-hrl" 
lora_model_path = "./final_lora_model"
output_dir = "./my_merged_presidio_model"

# 2. 根據錯誤訊息，你的模型只有 11 個 label (不是 13)
num_labels = 11 

print(f"1. 正在載入 Base Model: {base_model_name}...")
base_model = AutoModelForTokenClassification.from_pretrained(
    base_model_name,
    num_labels=num_labels,
    ignore_mismatched_sizes=True
)

print(f"2. 正在載入 LoRA Adapter: {lora_model_path}...")
model = PeftModel.from_pretrained(base_model, lora_model_path)

print("3. 正在合併模型 (Merge and Unload)...")
model = model.merge_and_unload()

print(f"4. 正在載入原始 Tokenizer...")
# 確保使用 fast tokenizer 以配合 Presidio
tokenizer = AutoTokenizer.from_pretrained(base_model_name, use_fast=True)

print(f"5. 正在儲存合併後嘅模型到: {output_dir}...")
model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)

print("✅ 完成！請重新執行 run_presidio_custom.py 測試。")