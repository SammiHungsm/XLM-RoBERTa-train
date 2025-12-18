import json
from datasets import Dataset
from transformers import (
    XLMRobertaTokenizerFast,
    XLMRobertaForTokenClassification,
    DataCollatorForTokenClassification,
    TrainingArguments,
    Trainer
)

# 1. 載入數據
print("載入數據集...")
with open("pii_dataset_final.json", "r") as f:
    data = json.load(f)

dataset = Dataset.from_list(data)
split_dataset = dataset.train_test_split(test_size=0.1) # 90% 訓練, 10% 測試

# 2. 準備模型與分詞器
model_name = "xlm-roberta-base"
tokenizer = XLMRobertaTokenizerFast.from_pretrained(model_name)

# 標籤定義 (必須與 generate_data.py 一致)
id2label = {
    0: "O", 1: "B-NAME", 2: "I-NAME", 
    3: "B-HKID", 4: "I-HKID", 
    5: "B-ADDRESS", 6: "I-ADDRESS"
}
label2id = {v: k for k, v in id2label.items()}

model = XLMRobertaForTokenClassification.from_pretrained(
    model_name,
    num_labels=len(id2label),
    id2label=id2label,
    label2id=label2id
)

# 3. 訓練參數設定
args = TrainingArguments(
    output_dir="./pii_model_result",
    evaluation_strategy="epoch",      # 每個 Epoch 結束測驗一次
    save_strategy="epoch",            # 每個 Epoch 存檔一次
    learning_rate=2e-5,               # 微調標準學習率
    per_device_train_batch_size=16,   # 如果顯卡記憶體不足，改小這裡 (例如 8)
    num_train_epochs=3,               # 訓練 3 輪
    weight_decay=0.01,
    logging_steps=100
)

# 4. 開始訓練
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=split_dataset["train"],
    eval_dataset=split_dataset["test"],
    tokenizer=tokenizer,
    data_collator=DataCollatorForTokenClassification(tokenizer)
)

print("開始訓練模型...")
trainer.train()

# 5. 儲存最終模型
print("儲存模型中...")
trainer.save_model("./my_pii_model")
tokenizer.save_pretrained("./my_pii_model")
print("搞定！模型已儲存在 ./my_pii_model 資料夾")