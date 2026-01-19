import torch
import os
import sys
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from peft import PeftModel

# ===========================
# 🔥 1. 路徑設定
# ===========================
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

# 🔥 關鍵：必須匯入 LABEL2ID 等設定，告訴模型有幾個標籤
from src.config import LORA_MODEL_PATH, BASE_MODEL_NAME, LABEL2ID, ID2LABEL
from src.inference.processor import PIIProcessor

class PIIPipeline:
    def __init__(self, model_path=LORA_MODEL_PATH, device=None):
        """
        初始化 PII Pipeline：負責正確載入 Base Model + LoRA Adapter
        """
        if device is None:
            device = 0 if torch.cuda.is_available() else -1
            
        print(f"📂 正在從 {model_path} 載入模型...")
        
        try:
            # 1. 載入 Tokenizer
            # 優先嘗試從 LoRA 資料夾載入，失敗則從 Base Model 載入
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            except:
                print("⚠️ LoRA 資料夾找不到 Tokenizer，改用 Base Model 的 Tokenizer。")
                self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)

            # 🔥 2. 關鍵修正：先載入 Base Model，並強制指定標籤數量 (解決 Size Mismatch)
            print(f"⚙️ 正在初始化 Base Model ({BASE_MODEL_NAME}) 並設定 {len(LABEL2ID)} 個標籤...")
            base_model = AutoModelForTokenClassification.from_pretrained(
                BASE_MODEL_NAME,
                num_labels=len(LABEL2ID),  # 告訴模型：我們有 15 個標籤，不是 2 個
                id2label=ID2LABEL,
                label2id=LABEL2ID,
                ignore_mismatched_sizes=True
            )

            # 🔥 3. 載入 LoRA Adapter 並與 Base Model 合併
            print("🔗 正在疊加 LoRA 權重...")
            self.model = PeftModel.from_pretrained(base_model, model_path)
            self.model = self.model.merge_and_unload() # 合併權重，提升推論速度

        except Exception as e:
            print(f"❌ 模型載入失敗: {e}")
            print("💡 請確認 src/config.py 裡的 LABEL2ID 是否與訓練時一致。")
            raise e
        
        # 建立 HuggingFace Pipeline
        self.nlp_pipeline = pipeline(
            "token-classification", 
            model=self.model, 
            tokenizer=self.tokenizer, 
            aggregation_strategy="simple",
            device=device
        )
        print(f"✅ 模型載入成功！(Device: {'GPU' if device==0 else 'CPU'})")

    def predict(self, text):
        """
        輸入文字，回傳：原文、遮蓋後文字、實體列表
        """
        # 1. AI 推論
        raw_results = self.nlp_pipeline(text)
        
        # 2. 後處理 (Processor Class)
        processor = PIIProcessor(text, raw_results)
        final_entities = processor.process()
        masked_text = processor.get_masked_text()
        
        return {
            "original": text,
            "masked": masked_text,
            "entities": final_entities
        }

# ===========================
# 🧪 測試區塊
# ===========================
if __name__ == "__main__":
    pii_pipe = PIIPipeline()
    
    test_texts = [
        "Li Ka-shing resides at 12/F, Man Yee Building. ID: R123456(7)",
        "他今年 31 歲，住在觀塘道 99 號。",
        "At the age of 82.",
        "我的車牌係 AB1234，銀行戶口 123-456-789。"
    ]
    
    print("\n" + "="*50)
    print("🚀 PII 遮蓋測試開始")
    print("="*50)
    
    for text in test_texts:
        result = pii_pipe.predict(text)
        print(f"📄 原文: {result['original']}")
        print(f"🛡️ 遮蓋: {result['masked']}")
        print("-" * 30)