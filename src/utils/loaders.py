# src/utils/loaders.py
import json
import os
import random
import re
from pathlib import Path

# ==========================================
# ✅ 1. 配置與黑名單管理 (Configuration)
# ==========================================

# 1.1 基礎禁止詞 (完全禁止，出現即丟棄)
try:
    from src.config import BASE_FORBIDDEN
except ImportError:
    BASE_FORBIDDEN = ["測試", "Test", "Unknown", "N/A", "null", "None"]

# 1.2 機構名 (部分禁止：允許作為長地址的一部分，但不允許單獨作為地址)
try:
    from src.utils.templates import ALL_HK_ORGS
except ImportError:
    ALL_HK_ORGS = ["HSBC", "MTR", "HKJC", "HKU", "CUHK", "Alibaba", "Tencent"]

# 1.3 常見中文地名 (用於補強 train.jsonl 只有英文的問題)
COMMON_CN_LOCATIONS = [
    "中國", "香港", "澳門", "台灣", "北京", "上海", "廣州", "深圳", 
    "美國", "英國", "日本", "韓國", "新加坡", "九龍", "新界"
]

# 構建過濾集合
STRICT_FORBIDDEN = set(BASE_FORBIDDEN)       # 絕對禁止
PARTIAL_FORBIDDEN = set(ALL_HK_ORGS)         # 允許出現在長地址中

# 1.4 地址暗示詞 (用於負樣本清洗，包含這些詞的句子不應作為負樣本)
ADDRESS_HINTS = [
    "街", "道", "路", "苑", "樓", "室", "廈", "區", "村", "號", 
    "Street", "Road", "Building", "Floor", "Room", "District", "Tower"
]

# ==========================================
# 🛠️ 輔助工具 (Helpers)
# ==========================================
def _safe_str_get(data, key):
    """
    [Data Type Consistency] 安全提取字串，防止 AttributeError
    """
    if not isinstance(data, dict): return ""
    val = data.get(key, "")
    return val.strip() if isinstance(val, str) else ""

# ==========================================
# ✅ 2. 名字載入器 (Name Loader)
# ==========================================
def load_names(corpus_folder):
    """
    載入名字庫，並提供數據審計日誌。
    """
    data = {"transliterated": [], "standard": []}
    folder_path = Path(corpus_folder)
    
    # 預設數據
    default_data = {
        "transliterated": ["阿諾", "史泰龍", "伊隆", "馬斯克"],
        "standard": ["陳大文", "李嘉誠", "田中太郎"]
    }
    
    if not folder_path.exists():
        print(f"⚠️ 警告：找不到名字庫 {corpus_folder}，使用預設值。")
        return default_data

    try:
        txt_files = list(folder_path.glob("*.txt"))
        if not txt_files: return default_data

        for file_path in txt_files:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            
            if "English_Cn_Name" in file_path.name:
                data["transliterated"].extend(lines)
            else:
                data["standard"].extend(lines)
        
        # 去重
        data["transliterated"] = list(set(data["transliterated"]))
        data["standard"] = list(set(data["standard"]))
        
        # 確保不為空
        if not data["standard"]: data["standard"] = default_data["standard"]
        
        # [Data Audit] 日誌記錄
        print(f"✅ [Name Loader] 載入完成:")
        print(f"   - 標準名 (Standard): {len(data['standard'])} (Sample: {random.sample(data['standard'], min(3, len(data['standard'])))})")
        print(f"   - 譯名 (Transliterated): {len(data['transliterated'])} (Sample: {random.sample(data['transliterated'], min(3, len(data['transliterated'])))})")
        
        return data

    except Exception as e:
        print(f"❌ 載入名字失敗: {e}")
        return default_data

# ==========================================
# ✅ 3. 全球地理數據載入器 (Global Geo Data Loader)
# ==========================================
def load_global_geo_data(file_path):
    """
    [New Feature] 解析 train.jsonl (全球城市/國家數據)
    """
    geo_terms = set()
    path = Path(file_path)
    
    if not path.exists():
        print(f"⚠️ 警告：找不到全球地理數據 {file_path}")
        return set(COMMON_CN_LOCATIONS) # Fallback

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line)
                    # 提取需要的層級
                    if city := _safe_str_get(item, "city"): geo_terms.add(city)
                    if country := _safe_str_get(item, "country"): geo_terms.add(country)
                    if region := _safe_str_get(item, "region"): geo_terms.add(region)
                except json.JSONDecodeError:
                    continue
        
        # 加入中文常見地名補強
        geo_terms.update(COMMON_CN_LOCATIONS)
        
        print(f"✅ [Geo Loader] 已載入 {len(geo_terms)} 個全球地名 (含中文補強)")
        return geo_terms
    except Exception as e:
        print(f"❌ 載入全球地理數據失敗: {e}")
        return set(COMMON_CN_LOCATIONS)

