import json
import os
import sys
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForTokenClassification
from peft import PeftModel

# ===========================
# 🔥 1. 路徑修復 (Path Fix)
# ===========================
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

# 導入配置與後處理器
from src.config import BASE_MODEL_NAME, LABEL2ID, ID2LABEL
from src.inference.processor import PIIProcessor

class PIIPipeline:
    """
    PII 推理流水線
    功能：
    1. 載入模型 (Base + LoRA)
    2. 執行滑動視窗推理 (支援長文本)
    3. 執行規則後處理 (PIIProcessor)
    """
    def __init__(self, lora_dir="./final_lora_model", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🚀 [Pipeline] Initializing on device: {self.device}")
        
        # 1. 載入 Tokenizer
        print(f"⏳ [Pipeline] Loading tokenizer: {BASE_MODEL_NAME}")
        self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)
        
        # 2. 載入 Base Model
        print(f"⏳ [Pipeline] Loading base model...")
        
        # 🔥🔥🔥 關鍵修復：加入 ignore_mismatched_sizes=True 🔥🔥🔥
        # 這會告訴模型："我知道標籤數量從 9 變成了 15，請捨棄舊的分類層並建立新的。"
        base_model = AutoModelForTokenClassification.from_pretrained(
            BASE_MODEL_NAME,
            num_labels=len(LABEL2ID),
            id2label=ID2LABEL,
            label2id=LABEL2ID,
            ignore_mismatched_sizes=True 
        )
        
        # 3. 載入 LoRA (如果存在)
        if os.path.exists(lora_dir):
            print(f"✅ [Pipeline] Found LoRA adapter at {lora_dir}, mounting...")
            self.model = PeftModel.from_pretrained(base_model, lora_dir)
        else:
            print(f"⚠️ [Pipeline] LoRA not found at {lora_dir}, using base model only.")
            self.model = base_model
            
        self.model.to(self.device)
        self.model.eval()
        print("✅ [Pipeline] Model loaded successfully!")

    def _predict_sliding_window(self, text, max_len=512, stride=400):
        """
        私有方法：執行滑動視窗預測，並計算真實信心分數 (Softmax)
        """
        all_raw_entities = []
        text_len = len(text)
        
        for start_idx in range(0, text_len, stride):
            end_idx = min(start_idx + max_len, text_len)
            chunk_text = text[start_idx:end_idx]
            
            if not chunk_text.strip(): continue

            inputs = self.tokenizer(
                chunk_text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=max_len,
                return_offsets_mapping=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(
                    input_ids=inputs["input_ids"], 
                    attention_mask=inputs["attention_mask"]
                )
                logits = outputs.logits
            
            probs = torch.nn.functional.softmax(logits, dim=2)[0].cpu().numpy()
            predictions = torch.argmax(logits, dim=2)[0].cpu().numpy()
            offset_mapping = inputs["offset_mapping"][0].cpu().numpy()
            
            chunk_entities = []
            current_ent = None
            
            for idx, pred_id in enumerate(predictions):
                label = ID2LABEL[pred_id]
                score = probs[idx][pred_id]
                start, end = offset_mapping[idx]
                
                if start == end: continue 
                
                # 🔥 FIX: 確保這些變量是 Python 原生 int，而不是 numpy.int64
                abs_start = int(start_idx + start)
                abs_end = int(start_idx + end)
                
                if abs_end > text_len: continue

                if label.startswith("B-"):
                    if current_ent: chunk_entities.append(current_ent)
                    current_ent = {
                        "entity_group": label[2:],
                        "start": abs_start,  # ✅ 已經轉為 int
                        "end": abs_end,      # ✅ 已經轉為 int
                        "word": text[abs_start:abs_end],
                        "score": float(score) # ✅ 確保轉為 float
                    }
                elif label.startswith("I-") and current_ent and label[2:] == current_ent["entity_group"]:
                    current_ent["end"] = abs_end
                    current_ent["word"] = text[current_ent["start"]:abs_end]
                    current_ent["score"] = (current_ent["score"] + float(score)) / 2
            
            if current_ent: chunk_entities.append(current_ent)
            all_raw_entities.extend(chunk_entities)
            
            if end_idx == text_len: break
            
        return all_raw_entities
    
    def predict(self, text):
        """
        對外接口：輸入文字，輸出遮蓋結果與實體列表
        """
        # 1. 獲取原始預測 (含滑動視窗)
        raw_entities = self._predict_sliding_window(text)
        
        # 2. 交給 Processor 進行後處理 (切割、過濾、規則修正)
        # 這一步會處理 "長和主席" -> "長和", "C9309次" -> 過濾 等邏輯
        processor = PIIProcessor(text, raw_entities)
        final_entities = processor.process()
        
        # 3. 獲取遮蓋後的文本
        masked_text = processor.get_masked_text()
        
        return {
            "original": text,
            "masked": masked_text,
            "entities": final_entities
        }

# ===========================
# 🔥 Main Execution Logic
# ===========================
def run_inference():
    print("\n" + "="*50)
    print("🚀 [1/3] Initializing PII Pipeline...")
    print("="*50)
    
    pii_pipe = PIIPipeline()

    # 設定檔案路徑
    current_path = Path(__file__).parent
    input_file = current_path / "test_data.json"
    output_file = Path("inference_results.json")

    # 準備測試數據
    test_data = []
    
    # 嘗試從檔案讀取
    if input_file.exists():
        print(f"📂 [2/3] Reading input from: {input_file}")
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                raw_input = json.load(f)
                test_data = raw_input.get("data", []) if isinstance(raw_input, dict) else raw_input
        except Exception as e:
            print(f"❌ Error reading file: {e}")
    
    # 如果沒有檔案或檔案為空，使用預設測試案例
    if not test_data:
        print(f"⚠️ Warning: No input file found or empty. Using default test cases.")
        test_data = [
            "李嘉誠好有錢，仲要住係香港中環皇后大道中 33 號萬宜大廈 12 樓，年齡 82 歲。",
            "聯絡電話為 +852 9123 4567。曾任職於長和主席。",
            "西延高鐵昨日通車，首班列車C9309次從延安出發。",
            "My ID is R123456(7), please check.",
            "Bank Account: 123-456-789 (HSBC)"
        ]

    print(f"\n🧪 [3/3] Processing {len(test_data)} samples...")

    output = []
    
    for idx, text in enumerate(test_data):
        if not isinstance(text, str): continue # 跳過非字串數據
        
        # ✅ 執行推論
        result = pii_pipe.predict(text)
        
        print(f"\n[Case #{idx+1}]")
        print(f"原文: {result['original'][:60]}..." if len(result['original']) > 60 else f"原文: {result['original']}")
        print(f"遮蓋: {result['masked'][:60]}..." if len(result['masked']) > 60 else f"遮蓋: {result['masked']}")
        
        output.append({
            "id": idx,
            "original": result['original'],
            "masked": result['masked'],
            "entities": result['entities']
        })

    # 存檔
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Inference Completed! Results saved to: {output_file.absolute()}")

if __name__ == "__main__":
    run_inference()