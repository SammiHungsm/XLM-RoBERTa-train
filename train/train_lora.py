import json
import numpy as np
import torch
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
try:
    with open("train_data_lora.json", "r", encoding="utf-8") as f:
        raw = json.load(f)
        data = raw["data"]
        label2id = raw["label2id"]
        # 確保 id2label 的 key 是整數
        id2label = {int(k): v for k, v in raw["id2label"].items()}
    print(f"✅ 成功載入 {len(data)} 條訓練數據")
except FileNotFoundError:
    print("❌ 錯誤：找不到 train_data_lora.json。請先執行 prepare_data.py！")
    exit()

dataset = Dataset.from_list(data)
# 切分 10% 作為驗證集 (Test/Validation Set)
dataset = dataset.train_test_split(test_size=0.1)

# ==========================================
# 1.5 數據完整性檢查 (Sanity Check)
# ==========================================
# 讓我們看看 smart_tokenize 的效果！
print("\n🔎 數據樣本檢查 (Example 0):")
print(f"Tokens: {dataset['train'][0]['tokens']}")
print(f"Tags:   {dataset['train'][0]['ner_tags']}")
print("(請確認上方的 Tokens 包含完整的英文單詞，例如 'Block' 而不是 'B','l'...) \n")

# ==========================================
# 2. 模型與分詞器
# ==========================================
model_name = "Davlan/xlm-roberta-large-ner-hrl" 
print(f"🤖 正在載入模型: {model_name}")
tokenizer = AutoTokenizer.from_pretrained(model_name)

# ==========================================
# 3. Tokenization & Alignment
# ==========================================
def tokenize_and_align_labels(examples):
    # 這裡的 is_split_into_words=True 非常重要
    # 因為我們的輸入已經是切分好的 List (smart_tokenize 的結果)
    tokenized_inputs = tokenizer(
        examples["tokens"], 
        is_split_into_words=True, 
        truncation=True, 
        padding="max_length", 
        max_length=256 
    )

    labels = []
    for i, label in enumerate(examples["ner_tags"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)
        previous_word_idx = None
        label_ids = []
        for word_idx in word_ids:
            if word_idx is None:
                # 特殊 token (<s>, </s>) 設為 -100 (不計算 Loss)
                label_ids.append(-100) 
            elif word_idx != previous_word_idx:
                # 這是單詞的第一個 Subtoken -> 賦予真實 Label
                # 因為我們現在用 smart_tokenize，這裡能確保 "Complex" 這個詞
                # 只有它的第一個 subtoken 獲得 B-TAG，這對模型學習很有幫助
                label_ids.append(label[word_idx]) 
            else:
                # 同一個單詞的後續 Subtokens -> 設為 -100
                # 例如 "Structure" 被切成 "Struc" + "ture"
                # "ture" 會被標記為 -100，避免模型過度關注後綴
                label_ids.append(-100) 
            previous_word_idx = word_idx
        labels.append(label_ids)

    tokenized_inputs["labels"] = labels
    return tokenized_inputs

print("⚙️ 正在處理 Tokenization 及 Label Alignment...")
tokenized_datasets = dataset.map(
    tokenize_and_align_labels, 
    batched=True,
    remove_columns=dataset["train"].column_names # 移除原始文字欄位
)

# ==========================================
# 4. 載入模型並配置 LoRA
# ==========================================
model = AutoModelForTokenClassification.from_pretrained(
    model_name, 
    num_labels=len(label2id),
    id2label=id2label,
    label2id=label2id,
    ignore_mismatched_sizes=True 
)

# 針對 NER 任務的 LoRA 配置
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
# 5. 訓練參數
# ==========================================
# 自動檢測是否可以使用 fp16 (CUDA)
use_fp16 = torch.cuda.is_available()
print(f"⚡ GPU 加速模式: {'FP16 (CUDA)' if use_fp16 else 'FP32 (CPU/MPS)'}")

args = TrainingArguments(
    output_dir="./lora_xlm_roberta_ner",
    eval_strategy="epoch",        
    save_strategy="epoch",        
    learning_rate=2e-4,
    per_device_train_batch_size=8, # 8G VRAM 建議 8; 4G VRAM 改 4
    gradient_accumulation_steps=1, 
    num_train_epochs=5,
    weight_decay=0.01,
    logging_steps=50,
    save_total_limit=2,           
    remove_unused_columns=False,
    load_best_model_at_end=True,  
    metric_for_best_model="f1",   
    
    # 設備相關設置
    fp16=use_fp16,                # 只有 NVIDIA GPU 才開 FP16
    dataloader_num_workers=0      # Windows 必須設為 0
)

# 加入 pad_to_multiple_of=8 可以讓 Tensor Core 運算更有效率
data_collator = DataCollatorForTokenClassification(
    tokenizer, 
    pad_to_multiple_of=8 if use_fp16 else None
)

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