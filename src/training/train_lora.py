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
    EarlyStoppingCallback,
    TrainerCallback
)
from peft import get_peft_model, LoraConfig, TaskType
import evaluate
from src.config import BASE_MODEL_NAME, LORA_MODEL_PATH, LABEL2ID, ID2LABEL

# 🔥 自定義日誌記錄器
class LogCallback(TrainerCallback):
    def __init__(self, log_path="training_history.json"):
        self.log_path = log_path
        self.history = []

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs:
            log_entry = {
                "step": state.global_step,
                "epoch": round(state.epoch, 2) if state.epoch else 0,
                **logs
            }
            self.history.append(log_entry)
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)

def train():
    # 1. 載入數據
    print("📂 載入訓練數據...")
    with open("train_data_lora.json", "r", encoding="utf-8") as f:
        raw = json.load(f)
        data = raw["data"]
    
    dataset = Dataset.from_list(data).train_test_split(test_size=0.1)

    # 2. 載入 Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)

    # 3. ⚙️ 處理數據 (Point 3：強化標籤對齊邏輯)
    def tokenize_and_align_labels(examples):
        tokenized_inputs = tokenizer(
            examples["tokens"], 
            is_split_into_words=True, 
            truncation=True, 
            max_length=384, 
            padding="max_length"
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
                    # 🔥 Point 3 核心：標籤傳播，確保模型學會長實體的連續性
                    label_ids.append(label[word_idx])
                
                previous_word_idx = word_idx
            labels.append(label_ids)

        tokenized_inputs["labels"] = labels
        return tokenized_inputs

    

    print("⚙️ 正在執行全標籤對齊處理 (Label Propagation)...")
    tokenized_datasets = dataset.map(
        tokenize_and_align_labels, 
        batched=True,
        remove_columns=dataset["train"].column_names
    )

    # 4. 載入模型並配置 LoRA
    model = AutoModelForTokenClassification.from_pretrained(
        BASE_MODEL_NAME, 
        num_labels=len(LABEL2ID),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True 
    )

    peft_config = LoraConfig(
        task_type=TaskType.TOKEN_CLS, 
        r=16, lora_alpha=32, lora_dropout=0.1,
        target_modules=["query", "key", "value", "output.dense", "intermediate.dense"]
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # 5. 設定評估指標
    metric = evaluate.load("seqeval")
    def compute_metrics(p):
        predictions, labels = p
        predictions = np.argmax(predictions, axis=2)
        true_predictions = [[ID2LABEL[p] for (p, l) in zip(pr, la) if l != -100] for pr, la in zip(predictions, labels)]
        true_labels = [[ID2LABEL[l] for (p, l) in zip(pr, la) if l != -100] for pr, la in zip(predictions, labels)]
        results = metric.compute(predictions=true_predictions, references=true_labels)
        return {
            "f1": results["overall_f1"],
            "precision": results["overall_precision"],
            "recall": results["overall_recall"]
        }

    # 6. 訓練參數 (Point 5 強化商用精調配置)
    args = TrainingArguments(
        output_dir="./lora_out",
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=100,
        
        # 🔥 Point 5 優化組合
        learning_rate=2e-5,           # 低學習率確保精細微調
        num_train_epochs=5,           # 配合低學習率增加 Epoch 確保收斂
        lr_scheduler_type="cosine",    # 使用餘弦退火，收尾學得更靚
        warmup_ratio=0.1,             # 加入熱身防止初期梯度不穩
        weight_decay=0.01,            # 增加權重衰減防止過擬合
        
        per_device_train_batch_size=4,
        gradient_accumulation_steps=2, # Effective Batch Size = 8
        logging_steps=10,
        logging_dir='./logs',
        fp16=torch.cuda.is_available(),
        gradient_checkpointing=True,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        report_to="tensorboard"
    )

    # 7. 啟動 Trainer
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
        tokenizer=tokenizer,
        data_collator=DataCollatorForTokenClassification(tokenizer),
        compute_metrics=compute_metrics,
        callbacks=[
            EarlyStoppingCallback(early_stopping_patience=3),
            LogCallback(log_path="training_history.json")
        ]
    )

    print("🚀 啟動強化版標籤對齊及商用精調訓練...")
    trainer.train()

    # 8. 儲存
    model.save_pretrained(LORA_MODEL_PATH)
    tokenizer.save_pretrained(LORA_MODEL_PATH)
    print(f"✅ 訓練完成！模型已存至 {LORA_MODEL_PATH}")

if __name__ == "__main__":
    train()