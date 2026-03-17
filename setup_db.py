import sqlite3

def init_db():
    conn = sqlite3.connect('kendo_app.db')
    cursor = conn.cursor()

    # 判定結果を保存するテーブルを作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS waza_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        waza_name TEXT,
        confidence REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()
    print("✅ データベース(kendo_app.db)を新しく作成しました！")

if __name__ == "__main__":
    init_db()