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
                    time_series TEXT,
                    dodh_series TEXT,
                    max_dodh REAL,
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
                show_popup("회원가입에 성공하였습니다! 로그인 페이지로 이동하세요.")
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
    c.execute("SELECT id, name FROM synthesis WHERE user_id = ?", (user_id,))
    synthesis_options = c.fetchall()

    if synthesis_options:
        synthesis_id = st.selectbox(
            "Select Synthesis",
            [f"ID: {row[0]} - Name: {row[1]}" for row in synthesis_options]
        )
        selected_synthesis = [row for row in synthesis_options if f"ID: {row[0]}" in synthesis_id][0]

        date = st.date_input("Date")
        temperature = st.number_input("Temperature (°C)", min_value=0.0)
        catalyst_amount = st.number_input("Catalyst Amount (g)", min_value=0.0)
        memo = st.text_area("Memo")

        if st.button("Add Reaction"):
            c.execute("INSERT INTO reaction (user_id, synthesis_id, date, temperature, catalyst_amount, memo) VALUES (?, ?, ?, ?, ?, ?)",
                      (user_id, selected_synthesis[0], str(date), temperature, catalyst_amount, memo))
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
            uploaded_file = st.file_uploader("Upload Result Data (Excel or CSV)", type=["xlsx", "csv"])

            if uploaded_file:
                data = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(".xlsx") else pd.read_csv(uploaded_file)

                st.subheader("Uploaded Data")
                st.write(data.head())

                if 'Time' in data.columns and 'DoDH' in data.columns:
                    plt.figure(figsize=(10, 6))
                    plt.plot(data['Time'], data['DoDH'], marker='o', label="DoDH (%)")
                    plt.xlabel("Time (min)")
                    plt.ylabel("DoDH (%)")
                    plt.title("DoDH over Time")
                    plt.legend()
                    st.pyplot(plt)
                else:
                    st.error("Uploaded file must contain 'Time' and 'DoDH' columns.")
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
        st.write(f"ID: {row[0]}, Date: {row[1]}, Name: {row[2]}, Amount: {row[4]} g")
        if st.button(f"Delete Synthesis {row[0]}"):
            c.execute("DELETE FROM synthesis WHERE id = ?", (row[0],))
            conn.commit()
            st.experimental_rerun()

    # Reaction Data
    st.subheader("Reaction Data")
    c.execute("SELECT id, date, temperature, catalyst_amount, memo FROM reaction WHERE user_id = ?", (user_id,))
    reaction_data = c.fetchall()
    for row in reaction_data:
        st.write(f"ID: {row[0]}, Date: {row[1]}, Temperature: {row[2]}°C, Catalyst Amount: {row[3]} g")
        if st.button(f"Delete Reaction {row[0]}"):
            c.execute("DELETE FROM reaction WHERE id = ?", (row[0],))
            conn.commit()
            st.experimental_rerun()

    conn.close()

# 메인 함수
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
        st.sidebar.title("Navigation")
        section = st.sidebar.radio("Select Section", ["Synthesis", "Reaction", "Results", "View Data", "Logout"])

        st.session_state['page'] = section

        if section == "Synthesis":
            synthesis_section()
        elif section == "Reaction":
            reaction_section()
        elif section == "Results":
            result_section()
        elif section == "View Data":
            view_data_section()
        elif section == "Logout":
            logout()
    else:
        if st.session_state['page'] == "Login":
            login()
        elif st.session_state['page'] == "Sign Up":
            signup()

if __name__ == "__main__":
    main()
