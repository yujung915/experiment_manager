import sqlite3

# 데이터베이스 연결
conn = sqlite3.connect("experiment_manager.db")
c = conn.cursor()

# 사용자 이름 입력
username = input("Enter the username for which you want to change the password: ")

# 새 비밀번호 입력
new_password = input("Enter the new password: ")

try:
    # 사용자 이름이 존재하는지 확인
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = c.fetchone()

    if user:
        # 비밀번호 업데이트
        c.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
        conn.commit()
        print(f"Password for '{username}' has been successfully updated!")
    else:
        print(f"Username '{username}' does not exist.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    conn.close()
