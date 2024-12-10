import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from hashlib import sha256

# 데이터베이스 연결 함수
def get_connection():
    return sqlite3.connect("experiment_manager.db", check_same_thread=False)

# 비밀번호 해싱 함수
def hash_password(password):
    return sha256(password.encode()).hexdigest()

# 데이터베이스 초기화 함수
def initialize_database():
    conn = get_connection()
    c = conn.cursor()

    # 사용자 테이블 생성
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT
                )''')

    # 합성 테이블 생성
    c.execute('''CREATE TABLE IF NOT EXISTS synthesis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    name TEXT,
                    memo TEXT,
                    amount REAL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )''')

    # 반응 테이블 생성
    c.execute('''CREATE TABLE IF NOT EXISTS reaction (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    synthesis_id INTEGER,
                    date TEXT,
                    temperature REAL,
                    pressure REAL,
                    catalyst_amount REAL,
                    memo TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (synthesis_id) REFERENCES synthesis (id)
                )''')

    # 결과 테이블 생성
    c.execute('''CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reaction_id INTEGER,
                    user_id INTEGER,
                    time_series TEXT,
                    dodh_series TEXT,
                    max_dodh REAL,
                    FOREIGN KEY (reaction_id) REFERENCES reaction (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )''')

    conn.commit()
    conn.close()

# 로그인 함수
def login():
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username and password:
            conn = get_connection()
            c = conn.cursor()

            # 사용자 확인
            c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            user = c.fetchone()

            if user and user[1] == hash_password(password):
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user[0]
                st.success("Logged in successfully!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")
            conn.close()
        else:
            st.error("Please fill in both fields.")

# 회원가입 함수
def signup():
    st.header("Sign Up")
    username = st.text_input("Create Username")
    password = st.text_input("Create Password", type="password")

    if st.button("Sign Up"):
        if username and password:
            try:
                conn = get_connection()
                c = conn.cursor()

                # 비밀번호 해싱 후 저장
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
                conn.commit()
                conn.close()

                st.success("Account created! Please log in.")
                st.experimental_rerun()
            except sqlite3.IntegrityError:
                st.error("Username already exists.")

# 결과 섹션
def result_section():
    st.header("Result Analysis")
    conn = get_connection()
    c = conn.cursor()

    user_id = st.session_state.get('user_id', None)
    c.execute("""SELECT reaction.id, reaction.date, reaction.temperature, reaction.pressure, 
                        reaction.catalyst_amount, synthesis.name
                 FROM reaction
                 JOIN synthesis ON reaction.synthesis_id = synthesis.id
                 WHERE reaction.user_id = ?""", (user_id,))
    reaction_options = c.fetchall()

    if reaction_options:
        reaction_id = st.selectbox(
            "Select Reaction",
            [f"ID: {row[0]} - Date: {row[1]} - Temp: {row[2]}°C - Catalyst: {row[5]}" for row in reaction_options]
        )

        if reaction_id:
            selected_reaction = [row for row in reaction_options if f"ID: {row[0]}" in reaction_id][0]
            st.write(f"**Reaction Conditions:**")
            st.write(f"- Temperature: {selected_reaction[2]}°C")
            st.write(f"- Pressure: {selected_reaction[3]} atm")
            st.write(f"- Catalyst Amount: {selected_reaction[4]} g")
            st.write(f"- Catalyst Name: {selected_reaction[5]}")
    else:
        st.write("No reaction data available. Please add reaction data first.")
    conn.close()

# 로그아웃 기능
def logout():
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.experimental_rerun()

# 메인 함수
def main():
    initialize_database()

    # 세션 상태 초기화
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None

    # 로그인 상태 확인 및 화면 구성
    if st.session_state['logged_in']:
        st.sidebar.title("Navigation")
        section = st.sidebar.radio("Select Section", ["Results"])

        if section == "Results":
            result_section()

        st.sidebar.button("Logout", on_click=logout)
    else:
        page = st.sidebar.radio("Choose an option", ["Login", "Sign Up"])
        if page == "Login":
            login()
        elif page == "Sign Up":
            signup()

if __name__ == "__main__":
    main()
