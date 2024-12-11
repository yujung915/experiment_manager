import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter
from hashlib import sha256

# NumPy 2.0 이상 호환
np.Inf = np.inf

# 상징 색깔
CRIMSON_RED = "#A33B39"

# 초기 세션 상태 설정
def initialize_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None
    if 'page' not in st.session_state:
        st.session_state['page'] = "Login"

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
                    excel_data BLOB,
                    average_dodh REAL,
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

# 로그아웃 버튼 상단에 추가
def render_logout():
    if st.session_state.get('logged_in', False):  # 기본값 False
        st.markdown(
            f'<a style="color:white;background-color:#A33B39;padding:10px 20px;text-decoration:none;border-radius:5px;display:inline-block;" href="/" onclick="window.location.reload();">Logout</a>',
            unsafe_allow_html=True
        )

# 합성 데이터 입력 섹션
def synthesis_section():
    st.header("Synthesis Section")
    conn = get_connection()
    c = conn.cursor()

    user_id = st.session_state.get('user_id', None)
    date = st.date_input("Date")
    name = st.text_input("Catalyst Name")
    memo = st.text_area("Memo")
    amount = st.number_input("Amount (g)", min_value=0.0)

    if st.button("Add Synthesis"):
        if user_id and name:
            c.execute("INSERT INTO synthesis (user_id, date, name, memo, amount) VALUES (?, ?, ?, ?, ?)",
                      (user_id, str(date), name, memo, amount))
            conn.commit()
            st.success("Synthesis added!")
        else:
            st.error("모든 필드를 채워주세요.")
    conn.close()

# 반응 데이터 입력 섹션
def reaction_section():
    st.header("Reaction Section")
    conn = get_connection()
    c = conn.cursor()

    user_id = st.session_state.get('user_id', None)
    c.execute("SELECT id, date, name FROM synthesis WHERE user_id = ?", (user_id,))
    synthesis_options = c.fetchall()

    if synthesis_options:
        synthesis_id = st.selectbox(
            "Select Synthesis",
            [f"ID: {row[0]} - Date: {row[1]} - Name: {row[2]}" for row in synthesis_options]
        )

        selected_id = int(synthesis_id.split(" ")[1])  # Extract synthesis ID

        date = st.date_input("Date")
        temperature = st.number_input("Temperature (°C)", min_value=0.0)
        catalyst_amount = st.number_input("Catalyst Amount (g)", min_value=0.0)
        memo = st.text_area("Memo")

        if st.button("Add Reaction"):
            c.execute("INSERT INTO reaction (user_id, synthesis_id, date, temperature, catalyst_amount, memo) VALUES (?, ?, ?, ?, ?, ?)",
                      (user_id, selected_id, str(date), temperature, catalyst_amount, memo))
            conn.commit()
            st.success("Reaction added!")
    else:
        st.error("No synthesis data available. Please add synthesis data first.")
    conn.close()

# 결과 데이터 및 시각화
def result_section():
    st.header("Result Section")
    conn = get_connection()
    c = conn.cursor()

    user_id = st.session_state.get('user_id', None)
    c.execute("SELECT reaction.id, reaction.date, reaction.temperature, reaction.catalyst_amount, synthesis.name FROM reaction JOIN synthesis ON reaction.synthesis_id = synthesis.id WHERE reaction.user_id = ?", (user_id,))
    reaction_options = c.fetchall()

    if reaction_options:
        reaction_id = st.selectbox(
            "Select Reaction",
            [f"ID: {row[0]} - Date: {row[1]} - Temp: {row[2]}°C - Catalyst: {row[4]}" for row in reaction_options]
        )

        if reaction_id:
            reaction_id = int(reaction_id.split(" ")[1])  # Extract reaction ID
            uploaded_file = st.file_uploader("Upload Result Data (Excel)", type=["xlsx"])

            if uploaded_file:
                try:
                    data = pd.read_excel(uploaded_file, engine="openpyxl")
                    if 'Time on stream (h)' in data.columns and 'DoDH(%)' in data.columns:
                        filtered_data = data[['Time on stream (h)', 'DoDH(%)']].dropna()
                        filtered_data['Time on stream (h)'] = filtered_data['Time on stream (h)'].to_numpy()
                        filtered_data['DoDH(%)'] = filtered_data['DoDH(%)'].to_numpy()
                        filtered_data = filtered_data[filtered_data['Time on stream (h)'] >= 1]

                        if not filtered_data.empty:
                            average_dodh = filtered_data['DoDH(%)'].mean()
                            st.metric(label="Average DoDH (%)", value=f"{average_dodh:.2f}")

                            fig, ax = plt.subplots()
                            ax.plot(filtered_data['Time on stream (h)'], filtered_data['DoDH(%)'], label="Original DoDH (%)")
                            ax.set_title("DoDH (%) Over Time")
                            st.pyplot(fig)

                            conn.close()
                    else:
                        st.error("The file must contain 'Time on stream (h)' and 'DoDH(%)' columns.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
    else:
        st.error("No reaction data available. Please add reaction data first.")
    conn.close()

# 데이터 보기 및 수정/삭제
def view_data_section():
    st.header("View All Data")
    conn = get_connection()
    c = conn.cursor()

    user_id = st.session_state.get('user_id', None)
    c.execute("SELECT id, date, name FROM synthesis WHERE user_id = ?", (user_id,))
    synthesis_data = c.fetchall()

    st.subheader("Synthesis Data")
    for row in synthesis_data:
        with st.expander(f"ID: {row[0]} - {row[2]} ({row[1]})"):
            st.write(f"ID: {row[0]}, Name: {row[2]}, Date: {row[1]}")
            if st.button(f"Delete Synthesis {row[0]}", key=f"delete_synthesis_{row[0]}"):
                c.execute("DELETE FROM synthesis WHERE id = ?", (row[0],))
                conn.commit()
                st.success(f"Synthesis ID {row[0]} deleted.")
                st.experimental_rerun()

    st.subheader("Reaction Data")
    c.execute("SELECT reaction.id, reaction.date, reaction.temperature, reaction.catalyst_amount, synthesis.name FROM reaction JOIN synthesis ON reaction.synthesis_id = synthesis.id WHERE reaction.user_id = ?", (user_id,))
    reaction_data = c.fetchall()

    for row in reaction_data:
        with st.expander(f"ID: {row[0]} - Catalyst: {row[4]} ({row[1]})"):
            st.write(f"Temperature: {row[2]}°C, Catalyst Amount: {row[3]} g")
            if st.button(f"Delete Reaction {row[0]}", key=f"delete_reaction_{row[0]}"):
                c.execute("DELETE FROM reaction WHERE id = ?", (row[0],))
                conn.commit()
                st.success(f"Reaction ID {row[0]} deleted.")
                st.experimental_rerun()

    conn.close()

# 메인 함수
def main():
    initialize_session_state()
    initialize_database()
    render_logout()
    display_popup()

    if st.session_state['logged_in']:
        st.sidebar.title("Navigation")
        section = st.sidebar.radio(
            "",
            ["Synthesis", "Reaction", "Results", "View Data"],
        )
        st.session_state['page'] = section

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