# ==========================================
# ✅ 4. 地址解析核心 (Address Parser)
# ==========================================
def parse_one_feature(feature):
    """
    [Address Parser Risk] 深度解析 GeoJSON，並區分完整地址與片段。
    Returns:
        full_combos (set): 完整地址 (包含街道+門牌 或 屋苑+座號)
        fragment_combos (set): 地址片段 (單獨的區、街名)
    """
    props = feature.get("properties", {})
    root = props.get("Address", {}).get("PremisesAddress", {})
    if not root: root = props 

    full_combos = set()
    fragment_combos = set()

    # --- 4.1 中文地址解析 ---
    chi_root = root.get("ChiPremisesAddress", {})
    if chi_root:
        # [Data Type Consistency] 使用 _safe_str_get
        c_region = _safe_str_get(chi_root, "Region")
        
        # 處理 ChiDistrict 可能為物件的情況
        raw_dist = chi_root.get("ChiDistrict", "")
        c_district = raw_dist if isinstance(raw_dist, str) else _safe_str_get(raw_dist, "ChiDistrict")

        c_street_obj = chi_root.get("ChiStreet", {})
        c_street_name = _safe_str_get(c_street_obj, "StreetName")
        c_bldg_no = _safe_str_get(c_street_obj, "BuildingNoFrom")
        
        c_street_full = f"{c_street_name}{c_bldg_no}號" if (c_street_name and c_bldg_no) else c_street_name

        c_estate_obj = chi_root.get("ChiEstate", {})
        c_estate = _safe_str_get(c_estate_obj, "EstateName")
        
        c_bldg_obj = chi_root.get("ChiBuilding", {})
        c_bldg = _safe_str_get(c_bldg_obj, "BuildingName")

        c_block_obj = chi_root.get("ChiBlock", {})
        c_block = _safe_str_get(c_block_obj, "BlockNo")

        # --- 分類邏輯 ---
        # 1. 片段 (Fragments) - 單獨出現容易導致 Overfitting，需控制比例
        if c_region: fragment_combos.add(c_region)
        if c_district: fragment_combos.add(c_district)
        if c_street_name: fragment_combos.add(c_street_name)
        if c_estate: fragment_combos.add(c_estate)

        # 2. 組合/完整地址 (Full/Combined)
        parts = [p for p in [c_region, c_district, c_street_full, c_estate, c_bldg, c_block] if p]
        
        # 區域 + 街道
        if c_district and c_street_full: full_combos.add(f"{c_district}{c_street_full}")
        # 街道 + 屋苑
        if c_street_full and c_estate: full_combos.add(f"{c_street_full}{c_estate}")
        # 完整串接
        full_addr = "".join(parts)
        if len(full_addr) > 5: # 確保足夠長
            full_combos.add(full_addr)

    # --- 4.2 英文地址解析 (邏輯同上) ---
    eng_root = root.get("EngPremisesAddress", {})
    if eng_root:
        e_region = _safe_str_get(eng_root, "Region")
        
        raw_e_dist = eng_root.get("EngDistrict", "")
        e_district = raw_e_dist if isinstance(raw_e_dist, str) else _safe_str_get(raw_e_dist, "EngDistrict")
        
        e_street_obj = eng_root.get("EngStreet", {})
        e_st_name = _safe_str_get(e_street_obj, "StreetName")
        e_bldg_no = _safe_str_get(e_street_obj, "BuildingNoFrom")
        
        e_st_full = f"{e_bldg_no} {e_st_name}" if (e_st_name and e_bldg_no) else e_st_name
        
        e_estate_obj = eng_root.get("EngEstate", {})
        e_estate = _safe_str_get(e_estate_obj, "EstateName")
        
        e_bldg_obj = eng_root.get("EngBuilding", {})
        e_bldg = _safe_str_get(e_bldg_obj, "BuildingName")

        # 片段
        if e_region: fragment_combos.add(e_region)
        if e_district: fragment_combos.add(e_district)
        if e_st_name: fragment_combos.add(e_st_name)
        
        # 完整
        e_parts = [p for p in [e_estate, e_bldg, e_st_full, e_district, e_region] if p]
        if len(e_parts) > 1:
            full_combos.add(", ".join(e_parts))

    return full_combos, fragment_combos

