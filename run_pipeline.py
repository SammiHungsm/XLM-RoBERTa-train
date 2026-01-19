import subprocess
import sys
import time
import os

def run_command(command, step_name):
    print(f"\n{'='*50}")
    print(f"🚀 正在執行步驟: {step_name}")
    print(f"📝 指令: {command}")
    print(f"{'='*50}\n")

    start_time = time.time()
    process = subprocess.run(command, shell=True)
    end_time = time.time()
    duration = end_time - start_time

    if process.returncode == 0:
        print(f"\n✅ {step_name} 成功完成！ (耗時: {duration:.2f} 秒)")
        return True
    else:
        print(f"\n❌ {step_name} 失敗！ (錯誤碼: {process.returncode})")
        return False

def check_requirements():
    bank_dir = "./data/raw/banks"
    if not os.path.exists(bank_dir) or not os.listdir(bank_dir):
        print(f"⚠️  警告：在 {bank_dir} 找不到任何檔案。")
    else:
        files = os.listdir(bank_dir)
        print(f"📂 檢測到銀行數據資料夾，包含 {len(files)} 個檔案，準備就緒。")

def main():
    print("🤖 PII 模型訓練流水線 (Pipeline) 啟動...\n")
    check_requirements()

    # 1. 生成合成數據 (使用 -m)
    cmd_generate = f"{sys.executable} -m src.training.generate_synthetic_data"
    if not run_command(cmd_generate, "1. 生成合成數據 (Data Generation)"):
        sys.exit(1)

    # 2. 數據清洗 (使用 -m，確保路徑正確)
    # 🔥 修改：這裡也建議改用 -m，雖然之前成功了，但這樣更穩
    cmd_clean = f"{sys.executable} -m src.training.clean_and_augment"
    if not run_command(cmd_clean, "2. 數據清洗與增強 (Cleaning & Augmentation)"):
        sys.exit(1)

    # 3. 模型訓練 (使用 -m)
    # 🔥 關鍵修改：從 src/training/train_lora.py 改為 -m src.training.train_lora
    cmd_train = f"{sys.executable} -m src.training.train_lora"
    if not run_command(cmd_train, "3. 模型訓練 (Model Training)"):
        sys.exit(1)

    print("\n🎉🎉🎉 所有步驟圓滿完成！模型已訓練完畢。 🎉🎉🎉")
    print("👉 您現在可以執行 'python -m src.inference.inference' 來測試模型效果。")

if __name__ == "__main__":
    main()