import pandas as pd
import os
import glob

def load_bank_data(data_dir="./data/raw/banks"):
    """
    讀取金管局數據，支援 .csv, .xls, .xlsx
    回傳 (機構名單, 地址名單)
    """
    orgs = set()
    addresses = set()
    
    # 支援的表頭
    name_cols = ['名 稱', 'NAME', 'Name', '機構名稱']
    addr_cols = [
        '在 香 港 的 主 要 營 業 地 址', 
        '在 香 港 的 地 址', 
        'ADDRESS OF THE PRINCIPAL PLACE OF BUSSINESS IN HONG KONG',
        'ADDRESS OF THE PRINCIPAL PLACE OF BUSINESS IN HONG KONG',
        'ADDRESS IN HONG KONG',
        '地址'
    ]

    # 🔥 關鍵修改：搜尋所有可能的副檔名
    extensions = ['*.csv', '*.xls', '*.xlsx']
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(data_dir, ext)))

    if not files:
        print(f"⚠️  警告：在 {data_dir} 找不到銀行數據檔案 (.csv/.xls/.xlsx)。")
        return [], []

    print(f"📂 發現 {len(files)} 個銀行檔案，開始讀取...")

    for file in files:
        try:
            filename = os.path.basename(file)
            df = None
            
            # 🔥 智能讀取邏輯
            if file.lower().endswith(('.xls', '.xlsx')):
                try:
                    # 嘗試當作 Excel 讀取
                    # header=4 代表第 5 行是標題 (skiprows=4 的另一種寫法)
                    df = pd.read_excel(file, header=4)
                except Exception:
                    # 如果失敗，有些檔案雖然叫 .xls，其實是 Tab 分隔的文字檔
                    # 嘗試當作 CSV/Text 讀取
                    try:
                        df = pd.read_csv(file, skiprows=4, encoding='utf-8', sep='\t')
                    except:
                        df = pd.read_csv(file, skiprows=4, encoding='utf-16', sep='\t')
            else:
                # 正常的 CSV 讀取
                try:
                    df = pd.read_csv(file, skiprows=4, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file, skiprows=4, encoding='utf-16')
                except:
                    df = pd.read_csv(file, skiprows=4, encoding='big5')

            if df is None:
                print(f"❌ 無法識別檔案格式: {filename}")
                continue

            # 提取數據 (邏輯不變)
            count_o = 0
            count_a = 0
            
            # 提取名稱
            for col in name_cols:
                if col in df.columns:
                    clean_names = df[col].dropna().astype(str).apply(lambda x: x.strip())
                    orgs.update(clean_names)
                    count_o += len(clean_names)
            
            # 提取地址
            for col in addr_cols:
                if col in df.columns:
                    clean_addrs = df[col].dropna().astype(str).apply(
                        lambda x: x.replace('\n', ', ').replace('\r', '').strip()
                    )
                    valid_addrs = [a for a in clean_addrs if len(a) > 5]
                    addresses.update(valid_addrs)
                    count_a += len(valid_addrs)
            
            # print(f"  -> {filename}: 讀取了 {count_o} 個機構, {count_a} 個地址")

        except Exception as e:
            print(f"❌ 讀取 {os.path.basename(file)} 失敗: {e}")

    # 排序並回傳
    final_orgs = sorted(list(orgs))
    final_addrs = sorted(list(addresses))
    print(f"✅ 成功整合銀行數據：{len(final_orgs)} 個機構, {len(final_addrs)} 個地址")
    
    return final_orgs, final_addrs