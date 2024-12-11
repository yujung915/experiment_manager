import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter
from hashlib import sha256
import io
from PIL import Image

# NumPy 2.0 이상 호환
np.Inf = np.inf

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
                    catalyst_amount REAL,
                    memo TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (synthesis_id) REFERENCES synthesis (id)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reaction_id INTEGER,
                    user_id INTEGER,
                    graph BLOB,
                    FOREIGN KEY (reaction_id) REFERENCES reaction (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )''')

    conn.commit()
    conn.close()

# 팝업 메시지 함수
def show_popup(message):
    st.session_state['popup_message'] = message

def display_popup():
    if 'popup_message' in st.session_state and st.session_state['popup_message']:
        st.info(st.session_state['popup_message'])
        if st.button("확인"):
            st.session_state['popup_message'] = ""

# 회원가입 페이지
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
                show_popup("회원가입에 성공하였습니다. 로그인 페이지로 이동하여 로그인 해주세요.")
                st.session_state['page'] = "Login"
            except sqlite3.IntegrityError:
                st.error("이미 존재하는 사용자 이름입니다.")
        else:
            st.error("모든 필드를 채워주세요.")

# 로그인 페이지
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
                st.session_state['page'] = "Synthesis"
                st.success("로그인 성공!")
            else:
                st.error("사용자 이름 또는 비밀번호가 올바르지 않습니다.")
            conn.close()
        else:
            st.error("모든 필드를 채워주세요.")

# 로그아웃 기능
def logout():
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['page'] = "Login"

# 결과 데이터 및 시각화 (그래프 저장 포함)
def result_section():
    st.header("Result Section")
    conn = get_connection()
    c = conn.cursor()

    user_id = st.session_state.get('user_id', None)
    c.execute("""SELECT reaction.id, reaction.date, reaction.temperature, 
                        reaction.catalyst_amount, synthesis.name
                 FROM reaction
                 JOIN synthesis ON reaction.synthesis_id = synthesis.id
                 WHERE reaction.user_id = ?""", (user_id,))
    reaction_options = c.fetchall()

    if reaction_options:
        reaction_id = st.selectbox(
            "Select Reaction",
            [f"ID: {row[0]} - Date: {row[1]} - Temp: {row[2]}°C - Catalyst: {row[4]}" for row in reaction_options]
        )

        if reaction_id:
            uploaded_file = st.file_uploader("Upload Result Data (Excel)", type=["xlsx"])

            if uploaded_file:
                try:
                    # 데이터 읽기
                    data = pd.read_excel(uploaded_file, engine="openpyxl")

                    if 'Time on stream (h)' in data.columns and 'DoDH(%)' in data.columns:
                        filtered_data = data[['Time on stream (h)', 'DoDH(%)']].dropna()
                        filtered_data = filtered_data[filtered_data['Time on stream (h)'] >= 1]

                        if not filtered_data.empty:
                            plt.figure(figsize=(10, 6))
                            plt.plot(filtered_data['Time on stream (h)'], filtered_data['DoDH(%)'], marker='o')
                            plt.xlabel("Time on stream (h)")
                            plt.ylabel("DoDH (%)")
                            plt.title("DoDH (%) vs Time on Stream (h)")
                            plt.legend()

                            # 그래프 저장
                            buf = io.BytesIO()
                            plt.savefig(buf, format='png')
                            buf.seek(0)

                            c.execute("INSERT INTO results (reaction_id, user_id, graph) VALUES (?, ?, ?)",
                                      (reaction_id, user_id, buf.read()))
                            conn.commit()
                            st.success("Graph saved to database.")
                        else:
                            st.warning("Filtered data is empty.")
                    else:
                        st.error("Required columns not found in file.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
    else:
        st.error("No reaction data available.")
    conn.close()

# 데이터 보기 및 수정/삭제
def view_data_section():
    st.header("View All Data")
    conn = get_connection()
    c = conn.cursor()

    user_id = st.session_state.get('user_id', None)
    c.execute("SELECT id, date, name FROM synthesis WHERE user_id = ?", (user_id,))
    data = c.fetchall()

    for row in data:
        if st.button(f"Delete Synthesis {row[0]}", key=f"delete_{row[0]}"):
            c.execute("DELETE FROM synthesis WHERE id = ?", (row[0],))
            conn.commit()
            st.experimental_rerun()
    conn.close()

def main():
    initialize_database()
    display_popup()

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None
    if 'page' not in st.session_state:
        st.session_state['page'] = "Login"

    if st.session_state['logged_in']:
        col1, col2 = st.columns([9, 1])
        with col2:
            if st.button("Logout"):
                logout()

        st.sidebar.title("Navigation")
        section = st.sidebar.radio("Select Section", ["Synthesis", "Reaction", "Results", "View Data"])
        if section == "Synthesis":
            synthesis_section()
        elif section == "Reaction":
            reaction_section()
        elif section == "Results":
            result_section()
        elif section == "View Data":
            view_data_section()
    else:
        if st.session_state['page'] == "Login":
            login()
        elif st.session_state['page'] == "Sign Up":
            signup()

if __name__ == "__main__":
    main()
