import subprocess
import sys
import time
import os
import argparse

def run_command(command, step_name):
    print(f"\n{'='*60}")
    print(f"🚀 正在執行步驟: {step_name}")
    print(f"📝 指令: {command}")
    print(f"{'='*60}\n")

    start_time = time.time()
    
    # 🔥 關鍵修正：確保 PYTHONPATH 包含當前目錄
    # 這能解決 "ModuleNotFoundError: No module named 'src'" 的問題
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")

    # 使用 unbuffered output (-u) 讓 log 即時顯示
    process = subprocess.run(command, shell=True, env=env)
    
    end_time = time.time()
    duration = end_time - start_time

    if process.returncode == 0:
        print(f"\n✅ {step_name} 成功完成！ (耗時: {duration:.2f} 秒)")
        return True
    else:
        print(f"\n❌ {step_name} 失敗！ (錯誤碼: {process.returncode})")
        return False

def check_requirements():
    """檢查必要的數據目錄是否存在"""
    bank_dir = "./data/raw/banks"
    required_dirs = ["./data/raw", "./data/processed", "./models", "./logs"]
    
    # 自動創建缺少的目錄
    for d in required_dirs:
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(bank_dir) or not os.listdir(bank_dir):
        print(f"⚠️  注意：在 {bank_dir} 找不到銀行數據檔案 (這會影響真實地址的生成)。")
        print("    建議將 .json/.geojson 檔案放入該目錄以獲得最佳效果。")
    else:
        files = os.listdir(bank_dir)
        print(f"📂 檢測到銀行數據資料夾，包含 {len(files)} 個檔案，準備就緒。")

def main():
    parser = argparse.ArgumentParser(description="PII 模型訓練流水線")
    parser.add_argument(
        "--steps", 
        type=str, 
        default="all", 
        help="指定要執行的步驟，用逗號分隔 (例如: gen,clean,train)。預設為 'all'。"
             "\n可選步驟: gen (生成), clean (清洗), train (訓練), eval (推理測試)"
    )
    args = parser.parse_args()

    print("🤖 PII 模型訓練流水線 (Pipeline) 啟動...\n")
    check_requirements()

    # 解析步驟
    steps_to_run = args.steps.split(",")
    if "all" in steps_to_run:
        steps_to_run = ["gen", "clean", "train", "eval"]

    python_exec = sys.executable

    # ==========================================
    # 1. 生成合成數據 (Data Generation)
    # ==========================================
    if "gen" in steps_to_run:
        cmd_generate = f"{python_exec} -m src.training.generate_synthetic_data"
        if not run_command(cmd_generate, "1. 生成合成數據 (Generation)"):
            sys.exit(1)
    else:
        print("⏩ 跳過步驟 1: 生成數據")

    # ==========================================
    # 2. 數據清洗與增強 (Data Cleaning)
    # ==========================================
    if "clean" in steps_to_run:
        cmd_clean = f"{python_exec} -m src.training.clean_and_augment"
        if not run_command(cmd_clean, "2. 數據清洗與增強 (Cleaning)"):
            sys.exit(1)
    else:
        print("⏩ 跳過步驟 2: 數據清洗")

    # ==========================================
    # 3. 模型訓練 (Model Training)
    # ==========================================
    if "train" in steps_to_run:
        # 這裡會使用 train_lora.py 裡設定的參數 (如 patience=10)
        cmd_train = f"{python_exec} -m src.training.train_lora"
        if not run_command(cmd_train, "3. 模型訓練 (Training - LoRA)"):
            sys.exit(1)
    else:
        print("⏩ 跳過步驟 3: 模型訓練")

    # ==========================================
    # 4. 推理評估 (Evaluation / Inference)
    # ==========================================
    # 🔥 自動執行推理，驗證 "長和主席" 和 "車牌修復" 是否生效
    if "eval" in steps_to_run:
        # 假設你的推理腳本在 src.inference.inference
        # 如果你有特定的測試腳本，請修改這裡
        cmd_eval = f"{python_exec} -m src.inference.inference"
        # 或者如果你想跑 run_pipeline.py 提到的長文本滑動視窗測試，可以指向該腳本
        
        if not run_command(cmd_eval, "4. 模型推理測試 (Inference Check)"):
            print("⚠️ 推理步驟執行失敗，請檢查 src.inference.inference 是否存在。")
            # 不強制退出，因為訓練已經完成了
    else:
        print("⏩ 跳過步驟 4: 推理測試")

    print(f"\n{'='*60}")
    print("🎉🎉🎉 流水線執行完畢！ 🎉🎉🎉")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()