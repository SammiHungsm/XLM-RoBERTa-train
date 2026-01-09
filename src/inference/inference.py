import os
import json
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from peft import PeftModel

# 匯入專案配置與工具
from src.config import BASE_MODEL_NAME, LORA_MODEL_PATH, ID2LABEL, LABEL2ID
from src.inference.utils import clean_and_process_entities, mask_text

def run_inference():
    print("🚀 [1/3] Loading Model and LoRA Adapter...")
    
    # 自動偵測設備
    device = 0 if torch.cuda.is_available() else -1
    
    # 載入分詞器
    tokenizer = AutoTokenizer.from_pretrained(LORA_MODEL_PATH)
    
    # 載入基礎模型並更換 Head (針對 15 類標籤)
    base = AutoModelForTokenClassification.from_pretrained(
        BASE_MODEL_NAME, 
        num_labels=len(LABEL2ID), 
        id2label=ID2LABEL, 
        label2id=LABEL2ID, 
        ignore_mismatched_sizes=True
    )
    
    # 掛載微調後的 LoRA 權重
    model = PeftModel.from_pretrained(base, LORA_MODEL_PATH).eval()
    
    # 封裝 Pipeline
    nlp = pipeline(
        "token-classification", 
        model=model, 
        tokenizer=tokenizer, 
        aggregation_strategy="simple", 
        device=device
    )

    # 定位測試數據路徑
    # 這裡使用 Path(__file__) 確保相對於當前腳本定位檔案
    current_dir = Path(__file__).parent
    input_file = current_dir / "test_data.json"
    output_file = Path("inference_results.json")

    print(f"📂 [2/3] Reading input from: {input_file}")
    
    if input_file.exists():
        with open(input_file, "r", encoding="utf-8") as f:
            test_data = json.load(f)
            if isinstance(test_data, dict):
                test_data = test_data.get("data", [])
    else:
        print(f"⚠️ Warning: {input_file} not found. Using default test cases.")
        test_data = ["李嘉誠住在香港中環，電話是 98765432。", "我的 ID 是 A123456(7)。"]

    print(f"🧪 [3/3] Processing {len(test_data)} samples...")

    output = []
    
    # 關閉梯度計算，節省內存並加速推論
    with torch.no_grad():
        for idx, text in enumerate(test_data):
            # 1. AI 模型預測
            raw_predictions = nlp(text)
            
            # 2. 後處理：清理、去重疊、Regex 補漏、編號
            # 這裡的 clean_and_process_entities 已處理 float32 轉換問題
            ents = clean_and_process_entities(raw_predictions, text)
            
            # 3. 生成掩碼文本
            masked = mask_text(text, ents)
            print(f"\n[#{idx}] 原文: {text}")
            print(f"[#{idx}] 遮蓋: {masked}")
            output.append({
                "id": idx,
                "original": text,
                "masked": masked,
                "entities": ents
            })
            
            # 每 100 條印一次進度
            if (idx + 1) % 100 == 0:
                print(f"⏳ Progress: {idx + 1}/{len(test_data)}")

    # 4. 儲存結果
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Inference Completed! Results saved to: {output_file.absolute()}")

if __name__ == "__main__":
    run_inference()