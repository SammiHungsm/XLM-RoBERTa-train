import json
import os
import sys
from pathlib import Path

# ===========================
# 🔥 1. 路徑修復 (Path Fix)
# ===========================
# 確保 Python 能找到專案根目錄，解決 ModuleNotFoundError
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

# 🔥 2. 使用我們剛寫好的 Pipeline 類別
from src.inference.pipeline import PIIPipeline

def run_inference():
    print("🚀 [1/3] Initializing PII Pipeline...")
    
    # ✅ 自動處理模型載入、GPU 偵測
    pii_pipe = PIIPipeline()

    # 設定檔案路徑
    current_path = Path(__file__).parent
    input_file = current_path / "test_data.json"
    output_file = Path("inference_results.json")

    print(f"📂 [2/3] Reading input from: {input_file}")
    
    # 讀取數據邏輯 (保持不變)
    if input_file.exists():
        with open(input_file, "r", encoding="utf-8") as f:
            raw_input = json.load(f)
            test_data = raw_input.get("data", []) if isinstance(raw_input, dict) else raw_input
    else:
        print(f"⚠️ Warning: {input_file} not found. Using default test cases.")
        test_data = [
            "我的 ID 是 R123456(7)，請檢查。",
            "Bank Account = 274-542-182-882 (HSBC)",
            "西延高鐵昨日通車。",
            "Li Ka-shing resides at 12/F, Man Yee Building. Age: 82."
        ]

    print(f"🧪 [3/3] Processing {len(test_data)} samples...")

    output = []
    
    # 執行推論
    for idx, text in enumerate(test_data):
        # ✅ 使用 Pipeline 的 predict 方法 (一鍵完成 AI + Regex + 清洗)
        result = pii_pipe.predict(text)
        
        print(f"\n[#{idx}] 原文: {result['original']}")
        print(f"[#{idx}] 遮蓋: {result['masked']}")
        
        output.append({
            "id": idx,
            "original": result['original'],
            "masked": result['masked'],
            "entities": result['entities']
        })

    # 存檔
    if output_file.parent:
        output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Inference Completed! Results saved to: {output_file.absolute()}")

if __name__ == "__main__":
    run_inference()