# ==========================================
# ✅ 5. 地址載入器 (Address Loader)
# ==========================================
def load_addresses(geojson_path, global_geo_path=None):
    """
    載入並清洗地址數據。
    Args:
        geojson_path: 香港 GeoJSON 數據路徑
        global_geo_path: (Optional) train.jsonl 全球數據路徑
    Returns:
        (full_addresses_list, location_fragments_list) 
    """
    # [Performance] 使用 Set 避免重複與大量 extend 開銷
    full_set = set()
    fragment_set = set()
    
    # 1. 載入 Global Geo Data (解決泛指地名問題)
    if global_geo_path:
        print(f"🌍 [Address Loader] 正在載入全球地理數據...")
        global_terms = load_global_geo_data(global_geo_path)
        fragment_set.update(global_terms) # 國家/城市視為片段或短地址

    # 2. 載入 GeoJSON Data
    path = Path(geojson_path)
    files = []
    if not path.exists():
        print(f"⚠️ 警告：找不到 GeoJSON 路徑 {geojson_path}")
    elif path.is_file():
        files = [path]
    else:
        files = list(path.glob("*.json")) + list(path.glob("*.geojson"))
    
    # print(f"📂 [Address Loader] 正在解析 {len(files)} 個 GeoJSON 檔案...")
    
    for p in files:
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                features = data.get("features", [])
                for feat in features:
                    f_full, f_frag = parse_one_feature(feat)
                    full_set.update(f_full)
                    fragment_set.update(f_frag)
        except Exception as e:
            pass

    # 3. 定義清洗邏輯 (內部函數，避免重複代碼)
    def clean_set(source_set):
        cleaned = set()
        for addr in source_set:
            addr = addr.strip()
            if len(addr) < 2: continue # 太短的丟棄
            
            # [Strict Forbidden Filter] 嚴格黑名單 (測試數據等) -> 直接殺
            if any(bad in addr for bad in STRICT_FORBIDDEN):
                continue
                
            # [Partial Forbidden Filter] 機構名
            # 如果地址「完全等於」機構名 (例如 "HSBC") -> 殺 (因為這是 ORG 不是 ADDRESS)
            if addr in PARTIAL_FORBIDDEN:
                continue
                
            cleaned.add(addr)
        return list(cleaned)

    # 4. 分別執行清洗
    final_full = clean_set(full_set)
    final_frags = clean_set(fragment_set)
    
    # [Data Audit] 審計日誌
    if final_full or final_frags:
        print(f"✅ [Address Loader] 載入完成")
        print(f"   - 完整地址 (Full): {len(final_full)} 條")
        print(f"   - 地名碎片 (Frag): {len(final_frags)} 條")
        if final_full:
            print(f"   - Full Sample: {random.sample(final_full, min(3, len(final_full)))}")
    else:
        print("⚠️ [Address Loader] 警告：地址庫為空，使用 fallback")
        # 回傳預設值，注意也要是兩個列表
        return (["香港中環德輔道中88號", "九龍塘", "屯門市廣場"], ["香港", "九龍", "新界"])

    # 🔥 關鍵修正：回傳兩個列表以配合 generate_synthetic_data.py 的解包
    return final_full, final_frags

# ==========================================
# ✅ 6. 負樣本載入器 (Negative Sample Loader)
# ==========================================
def load_negative_samples(source, max_samples=10000):
    """
    從數據集中提取負樣本 (不含 PII 的句子)。
    """
    samples = set() # [Performance] Use set
    target_files = []
    
    if isinstance(source, list):
        target_files = [Path(p) for p in source]
    else:
        folder = Path(source)
        if folder.exists():
            target_files = list(folder.glob("*.json"))
    
    print(f"🛡️ [Negative Loader] 正在掃描 {len(target_files)} 個檔案...")

    for path in target_files:
        if not path.exists(): continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                data_list = raw.get("data", []) if isinstance(raw, dict) else raw
                if not isinstance(data_list, list): continue

                for item in data_list:
                    tokens = item.get("tokens", [])
                    tags = item.get("ner_tags", [])
                    
                    if len(tokens) != len(tags): continue
                    
                    # 1. 基礎檢查：全為 O 標籤
                    if all(t == 0 for t in tags):
                        sent = "".join(tokens)
                        
                        if 5 < len(sent) < 200:
                            # 2. [Negative Sample Logic] 關鍵字檢查 (Purity Check)
                            # 如果句子含有「街」、「道」、「Room」等詞，即使標註為 O，也有可能是漏標
                            # 我們寧可錯殺，不可放過，確保負樣本絕對純淨
                            if any(hint in sent for hint in ADDRESS_HINTS):
                                continue
                                
                            # 3. 嚴格敏感詞檢查
                            if not any(bad in sent for bad in STRICT_FORBIDDEN):
                                samples.add(sent)
                                
        except Exception:
            pass

    final_samples = list(samples)
    
    # [Data Feeding Verification] 數量控制
    if len(final_samples) > max_samples:
        print(f"   ✂️ 負樣本過多 ({len(final_samples)})，隨機採樣至 {max_samples}")
        final_samples = random.sample(final_samples, max_samples)
        
    print(f"✅ [Negative Loader] 負樣本準備完成: {len(final_samples)} 條")
    return final_samples