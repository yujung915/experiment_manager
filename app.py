import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter
from hashlib import sha256
from io import BytesIO

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

# 데이터베이스 초기화 및 업데이트 함수
def initialize_database():
    conn = get_connection()
    c = conn.cursor()

    # 테이블 생성
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

    # `results` 테이블 업데이트
    c.execute('''CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reaction_id INTEGER,
                    user_id INTEGER,
                    graph BLOB,
                    average_dodh REAL,
                    FOREIGN KEY (reaction_id) REFERENCES reaction (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )''')

    conn.commit()
    conn.close()

# 비밀번호 해싱 함수
def hash_password(password):
    return sha256(password.encode()).hexdigest()

# 팝업 메시지 함수
def show_popup(message):
    st.session_state['popup_message'] = message

def display_popup():
    if 'popup_message' in st.session_state and st.session_state['popup_message']:
        st.info(st.session_state['popup_message'])
        if st.button("확인"):
            st.session_state['popup_message'] = ""

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

# 결과 데이터 저장 함수
def save_result_to_db(reaction_id, user_id, graph, average_dodh):
    conn = get_connection()
    c = conn.cursor()

    buffer = BytesIO()
    graph.savefig(buffer, format='png')
    buffer.seek(0)
    graph_data = buffer.read()

    c.execute('''INSERT OR REPLACE INTO results (reaction_id, user_id, graph, average_dodh)
                 VALUES (?, ?, ?, ?)''', (reaction_id, user_id, graph_data, average_dodh))
    conn.commit()
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
                        filtered_data = filtered_data[filtered_data['Time on stream (h)'] >= 1]

                        if not filtered_data.empty:
                            time_stream = filtered_data['Time on stream (h)'].to_numpy()
                            dodh = filtered_data['DoDH(%)'].to_numpy()

                            smoothed_dodh = savgol_filter(dodh, window_length=51, polyorder=2)
                            average_dodh = np.mean(dodh)
                            st.metric(label="Average DoDH (%)", value=f"{average_dodh:.2f}")

                            fig, ax = plt.subplots()
                            ax.plot(time_stream, smoothed_dodh, label="Smoothed DoDH (%)")
                            ax.set_title("DoDH (%) Over Time on Stream")
                            ax.set_xlabel("Time on stream (h)")
                            ax.set_ylabel("DoDH (%)")
                            ax.legend()
                            st.pyplot(fig)

                            save_result_to_db(reaction_id, user_id, fig, average_dodh)
                            st.success("Results saved!")
                    else:
                        st.error("The file must contain 'Time on stream (h)' and 'DoDH(%)' columns.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
    else:
        st.error("No reaction data available. Please add reaction data first.")
    conn.close()

# 데이터 보기 및 결과 확인
def view_data_section():
    st.header("View All Data")
    conn = get_connection()
    c = conn.cursor()

    user_id = st.session_state.get('user_id', None)
    c.execute("SELECT reaction.id, reaction.date, reaction.temperature, reaction.catalyst_amount, synthesis.name FROM reaction JOIN synthesis ON reaction.synthesis_id = synthesis.id WHERE reaction.user_id = ?", (user_id,))
    reaction_data = c.fetchall()

    for row in reaction_data:
        with st.expander(f"Reaction ID: {row[0]} | Date: {row[1]} | Catalyst: {row[4]}"):
            st.write(f"Temperature: {row[2]}°C, Catalyst Amount: {row[3]} g")

            # Fetch results for this reaction
            c.execute("SELECT average_dodh, graph FROM results WHERE reaction_id = ?", (row[0],))
            result = c.fetchone()

            if result:
                st.write(f"Average DoDH: {result[0]:.2f}%")
                if result[1]:
                    st.image(result[1], caption="DoDH (%) Graph", use_column_width=True)
            else:
                st.warning("No results available for this reaction.")

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
