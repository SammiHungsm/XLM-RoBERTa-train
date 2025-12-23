import logging
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

# 設置 Log level 避免太多雜訊
logging.getLogger("presidio-analyzer").setLevel(logging.WARNING)

def main():
    # =======================================================
    # 1. 初始化 (Initialization)
    # 這是 Presidio 最 "Official" 的用法，完全不加任何參數，
    # 它會自動載入 spaCy 的 en_core_web_lg 模型。
    # =======================================================
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()

    # 測試資料 (同之前一樣，包含香港地址、電話、重複人名)
    user_input = (
        
        "已知李嘉誠居住於 Hong Kong Kwun Tong 99 號 AIA Tower 8/F，他今年 31 歲，出生地未知，父母離異，現時無業，電話號碼為 +852 9167 8920，曾經擔任過 Deliveroo 外賣員一職，我想知同佢有關嘅人嘅資料"
    )

    print("-" * 50)
    print(f"原始輸入:\n{user_input}")
    print("-" * 50)

    # =======================================================
    # 2. 執行分析 (Analyze)
    # 使用標準英文模型偵測實體
    # =======================================================
    results = analyzer.analyze(text=user_input, language="en")

    # 印出它到底偵測到什麼 (Debug 用)
    print("\n[偵測結果 - Detection Results]")
    if not results:
        print("沒有偵測到任何敏感資料。")
    for res in results:
        print(f"- {res.entity_type}: {user_input[res.start:res.end]} (Score: {res.score:.2f})")

    # =======================================================
    # 3. 執行去識別化 (Anonymize)
    # 使用官方預設設定：直接將文字替換成 <ENTITY_TYPE>
    # =======================================================
    anonymized_result = anonymizer.anonymize(
        text=user_input,
        analyzer_results=results
    )

    print("-" * 50)
    print(f"官方標準處理結果:\n{anonymized_result.text}")
    print("-" * 50)

if __name__ == "__main__":
    main()