import json
import numpy as np
import torch
import os
from datasets import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForTokenClassification, 
    TrainingArguments, 
    Trainer,
    DataCollatorForTokenClassification,
    EarlyStoppingCallback
)
from peft import get_peft_model, LoraConfig, TaskType
import evaluate

# ==========================================
# 1. 載入數據
# ==========================================
print("📂 正在載入數據...")
try:
    with open("train_data_lora.json", "r", encoding="utf-8") as f:
        raw = json.load(f)
        data = raw["data"]
        label2id = raw["label2id"]
        id2label = {int(k): v for k, v in raw["id2label"].items()}
    print(f"✅ 成功載入 {len(data)} 條訓練數據")
except FileNotFoundError:
    print("❌ 錯誤：找不到 train_data_lora.json。請先執行 prepare_data.py！")
    exit()

dataset = Dataset.from_list(data)
# 切分 10% 作為驗證集
dataset = dataset.train_test_split(test_size=0.1)

# ==========================================
# 2. 模型與分詞器 (XLM-R Large)
# ==========================================
model_name = "Davlan/xlm-roberta-large-ner-hrl" 
print(f"🤖 正在載入模型及分詞器: {model_name}")
tokenizer = AutoTokenizer.from_pretrained(model_name)

# ==========================================
# 3. Tokenization & Alignment (優化 Max Length)
# ==========================================
def tokenize_and_align_labels(examples):
    # 增加至 384 以防新聞長句被截斷
    tokenized_inputs = tokenizer(
        examples["tokens"], 
        is_split_into_words=True, 
        truncation=True, 
        padding="max_length", 
        max_length=384 
    )

    labels = []
    for i, label in enumerate(examples["ner_tags"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)
        previous_word_idx = None
        label_ids = []
        for word_idx in word_ids:
            if word_idx is None:
                label_ids.append(-100) 
            elif word_idx != previous_word_idx:
                label_ids.append(label[word_idx]) 
            else:
                label_ids.append(-100) 
            previous_word_idx = word_idx
        labels.append(label_ids)

    tokenized_inputs["labels"] = labels
    return tokenized_inputs

print("⚙️ 正在處理 Tokenization 及 Label Alignment (Max Length: 384)...")
tokenized_datasets = dataset.map(
    tokenize_and_align_labels, 
    batched=True,
    remove_columns=dataset["train"].column_names
)

# ==========================================
# 4. 載入模型並配置進階 LoRA
# ==========================================
model = AutoModelForTokenClassification.from_pretrained(
    model_name, 
    num_labels=len(label2id),
    id2label=id2label,
    label2id=label2id,
    ignore_mismatched_sizes=True 
)

# 針對 Large 模型優化 target_modules，覆蓋所有 Dense 層以提升效果
peft_config = LoraConfig(
    task_type=TaskType.TOKEN_CLS, 
    inference_mode=False, 
    r=16,           
    lora_alpha=32,  
    lora_dropout=0.1,
    bias="none",
    target_modules=["query", "key", "value", "output.dense", "intermediate.dense"]
)

model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# ==========================================
# 5. 訓練參數 (VRAM 優化組合)
# ==========================================
use_fp16 = torch.cuda.is_available()
print(f"⚡ GPU 加速模式: {'FP16 (CUDA)' if use_fp16 else 'FP32'}")

args = TrainingArguments(
    output_dir="./lora_xlm_roberta_ner",
    eval_strategy="steps",        # 改為按步數評估，配合 Early Stopping 更靈活
    eval_steps=100,
    save_strategy="steps",
    save_steps=100,
    learning_rate=2e-4,
    per_device_train_batch_size=4,   # 降低 Batch Size 以防 OOM
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=2,  # 累積梯度，維持 Effective Batch Size = 8
    num_train_epochs=5,
    weight_decay=0.01,
    logging_steps=20,
    save_total_limit=2,           
    load_best_model_at_end=True,  
    metric_for_best_model="f1",
    fp16=use_fp16,
    # 🔥 VRAM 核心優化：開啟梯度檢查點
    gradient_checkpointing=True,
    # Windows 系統建議
    dataloader_num_workers=0,
    report_to="none" 
)

# ==========================================
# 6. Metrics 評估與 Collator
# ==========================================
data_collator = DataCollatorForTokenClassification(
    tokenizer, 
    pad_to_multiple_of=8 if use_fp16 else None
)

metric = evaluate.load("seqeval")

def compute_metrics(p):
    predictions, labels = p
    predictions = np.argmax(predictions, axis=2)

    true_predictions = [
        [id2label[p] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    true_labels = [
        [id2label[l] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]

    results = metric.compute(predictions=true_predictions, references=true_labels)
    return {
        "precision": results["overall_precision"],
        "recall": results["overall_recall"],
        "f1": results["overall_f1"],
        "accuracy": results["overall_accuracy"],
    }

# ==========================================
# 7. 開始訓練 (加入 Early Stopping)
# ==========================================
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["test"],
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=3)] # 3次評估冇進步就停
)

# 🔎 訓練前最後檢查
sample = dataset['train'][0]
if len(sample['tokens']) != len(sample['ner_tags']):
    print("❌ 致命錯誤：Tokens 與 Tags 長度不一！")
    exit()

print("🚀 啟動微調訓練...")
trainer.train()

# ==========================================
# 8. 儲存
# ==========================================
final_output = "./final_lora_model"
model.save_pretrained(final_output)
tokenizer.save_pretrained(final_output)
print(f"✅ 訓練完成！模型已存至 {final_output}")