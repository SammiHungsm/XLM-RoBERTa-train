import requests
import json
import re

def call_ollama_qwen():
    # 1. 讀取 Step 1 生成的脫敏文字
    try:
        with open("masked_input.txt", "r", encoding="utf-8") as f:
            masked_text = f.read()
    except FileNotFoundError:
        print("❌ 找不到 masked_input.txt，請先執行 Step 1。")
        return

    # 2. 設定 Ollama API
    url = "http://localhost:11434/api/chat"
    
    # 提示詞 (System Prompt) 確保 AI 不會弄亂標籤
    payload = {
        "model": "qwen3:8b", 
        "messages": [
            {
                "role": "system", 
                "content": "你是一個專業助手。請根據用戶要求撰寫段落文字。注意：必須完整保留 [TagXX] 格式的標籤，嚴禁翻譯或修改標籤內容。請直接輸出段落文字，不要輸出 JSON。"
            },
            {
                "role": "user", 
                "content": f"根據以下內容寫一份聯繫摘要或備忘錄：\n{masked_text}"
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.2  # 較低的溫度確保標籤更穩定
        }
    }

    print("--- [Step 2] 正在傳送至 Ollama (Qwen3:8b) ---")
    print("提示：模型正在推理中，請耐心等候...")

    try:
        # 3. 發送請求 (設定較長的 timeout 因為 8B 模型推理較慢)
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        
        content = response.json()['message']['content']
        
        # 4. 處理推理模型標籤 (移除 <think> 內容)
        ai_reply = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

        # 5. 儲存 AI 回覆至 txt 檔案
        with open("ai_response.txt", "w", encoding="utf-8") as f:
            f.write(ai_reply)
            
        print("\n✅ Step 2 完成！")
        print("AI 原始回覆 (已儲存至 ai_response.txt):")
        print("-" * 30)
        print(ai_reply)
        print("-" * 30)

    except requests.exceptions.Timeout:
        print("❌ 錯誤：Ollama 回應超時。請確保你的電腦資源足夠運行 8B 模型。")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    call_ollama_qwen()