import streamlit as st
import sqlite3
import hashlib
import pandas as pd

# 데이터베이스 연결
conn = sqlite3.connect("experiment_manager.db")
c = conn.cursor()

# 데이터베이스 초기화
c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS synthesis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                name TEXT,
                memo TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS reaction (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                synthesis_id INTEGER,
                date TEXT,
                temperature REAL,
                pressure REAL,
                memo TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (synthesis_id) REFERENCES synthesis (id)
            )''')

conn.commit()

# 비밀번호 해싱 함수
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 로그인 기능
def login():
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        hashed_password = hash_password(password)
        c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hashed_password))
        user = c.fetchone()
        if user:
            st.session_state['logged_in'] = True
            st.session_state['user_id'] = user[0]
            st.success(f"Logged in as {username}")
        else:
            st.error("Invalid username or password")

# 회원가입 기능
def signup():
    st.header("Sign Up")
    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")
    if st.button("Sign Up"):
        hashed_password = hash_password(password)
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            st.success("Account created successfully! Please login.")
        except sqlite3.IntegrityError:
            st.error("Username already exists")

# 합성 섹션
def synthesis_section():
    st.header("Synthesis Data Input")
    synthesis_date = st.date_input("Synthesis Date")
    synthesis_name = st.text_input("Catalyst Name")
    synthesis_memo = st.text_area("Memo (Optional)")

    if st.button("Add Synthesis Data"):
        user_id = st.session_state['user_id']
        c.execute("INSERT INTO synthesis (user_id, date, name, memo) VALUES (?, ?, ?, ?)",
                  (user_id, str(synthesis_date), synthesis_name, synthesis_memo))
        conn.commit()
        st.success("Synthesis data added successfully!")

    # Synthesis 데이터 보기 및 삭제
    st.header("View Synthesis Data")
    user_id = st.session_state['user_id']
    c.execute("SELECT * FROM synthesis WHERE user_id = ?", (user_id,))
    synthesis_data = c.fetchall()
    if synthesis_data:
        for row in synthesis_data:
            col1, col2 = st.columns([4, 1])  # 데이터와 삭제 버튼을 열 형태로 배치
            with col1:
                st.write(f"ID: {row[0]}, Date: {row[2]}, Name: {row[3]}, Memo: {row[4]}")
            with col2:
                if st.button("🗑️", key=f"delete_synthesis_{row[0]}"):
                    c.execute("DELETE FROM synthesis WHERE id = ?", (row[0],))
                    conn.commit()
                    st.success(f"Synthesis ID {row[0]} deleted!")
    else:
        st.write("No synthesis data available.")

# 반응 섹션
def reaction_section():
    st.header("Reaction Data Input")

    # Synthesis 데이터 가져오기
    user_id = st.session_state['user_id']
    c.execute("SELECT id, date, name FROM synthesis WHERE user_id = ?", (user_id,))
    synthesis_options = c.fetchall()
    synthesis_id = st.selectbox(
        "Select Synthesis (ID + Date + Catalyst Name)",
        [f"ID: {row[0]} - {row[1]} - {row[2]}" for row in synthesis_options]
    )

    reaction_date = st.date_input("Reaction Date")
    reaction_temperature = st.number_input("Reaction Temperature (°C)", step=0.1)
    reaction_pressure = st.number_input("Pressure (atm)", step=0.1)
    reaction_memo = st.text_area("Memo (Optional)")

    if st.button("Add Reaction Data"):
        selected_synthesis_id = int(synthesis_id.split("ID: ")[-1].split(" - ")[0])
        c.execute("INSERT INTO reaction (user_id, synthesis_id, date, temperature, pressure, memo) VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, selected_synthesis_id, str(reaction_date), reaction_temperature, reaction_pressure, reaction_memo))
        conn.commit()
        st.success("Reaction data added successfully!")

    # Reaction 데이터 보기 및 삭제
    st.header("View Reaction Data")
    c.execute('''SELECT reaction.id, reaction.date, reaction.temperature, reaction.pressure, reaction.memo, synthesis.id AS synthesis_id, synthesis.date AS synthesis_date, synthesis.name AS synthesis_name
                 FROM reaction
                 JOIN synthesis ON reaction.synthesis_id = synthesis.id
                 WHERE reaction.user_id = ?''', (user_id,))
    reaction_data = c.fetchall()
    if reaction_data:
        for row in reaction_data:
            col1, col2 = st.columns([4, 1])  # 데이터와 삭제 버튼을 열 형태로 배치
            with col1:
                st.write(f"ID: {row[0]}, Date: {row[1]}, Temperature: {row[2]}°C, Pressure: {row[3]} atm, Memo: {row[4]}, Linked Synthesis: [ID: {row[5]}, Date: {row[6]}, Name: {row[7]}]")
            with col2:
                if st.button("🗑️", key=f"delete_reaction_{row[0]}"):
                    c.execute("DELETE FROM reaction WHERE id = ?", (row[0],))
                    conn.commit()
                    st.success(f"Reaction ID {row[0]} deleted!")
    else:
        st.write("No reaction data available.")

# 로그아웃 기능
def logout():
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.experimental_rerun()

# 앱 상태 관리
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None

# 메인 앱
if st.session_state['logged_in']:
    st.sidebar.title("Navigation")
    section = st.sidebar.radio("Select Section", ["Synthesis", "Reaction"])
    if section == "Synthesis":
        synthesis_section()
    elif section == "Reaction":
        reaction_section()

    # 로그아웃 버튼 (왼쪽 아래)
    with st.sidebar:
        st.button("Logout", on_click=logout)
else:
    st.sidebar.title("Authentication")
    page = st.sidebar.radio("Choose an option", ["Login", "Sign Up"])
    if page == "Login":
        login()
    elif page == "Sign Up":
        signup()
