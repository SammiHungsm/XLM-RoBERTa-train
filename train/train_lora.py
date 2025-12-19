import json
import numpy as np
from datasets import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForTokenClassification, 
    TrainingArguments, 
    Trainer,
    DataCollatorForTokenClassification
)
from peft import get_peft_model, LoraConfig, TaskType
import evaluate

# 1. 載入數據
print("正在載入數據...")
with open("train_data_lora.json", "r", encoding="utf-8") as f:
    raw = json.load(f)
    data = raw["data"]
    label2id = raw["label2id"]
    # 確保 id2label 的 key 是整數
    id2label = {int(k): v for k, v in raw["id2label"].items()}

dataset = Dataset.from_list(data)
dataset = dataset.train_test_split(test_size=0.1)

# 2. 模型與分詞器
model_name = "Davlan/xlm-roberta-large-ner-hrl" 
print(f"正在載入模型: {model_name}")
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 3. Tokenization & Alignment
def tokenize_and_align_labels(examples):
    tokenized_inputs = tokenizer(
        examples["tokens"], 
        is_split_into_words=True, 
        truncation=True, 
        padding="max_length", 
        max_length=128
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

print("正在處理 Tokenization...")
# --- 修正開始 ---
tokenized_datasets = dataset.map(
    tokenize_and_align_labels, 
    batched=True,
    remove_columns=dataset["train"].column_names # 關鍵修正：移除原始文字欄位
)
# --- 修正結束 ---

# 4. 載入模型並配置 LoRA
model = AutoModelForTokenClassification.from_pretrained(
    model_name, 
    num_labels=len(label2id),
    id2label=id2label,
    label2id=label2id,
    ignore_mismatched_sizes=True
)

# LoRA 設定
peft_config = LoraConfig(
    task_type=TaskType.TOKEN_CLS, 
    inference_mode=False, 
    r=16,           
    lora_alpha=32,  
    lora_dropout=0.1,
    bias="none",
    target_modules=["query", "value"]
)

model = get_peft_model(model, peft_config)
print("--- LoRA 參數分佈 ---")
model.print_trainable_parameters()

# 5. 訓練參數
args = TrainingArguments(
    output_dir="./lora_xlm_roberta_ner",
    eval_strategy="epoch",
    learning_rate=2e-4,
    per_device_train_batch_size=8, # 如果顯示記憶體不足(OOM)，請改為 4
    gradient_accumulation_steps=1, # 如果 batch 改為 4，這裡建議改為 2
    num_train_epochs=5,
    weight_decay=0.01,
    save_strategy="epoch",
    logging_steps=100,
    save_total_limit=2,
    remove_unused_columns=False,
    
    # === 新增以下設定以啟用 GPU 加速 ===
    fp16=True,        # 開啟混合精度訓練 (速度快，省顯存)
    # bf16=True,      # RTX 40 系列其實支援 bf16，這比 fp16 更穩定，你可以試試將 fp16 改為 bf16
    dataloader_num_workers=0 # Windows 上有時多線程讀取會報錯，設為 0 最保險
)
data_collator = DataCollatorForTokenClassification(tokenizer)

# Metrics
print("載入評估指標...")
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

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["test"],
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
)

print("開始訓練...")
trainer.train()

# 儲存
print("正在儲存模型...")
model.save_pretrained("./final_lora_model")
tokenizer.save_pretrained("./final_lora_model")
print("✅ 訓練完成！模型已存至 ./final_lora_model")