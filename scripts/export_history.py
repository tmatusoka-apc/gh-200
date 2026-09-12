import os
import glob
import shutil
import sqlite3
import subprocess
import pandas as pd
import requests
from datetime import datetime

# --------------------------------------------------
# 設定エリア
# --------------------------------------------------
SCRIPT_DIR = os.path.dirname(__file__)
SAVE_FOLDER = os.path.join(SCRIPT_DIR, "00.hisotry") 
USER_DATA_DIR = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data"

# テンプレートファイルのパス（scriptsフォルダ内にある前提）
TEMPLATE_FILE = os.path.join(SCRIPT_DIR, "daily-note-temp.md")

# Gemini APIキーを環境変数から取得
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("エラー: 環境変数 'GEMINI_API_KEY' が設定されていません。")
    exit(1)

# --------------------------------------------------
# 1. 閲覧履歴の抽出
# --------------------------------------------------
os.makedirs(SAVE_FOLDER, exist_ok=True)

history_paths = []
default_path = os.path.join(USER_DATA_DIR, "Default", "History")
if os.path.exists(default_path):
    history_paths.append(("Default", default_path))

for p in glob.glob(os.path.join(USER_DATA_DIR, "Profile *")):
    p_name = os.path.basename(p)
    h_path = os.path.join(p, "History")
    if os.path.exists(h_path):
        history_paths.append((p_name, h_path))

all_dfs = []
temp_db = os.path.join(SAVE_FOLDER, "temp_chrome_history")

for p_name, h_path in history_paths:
    try:
        shutil.copy2(h_path, temp_db)
        conn = sqlite3.connect(temp_db)
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
            df['profile'] = p_name
            all_dfs.append(df)
            
    except Exception as e:
        print(f"読み込みエラー ({p_name}): {e}")
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

if not all_dfs:
    print("本日の閲覧履歴は見つかりませんでした。処理を終了します。")
    exit()

final_df = pd.concat(all_dfs, ignore_index=True)

# --------------------------------------------------
# 2. テンプレートの読み込み
# --------------------------------------------------
if not os.path.exists(TEMPLATE_FILE):
    print(f"エラー: テンプレートファイル '{TEMPLATE_FILE}' が見つかりません。")
    exit(1)

with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
    template_content = f.read()

# --------------------------------------------------
# 3. Gemini API で日報を生成
# --------------------------------------------------
print(f"履歴抽出完了 ({len(final_df)}件)。Gemini APIで日報を生成中...")

history_text = final_df[['visit_time', 'title', 'url']].to_string(index=False)
today_str = datetime.now().strftime("%Y%m%d")

prompt = f"""
あなたは優秀なアシスタントです。
以下のWeb閲覧履歴を解析し、指定された【日報テンプレート】の形式に完全に沿って本日の業務日報を作成してください。

【ルール】
- 無関係なログイン画面や検索エンジンのトップページなどの履歴は除外してください。
- 閲覧履歴から推測される具体的な技術名やサービス名を用いた自然な日本語にまとめてください。
- テンプレートの見出しや構造は変更せず、そのまま使用してください。

【日報テンプレート】
{template_content}

【閲覧履歴データ】
{history_text}
"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
headers = {"Content-Type": "application/json"}
payload = {"contents": [{"parts": [{"text": prompt}]}]}

response = requests.post(url, headers=headers, json=payload)

if response.status_code == 200:
    report_content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    
    # 日報Markdownをファイルとして保存
    report_filename = f"report_{today_str}.md"
    report_filepath = os.path.join(SAVE_FOLDER, report_filename)
    
    with open(report_filepath, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"日報の生成が完了しました: {report_filepath}")
else:
    print(f"Gemini API エラー (Status Code: {response.status_code}):")
    print(response.text)
    exit(1)

# --------------------------------------------------
# 4. 完成した日報(Markdown)だけをGitHubへGit Push
# --------------------------------------------------
try:
    repo_root = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
    
    subprocess.run(["git", "add", report_filepath], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", f"docs: add daily report for {today_str}"], cwd=repo_root, check=True)
    subprocess.run(["git", "push", "origin", "develop"], cwd=repo_root, check=True) 
    print("生成された日報をGitHubへ正常にPushしました。")
except subprocess.CalledProcessError as e:
    print(f"Git操作中にエラーが発生しました（変更がない可能性があります）: {e}")