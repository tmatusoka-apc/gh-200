# 📝 Chrome History to Daily Report

Chromeの閲覧履歴（ローカルのSQLiteデータベース）を自動で抽出し、AI（NotebookLM / Gemini等）を用いて業務日報を半自動生成するシステムです。

## 💡 概要・目的
日々の業務において「今日1日何をやっていたか」を思い出す手間を省き、日報作成にかかる時間を数分レベルまで短縮することを目的としています。
Chromeのローカルデータベース（`User Data`）から全プロファイルの閲覧履歴を検索・集計し、指定した時刻に本日のアクセス履歴をCSVとして自動エクスポートします。

## 🏗 アーキテクチャ

1. **データ抽出**: Pythonスクリプト (`export_history.py`)
2. **自動実行**: Windows タスクスケジューラ
3. **日報生成**: NotebookLM (Google) ＋ 専用プロンプト

---

## 🚀 セットアップ手順

### 1. 動作環境の準備
* **OS:** Windows 10 / 11
* **言語:** Python 3.x
* **必要なライブラリ:**
  ```bash
  pip install pandas