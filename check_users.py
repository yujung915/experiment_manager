import sqlite3

# 데이터베이스 연결
conn = sqlite3.connect("experiment_manager.db")
c = conn.cursor()

# 사용자 데이터 확인
c.execute("SELECT id, username FROM users")
users = c.fetchall()

print("Existing Users:")
for user in users:
    print(f"ID: {user[0]}, Username: {user[1]}")

conn.close()
