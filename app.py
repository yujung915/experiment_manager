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
                amount REAL,  -- 생성된 촉매의 양
                FOREIGN KEY (user_id) REFERENCES users (id)
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS reaction (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                synthesis_id INTEGER,
                date TEXT,
                temperature REAL,
                pressure REAL,
                catalyst_amount REAL,  -- 반응에 사용된 촉매 양
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

# 결과 섹션
def result_section():
    st.header("Result Analysis")

    # Reaction 데이터 가져오기
    user_id = st.session_state['user_id']
    c.execute("SELECT reaction.id, reaction.date, reaction.temperature, reaction.pressure, reaction.catalyst_amount, synthesis.name "
              "FROM reaction JOIN synthesis ON reaction.synthesis_id = synthesis.id "
              "WHERE reaction.user_id = ?", (user_id,))
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

                # 데이터 검증 및 그래프 생성
                if 'Time' in data.columns and 'DoDH' in data.columns:
                    plt.figure(figsize=(10, 6))
                    plt.plot(data['Time'], data['DoDH'], marker='o', label="DoDH (%)")
                    plt.xlabel("Time (min)")
                    plt.ylabel("DoDH (%)")
                    plt.title("DoDH over Time")
                    plt.legend()
                    st.pyplot(plt)

                    # 최대 DoDH 계산 및 저장
                    max_dodh = data['DoDH'].max()
                    reaction_id_num = int(reaction_id.split("ID: ")[-1].split(" - ")[0])
                    c.execute("INSERT INTO results (reaction_id, user_id, time_series, dodh_series, max_dodh) VALUES (?, ?, ?, ?, ?)",
                              (reaction_id_num, user_id, data['Time'].to_json(), data['DoDH'].to_json(), max_dodh))
                    conn.commit()
                    st.metric("Max DoDH (%)", f"{max_dodh:.2f}")
                else:
                    st.error("Uploaded file must contain 'Time' and 'DoDH' columns.")
    else:
        st.write("No reaction data available. Please add reaction data first.")

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
