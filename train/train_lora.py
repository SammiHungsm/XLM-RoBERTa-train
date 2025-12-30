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

# ==========================================
# 1. 載入數據
# ==========================================
print("📂 正在載入數據...")
with open("train_data_lora.json", "r", encoding="utf-8") as f:
    raw = json.load(f)
    data = raw["data"]
    label2id = raw["label2id"]
    # 確保 id2label 的 key 是整數
    id2label = {int(k): v for k, v in raw["id2label"].items()}

dataset = Dataset.from_list(data)
# 切分 10% 作為驗證集 (Test/Validation Set)
dataset = dataset.train_test_split(test_size=0.1)

# ==========================================
# 2. 模型與分詞器
# ==========================================
model_name = "Davlan/xlm-roberta-large-ner-hrl" 
print(f"🤖 正在載入模型: {model_name}")
tokenizer = AutoTokenizer.from_pretrained(model_name)

# ==========================================
# 3. Tokenization & Alignment (改良版)
# ==========================================
def tokenize_and_align_labels(examples):
    tokenized_inputs = tokenizer(
        examples["tokens"], 
        is_split_into_words=True, 
        truncation=True, 
        padding="max_length", 
        max_length=256  # 🔥 改良點 1: 提升到 256，確保長地址唔會被截斷
    )

    labels = []
    for i, label in enumerate(examples["ner_tags"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)
        previous_word_idx = None
        label_ids = []
        for word_idx in word_ids:
            if word_idx is None:
                label_ids.append(-100) # 忽略特殊 token (如 [CLS], [SEP])
            elif word_idx != previous_word_idx:
                label_ids.append(label[word_idx]) # 只標記單詞的第一個 token
            else:
                label_ids.append(-100) # 同一個單詞的後續 token 設為 -100
            previous_word_idx = word_idx
        labels.append(label_ids)

    tokenized_inputs["labels"] = labels
    return tokenized_inputs

print("⚙️ 正在處理 Tokenization...")
tokenized_datasets = dataset.map(
    tokenize_and_align_labels, 
    batched=True,
    remove_columns=dataset["train"].column_names # 移除原始文字欄位，避免格式衝突
)

# ==========================================
# 4. 載入模型並配置 LoRA (改良版)
# ==========================================
model = AutoModelForTokenClassification.from_pretrained(
    model_name, 
    num_labels=len(label2id),
    id2label=id2label,
    label2id=label2id,
    ignore_mismatched_sizes=True # 允許最後一層分類器維度改變
)

# 🔥 改良點 2: 擴大 LoRA 訓練範圍
# 加入 key, output, intermediate 層，讓模型更快適應新知識 (如香港地址格式)
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
print("--- LoRA 參數分佈 ---")
model.print_trainable_parameters()

# ==========================================
# 5. 訓練參數 (改良版)
# ==========================================
args = TrainingArguments(
    output_dir="./lora_xlm_roberta_ner",
    eval_strategy="epoch",        # 每個 epoch 評估一次
    save_strategy="epoch",        # 每個 epoch 儲存一次 checkpoint
    learning_rate=2e-4,
    per_device_train_batch_size=8, # 顯存如果不夠 (OOM)，請改為 4
    gradient_accumulation_steps=1, # 如果 batch 改為 4，建議這裡改為 2
    num_train_epochs=5,
    weight_decay=0.01,
    logging_steps=50,
    save_total_limit=2,           # 只保留最新的 2 個模型，慳位
    remove_unused_columns=False,
    
    # 🔥 改良點 3: 自動載入最佳模型 (防止 Overfitting)
    load_best_model_at_end=True,  # 訓練結束時，自動 Load 返效果最好嗰個 Checkpoint
    metric_for_best_model="f1",   # 以 F1 Score 作為標準
    
    # GPU 加速設定
    fp16=True,                    # 混合精度 (速度快)
    dataloader_num_workers=0      # Windows 建議設為 0
)

data_collator = DataCollatorForTokenClassification(tokenizer)

# ==========================================
# 6. Metrics 評估函數
# ==========================================
print("📊 載入評估指標...")
metric = evaluate.load("seqeval")

def compute_metrics(p):
    predictions, labels = p
    predictions = np.argmax(predictions, axis=2)

    # 將預測結果還原為標籤名稱 (過濾掉 -100)
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
# 7. 開始訓練
# ==========================================
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["test"],
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
)

print("🚀 開始訓練...")
trainer.train()

# ==========================================
# 8. 儲存模型
# ==========================================
print("💾 正在儲存最佳模型...")
model.save_pretrained("./final_lora_model")
tokenizer.save_pretrained("./final_lora_model")
print("✅ 訓練完成！最佳模型已存至 ./final_lora_model")