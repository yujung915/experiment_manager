import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

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

c.execute('''CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reaction_id INTEGER,
                user_id INTEGER,
                time_series TEXT,  -- 시간 데이터를 저장 (JSON 형식)
                dodh_series TEXT,  -- DoDH 데이터를 저장 (JSON 형식)
                max_dodh REAL,     -- 최대 DoDH
                FOREIGN KEY (reaction_id) REFERENCES reaction (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )''')

conn.commit()

# 결과 데이터 업로드 및 해석
def result_section():
    st.header("Result Analysis")

    # Reaction 데이터 가져오기
    user_id = st.session_state['user_id']
    c.execute("SELECT id, date, temperature FROM reaction WHERE user_id = ?", (user_id,))
    reaction_options = c.fetchall()
    reaction_id = st.selectbox(
        "Select Reaction (ID + Date + Temperature)",
        [f"ID: {row[0]} - {row[1]} - {row[2]}°C" for row in reaction_options]
    )

    # 엑셀 파일 업로드
    uploaded_file = st.file_uploader("Upload Result Data (Excel or CSV)", type=["xlsx", "csv"])

    if uploaded_file:
        # 데이터 읽기
        if uploaded_file.name.endswith(".xlsx"):
            data = pd.read_excel(uploaded_file)
        else:
            data = pd.read_csv(uploaded_file)

        st.subheader("Uploaded Data")
        st.write(data.head())

        # 그래프 생성
        st.subheader("DoDH Analysis")
        if 'Time' in data.columns and 'DoDH' in data.columns:
            # 데이터 시각화
            plt.figure(figsize=(10, 6))
            plt.plot(data['Time'], data['DoDH'], marker='o', label="DoDH (%)")
            plt.xlabel("Time (min)")
            plt.ylabel("DoDH (%)")
            plt.title("DoDH over Time")
            plt.legend()
            st.pyplot(plt)

            # 최대 DoDH 계산
            max_dodh = data['DoDH'].max()
            st.metric("Max DoDH (%)", f"{max_dodh:.2f}")

            # 데이터 저장
            reaction_id_num = int(reaction_id.split("ID: ")[-1].split(" - ")[0])
            c.execute("INSERT INTO results (reaction_id, user_id, time_series, dodh_series, max_dodh) VALUES (?, ?, ?, ?, ?)",
                      (reaction_id_num, user_id, data['Time'].to_json(), data['DoDH'].to_json(), max_dodh))
            conn.commit()
            st.success("Result data saved successfully!")
        else:
            st.error("Uploaded file must contain 'Time' and 'DoDH' columns.")

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
    section = st.sidebar.radio("Select Section", ["Synthesis", "Reaction", "Results"])
    if section == "Synthesis":
        synthesis_section()
    elif section == "Reaction":
        reaction_section()
    elif section == "Results":
        result_section()

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
