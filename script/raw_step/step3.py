import json

def restore_data():
    try:
        with open("ai_response.txt", "r", encoding="utf-8") as f:
            ai_text = f.read()
        with open("mappings.json", "r", encoding="utf-8") as f:
            mappings = json.load(f)
    except FileNotFoundError:
        print("找不到必要檔案，請確保 Step 1 & 2 已執行")
        return

    final_text = ai_text
    for tag, real_value in mappings.items():
        final_text = final_text.replace(tag, real_value)

    with open("final_output.txt", "w", encoding="utf-8") as f:
        f.write(final_text)
    
    print("Step 3 完成：最終結果已儲存至 final_output.txt")
    print("\n--- 最終還原內容 ---")
    print(final_text)

if __name__ == "__main__":
    restore_data()