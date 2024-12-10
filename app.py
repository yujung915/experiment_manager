import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter
from hashlib import sha256
import io  # 그래프 저장용

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

# 로그아웃 버튼
def logout_button():
    if st.button("Logout", key="logout_button"):
        logout()

def logout():
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['page'] = "Login"

# 결과 데이터 및 그래프 저장
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

                    # 필요한 컬럼 확인 및 필터링
                    if 'Time on stream (h)' in data.columns and 'DoDH(%)' in data.columns:
                        filtered_data = data[['Time on stream (h)', 'DoDH(%)']].dropna()

                        st.subheader("Uploaded Data Preview")
                        st.write(filtered_data.head())

                        # "Time on stream (h)" 기준으로 1 이상 필터링
                        filtered_data = filtered_data[filtered_data['Time on stream (h)'] >= 1]

                        if filtered_data.empty:
                            st.warning("Filtered data is empty. Please check your input file.")
                        else:
                            filtered_data['DoDH(%)'] = (
                                filtered_data['DoDH(%)']
                                .replace([np.inf, -np.inf], np.nan)
                                .dropna()
                            )
                            average_dodh = filtered_data['DoDH(%)'].mean()
                            st.metric(label="Average DoDH (%)", value=f"{average_dodh:.2f}")

                            # 그래프 생성 및 저장
                            fig, ax = plt.subplots(figsize=(10, 6))
                            ax.plot(
                                filtered_data['Time on stream (h)'].to_numpy(),
                                filtered_data['DoDH(%)'].to_numpy(),
                                marker='o', label="Original DoDH (%)"
                            )
                            ax.set_xlabel("Time on stream (h)")
                            ax.set_ylabel("DoDH (%)")
                            ax.set_title("DoDH (%) vs Time on stream (h)")
                            ax.legend()

                            # 그래프 저장
                            graph_buffer = io.BytesIO()
                            plt.savefig(graph_buffer, format='png')
                            graph_buffer.seek(0)

                            # 결과 테이블에 그래프 저장
                            c.execute(
                                "INSERT INTO results (reaction_id, user_id, graph) VALUES (?, ?, ?)",
                                (reaction_id, user_id, graph_buffer.read())
                            )
                            conn.commit()

                            st.pyplot(fig)

                            # Smoothing 처리 (Savitzky-Golay 필터)
                            smoothed_dodh = savgol_filter(filtered_data['DoDH(%)'].to_numpy(), window_length=11, polyorder=2)

                            # Smoothing 그래프 생성
                            st.subheader("Smoothed DoDH (%) Over Time on Stream (h)")
                            plt.figure(figsize=(10, 6))
                            plt.plot(
                                filtered_data['Time on stream (h)'].to_numpy(),
                                smoothed_dodh,
                                color='orange', label="Smoothed DoDH (%)"
                            )
                            plt.xlabel("Time on stream (h)")
                            plt.ylabel("DoDH (%)")
                            plt.title("Smoothed DoDH (%) vs Time on stream (h)")
                            plt.legend()
                            st.pyplot(plt)

                    else:
                        st.error("Uploaded file must contain 'Time on stream (h)' and 'DoDH(%)' columns.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    print("Error Details:", e)
    else:
        st.error("No reaction data available. Please add reaction data first.")
    conn.close()

# 데이터 보기 및 삭제
def view_data_section():
    st.header("View All Data")
    conn = get_connection()
    c = conn.cursor()

    user_id = st.session_state.get('user_id', None)

    # Synthesis Data
    st.subheader("Synthesis Data")
    c.execute("SELECT id, date, name, memo, amount FROM synthesis WHERE user_id = ?", (user_id,))
    synthesis_data = c.fetchall()

    for row in synthesis_data:
        with st.expander(f"ID: {row[0]} | Date: {row[1]} | Name: {row[2]} | Amount: {row[4]} g"):
            st.write(f"Memo: {row[3]}")
            if st.button(f"Delete Synthesis {row[0]}", key=f"delete_synthesis_{row[0]}"):
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
            logout_button()

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
