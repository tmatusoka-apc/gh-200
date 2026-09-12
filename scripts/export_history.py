import os
import glob
import shutil
import sqlite3
import pandas as pd
from datetime import datetime

# --------------------------------------------------
# 設定エリア
# --------------------------------------------------
SAVE_FOLDER = r"C:\Users\t_matsuoka_ap-com\workspace\test\00.output"
USER_DATA_DIR = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data"

# --------------------------------------------------
# 処理本体
# --------------------------------------------------
os.makedirs(SAVE_FOLDER, exist_ok=True)

# 1. User Data 内のすべてのプロファイル（Default, Profile 1, Profile 2 ...）のHistoryを探す
history_paths = []
default_path = os.path.join(USER_DATA_DIR, "Default", "History")
if os.path.exists(default_path):
    history_paths.append(("Default", default_path))

for p in glob.glob(os.path.join(USER_DATA_DIR, "Profile *")):
    p_name = os.path.basename(p)
    h_path = os.path.join(p, "History")
    if os.path.exists(h_path):
        history_paths.append((p_name, h_path))

print(f"検索されたプロファイル数: {len(history_paths)}")

all_dfs = []
temp_db = os.path.join(SAVE_FOLDER, "temp_chrome_history")

# 2. 各プロファイルの履歴を走査
for p_name, h_path in history_paths:
    try:
        shutil.copy2(h_path, temp_db)
        conn = sqlite3.connect(temp_db)
        
        # 本日の履歴をPCのローカル時刻（本日00:00以降）基準で抽出
        query = """
        SELECT 
            datetime(v.visit_time / 1000000 - 11644473600, 'unixepoch', 'localtime') AS visit_time,
            u.title,
            u.url
        FROM visits v
        JOIN urls u ON v.url = u.id
        WHERE datetime(v.visit_time / 1000000 - 11644473600, 'unixepoch', 'localtime') >= date('now', 'localtime')
        ORDER BY v.visit_time DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            print(f"  - 【{p_name}】: {len(df)}件の履歴が見つかりました")
            df['profile'] = p_name
            all_dfs.append(df)
        else:
            print(f"  - 【{p_name}】: 0件")
            
    except Exception as e:
        print(f"  - 【{p_name}】の読み込み中にエラー発生: {e}")
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

# 3. 集計結果をCSV出力
if all_dfs:
    final_df = pd.concat(all_dfs, ignore_index=True)
    today_str = datetime.now().strftime("%Y%m%d")
    output_filepath = os.path.join(SAVE_FOLDER, f"history_{today_str}.csv")
    final_df.to_csv(output_filepath, index=False, encoding="utf-8-sig")
    print(f"\n保存完了: {output_filepath} (合計 {len(final_df)}件)")
else:
    print("\n本日分の履歴は見つかりませんでした。")