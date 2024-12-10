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
def initialize_database(reset=False):
    conn = get_connection()
    c = conn.cursor()

    if reset:
        c.execute("DROP TABLE IF EXISTS users")
        c.execute("DROP TABLE IF EXISTS synthesis")
        c.execute("DROP TABLE IF EXISTS reaction")
        c.execute("DROP TABLE IF EXISTS results")

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
                    amount REAL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )''')
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

            c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            user = c.fetchone()

            if user and user[1] == hash_password(password):
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user[0]
                st.success("Logged in successfully!")
                if "rerun" not in st.session_state:
                    st.session_state["rerun"] = True
                else:
                    st.session_state["rerun"] = not st.session_state["rerun"]
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
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
                conn.commit()
                conn.close()
                st.success("Account created! Please log in.")
                if "rerun" not in st.session_state:
                    st.session_state["rerun"] = True
                else:
                    st.session_state["rerun"] = not st.session_state["rerun"]
            except sqlite3.IntegrityError:
                st.error("Username already exists.")

# 로그아웃 기능
def logout():
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    if "rerun" not in st.session_state:
        st.session_state["rerun"] = True
    else:
        st.session_state["rerun"] = not st.session_state["rerun"]

# 합성 섹션
def synthesis_section():
    st.header("Synthesis Section")
    st.write("Synthesis data can be added here.")

# 반응 섹션
def reaction_section():
    st.header("Reaction Section")
    st.write("Reaction data can be added here.")

# 메인 함수
def main():
    # 데이터베이스 초기화
    reset = st.sidebar.button("Reset Database")
    if reset:
        initialize_database(reset=True)
        st.success("Database reset successfully!")
        st.stop()

    initialize_database()

    # 세션 상태 초기화
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None

    if st.session_state['logged_in']:
        st.sidebar.title("Navigation")
        section = st.sidebar.radio("Select Section", ["Synthesis", "Reaction", "Logout"])

        if section == "Synthesis":
            synthesis_section()
        elif section == "Reaction":
            reaction_section()
        elif section == "Logout":
            logout()
    else:
        page = st.sidebar.radio("Choose an option", ["Login", "Sign Up"])
        if page == "Login":
            login()
        elif page == "Sign Up":
            signup()

if __name__ == "__main__":
    main()
