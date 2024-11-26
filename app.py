import streamlit as st
import sqlite3
import hashlib

# 데이터베이스 연결
conn = sqlite3.connect("experiment_manager.db")
c = conn.cursor()

# 데이터베이스 초기화 (테이블 생성)
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

c.execute('''CREATE TABLE IF NOT EXISTS calcination (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                synthesis_id INTEGER,
                date TEXT,
                name TEXT,
                memo TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (synthesis_id) REFERENCES synthesis (id)
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS experiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                calcination_id INTEGER,
                date TEXT,
                temperature REAL,
                lshv REAL,
                memo TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (calcination_id) REFERENCES calcination (id)
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
            st.session_state['logged_in'] = True  # 로그인 상태 설정
            st.session_state['user_id'] = user[0]  # 사용자 ID 저장
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

# 로그아웃 기능
def logout():
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.success("Logged out successfully!")

# Synthesis 섹션
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

    # Synthesis 데이터 보기
    st.header("View Synthesis Data")
    user_id = st.session_state['user_id']
    c.execute("SELECT * FROM synthesis WHERE user_id = ?", (user_id,))
    synthesis_data = c.fetchall()
    if synthesis_data:
        for row in synthesis_data:
            st.write(f"ID: {row[0]}, Date: {row[2]}, Name: {row[3]}, Memo: {row[4]}")
    else:
        st.write("No synthesis data available.")

# Calcination 섹션
def calcination_section():
    st.header("Calcination Data Input")

    # Synthesis 데이터 가져오기
    user_id = st.session_state['user_id']
    c.execute("SELECT id, date, name FROM synthesis WHERE user_id = ?", (user_id,))
    synthesis_options = c.fetchall()
    synthesis_id = st.selectbox(
        "Select Synthesis (ID + Date + Catalyst Name)",
        [f"ID: {row[0]} - {row[1]} - {row[2]}" for row in synthesis_options]
    )

    calcination_date = st.date_input("Calcination Date")
    calcination_memo = st.text_area("Memo (Optional)")

    if st.button("Add Calcination Data"):
        selected_synthesis_id = int(synthesis_id.split("ID: ")[-1].split(" - ")[0])  # ID만 추출
        c.execute("INSERT INTO calcination (user_id, synthesis_id, date, name, memo) VALUES (?, ?, ?, ?, ?)",
                  (user_id, selected_synthesis_id, str(calcination_date), synthesis_id.split(" - ")[2], calcination_memo))
        conn.commit()
        st.success("Calcination data added successfully!")

    # Calcination 데이터 보기
    st.header("View Calcination Data")
    c.execute('''SELECT calcination.id, calcination.date, calcination.name, calcination.memo, synthesis.id AS synthesis_id, synthesis.date AS synthesis_date, synthesis.name AS synthesis_name
                 FROM calcination
                 JOIN synthesis ON calcination.synthesis_id = synthesis.id
                 WHERE calcination.user_id = ?''', (user_id,))
    calcination_data = c.fetchall()
    if calcination_data:
        for row in calcination_data:
            st.write(f"ID: {row[0]}, Calcination Date: {row[1]}, Name: {row[2]}, Memo: {row[3]}, Linked Synthesis: [ID: {row[4]}, Date: {row[5]}, Name: {row[6]}]")
    else:
        st.write("No calcination data available.")

# Experiment 섹션
def experiment_section():
    st.header("Experiment Data Input")

    # Calcination 데이터 가져오기
    user_id = st.session_state['user_id']
    c.execute("SELECT id, date, name FROM calcination WHERE user_id = ?", (user_id,))
    calcination_options = c.fetchall()
    calcination_id = st.selectbox(
        "Select Calcination (ID + Date + Catalyst Name)",
        [f"ID: {row[0]} - {row[1]} - {row[2]}" for row in calcination_options]
    )

    experiment_date = st.date_input("Experiment Date")
    experiment_temperature = st.number_input("Reaction Temperature (°C)", step=0.1)
    experiment_lshv = st.number_input("LHSV (h⁻¹)", step=0.1)
    experiment_memo = st.text_area("Memo (Optional)")

    if st.button("Add Experiment Data"):
        selected_calcination_id = int(calcination_id.split("ID: ")[-1].split(" - ")[0])  # ID만 추출
        c.execute("INSERT INTO experiment (user_id, calcination_id, date, temperature, lshv, memo) VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, selected_calcination_id, str(experiment_date), experiment_temperature, experiment_lshv, experiment_memo))
        conn.commit()
        st.success("Experiment data added successfully!")

    # Experiment 데이터 보기
    st.header("View Experiment Data")
    c.execute('''SELECT experiment.id, experiment.date, experiment.temperature, experiment.lshv, experiment.memo, calcination.id AS calcination_id, calcination.date AS calcination_date, calcination.name AS calcination_name
                 FROM experiment
                 JOIN calcination ON experiment.calcination_id = calcination.id
                 WHERE experiment.user_id = ?''', (user_id,))
    experiment_data = c.fetchall()
    if experiment_data:
        for row in experiment_data:
            st.write(f"ID: {row[0]}, Experiment Date: {row[1]}, Temperature: {row[2]}°C, LHSV: {row[3]} h⁻¹, Memo: {row[4]}, Linked Calcination: [ID: {row[5]}, Date: {row[6]}, Name: {row[7]}]")
    else:
        st.write("No experiment data available.")

# 애플리케이션 상태 관리
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None

# 메인 애플리케이션
if st.session_state['logged_in']:
    st.sidebar.title("Navigation")
    section = st.sidebar.radio("Select Section", ["Synthesis", "Calcination", "Experiment", "Logout"])
    if section == "Synthesis":
        synthesis_section()
    elif section == "Calcination":
        calcination_section()
    elif section == "Experiment":
        experiment_section()
    elif section == "Logout":
        logout()
else:
    st.sidebar.title("Authentication")
    page = st.sidebar.radio("Choose an option", ["Login", "Sign Up"])
    if page == "Login":
        login()
    elif page == "Sign Up":
        signup()
