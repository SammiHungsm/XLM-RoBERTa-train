# src/utils/export_bank_review.py
import json
import os
import sys

# 確保可以導入專案模組
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.bank_loader import load_bank_data

def export_review_data():
    print("🔍 開始檢核銀行數據提取邏輯...")
    
    # 1. 使用與訓練完全相同的邏輯讀取數據
    # 這會讀取 data/raw/banks 下的所有檔案 (.xls, .csv, .xlsx)
    orgs, addrs = load_bank_data()
    
    # 2. 準備輸出格式
    review_data = {
        "summary": {
            "total_organizations": len(orgs),
            "total_addresses": len(addrs),
            "source_directory": "./data/raw/banks"
        },
        "extracted_organizations": orgs, # 這裡列出所有抓到的銀行名
        "extracted_addresses": addrs     # 這裡列出所有抓到的地址
    }
    
    # 3. 寫入 JSON 檔案
    output_file = "review_bank_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(review_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ 檢核報告已生成！")
    print(f"📄 請打開專案根目錄下的 '{output_file}' 進行查看。")
    print(f"📊 摘要: 抓到了 {len(orgs)} 個機構名, {len(addrs)} 個地址。")

if __name__ == "__main__":
    export_review_data()