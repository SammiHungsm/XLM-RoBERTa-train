🛠️ 完整訓練流程 (The Workflow)
第一階段：準備原始素材
首先，確保你已經從不同來源生成了原始 JSON 數據。

生成新聞數據: python -m src.training.process_news

生成港鐵數據: python -m src.training.process_mtr_news

(如有) 生成小說/合成數據: python -m src.training.generate_synthetic_data 等

第二階段：打包數據 (Aggregation)
將上面所有的 Raw Data 集合在一起。 4. 打包: python -m src.training.prepare_data * 輸入: data/raw/*.json * 輸出: train_data_lora.json (這是包含所有數據的大文件，但可能含有「長機構名」等隱患)

第三階段：清洗與增強 (Sanitization) 👈 這裡 Call clean_and_argument.py
這是我們新加的關鍵步驟，用來解決 "Case 17" 過度遮蔽的問題。 5. 清洗: python -m src.training.clean_and_augment * 輸入: train_data_lora.json * 動作: * 檢查有無長度 > 15 的 ORG，有的話強制切斷。 * 注入「負面樣本」(Negative Samples) 教模型分辯邊界。 * 輸出: train_data_lora_cleaned.json (這才是最終完美的訓練數據)

第四階段：開始訓練 (Training)
訓練: python -m src.training.train_lora

注意: 確保你的 train_lora.py 裡面的代碼已經修改為讀取 train_data_lora_cleaned.json。