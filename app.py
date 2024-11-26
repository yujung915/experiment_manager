import streamlit as st
import sqlite3

# 데이터베이스 연결
conn = sqlite3.connect("experiments.db")
c = conn.cursor()

# 데이터베이스 초기화 (테이블 생성)
c.execute('''CREATE TABLE IF NOT EXISTS synthesis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                name TEXT,
                memo TEXT
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS calcination (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                synthesis_id INTEGER,
                date TEXT,
                name TEXT,
                memo TEXT,
                FOREIGN KEY (synthesis_id) REFERENCES synthesis (id)
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS experiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calcination_id INTEGER,
                date TEXT,
                temperature REAL,
                lshv REAL,
                memo TEXT,
                FOREIGN KEY (calcination_id) REFERENCES calcination (id)
            )''')

# 사이드바 메뉴
st.sidebar.title("Experiment Sections")
section = st.sidebar.radio("Select Section", ["Synthesis", "Calcination", "Experiment", "View All Data"])

# 합성 섹션
if section == "Synthesis":
    st.header("Synthesis Data Input")
    synthesis_date = st.date_input("Synthesis Date")
    synthesis_name = st.text_input("Catalyst Name")
    synthesis_memo = st.text_area("Memo (Optional)")

    if st.button("Add Synthesis Data"):
        c.execute("INSERT INTO synthesis (date, name, memo) VALUES (?, ?, ?)", (str(synthesis_date), synthesis_name, synthesis_memo))
        conn.commit()
        st.success("Synthesis data added successfully!")

    # 합성 데이터 보기 및 삭제
    st.header("View and Delete Synthesis Data")
    c.execute("SELECT * FROM synthesis")
    synthesis_data = c.fetchall()
    if synthesis_data:
        for row in synthesis_data:
            col1, col2 = st.columns([4, 1])  # 컬럼 분할: 데이터(4) / 삭제 버튼(1)
            with col1:
                st.write(f"ID: {row[0]}, Date: {row[1]}, Name: {row[2]}, Memo: {row[3]}")
            with col2:
                if st.button("🗑️", key=f"delete_synthesis_{row[0]}"):
                    c.execute("DELETE FROM synthesis WHERE id = ?", (row[0],))
                    conn.commit()
                    st.success(f"Synthesis ID {row[0]} deleted!")
    else:
        st.write("No synthesis data available.")

# 소성 섹션
elif section == "Calcination":
    st.header("Calcination Data Input")

    # 합성 데이터 가져오기
    c.execute("SELECT id, date, name FROM synthesis")
    synthesis_options = c.fetchall()
    synthesis_id = st.selectbox(
        "Select Synthesis (ID + Date + Catalyst Name)",
        [f"ID: {row[0]} - {row[1]} - {row[2]}" for row in synthesis_options]
    )

    calcination_date = st.date_input("Calcination Date")
    calcination_memo = st.text_area("Memo (Optional)")

    if st.button("Add Calcination Data"):
        selected_synthesis_id = int(synthesis_id.split("ID: ")[-1].split(" - ")[0])  # ID만 추출
        c.execute("INSERT INTO calcination (synthesis_id, date, name, memo) VALUES (?, ?, ?, ?)",
                  (selected_synthesis_id, str(calcination_date), synthesis_id.split(" - ")[2], calcination_memo))
        conn.commit()
        st.success("Calcination data added successfully!")

    # 소성 데이터 보기 및 삭제
    st.header("View and Delete Calcination Data")
    c.execute('''SELECT calcination.id, calcination.date, calcination.name, calcination.memo, synthesis.id AS synthesis_id, synthesis.date AS synthesis_date, synthesis.name AS synthesis_name
                 FROM calcination
                 JOIN synthesis ON calcination.synthesis_id = synthesis.id''')
    calcination_data = c.fetchall()
    if calcination_data:
        for row in calcination_data:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"ID: {row[0]}, Calcination Date: {row[1]}, Name: {row[2]}, Memo: {row[3]}, Linked Synthesis: [ID: {row[4]}, Date: {row[5]}, Name: {row[6]}]")
            with col2:
                if st.button("🗑️", key=f"delete_calcination_{row[0]}"):
                    c.execute("DELETE FROM calcination WHERE id = ?", (row[0],))
                    conn.commit()
                    st.success(f"Calcination ID {row[0]} deleted!")
    else:
        st.write("No calcination data available.")

# 실험 섹션
elif section == "Experiment":
    st.header("Experiment Data Input")

    # 소성 데이터 가져오기
    c.execute("SELECT id, date, name FROM calcination")
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
        c.execute("INSERT INTO experiment (calcination_id, date, temperature, lshv, memo) VALUES (?, ?, ?, ?, ?)",
                  (selected_calcination_id, str(experiment_date), experiment_temperature, experiment_lshv, experiment_memo))
        conn.commit()
        st.success("Experiment data added successfully!")

    # 실험 데이터 보기 및 삭제
    st.header("View and Delete Experiment Data")
    c.execute('''SELECT experiment.id, experiment.date, experiment.temperature, experiment.lshv, experiment.memo, calcination.id AS calcination_id, calcination.date AS calcination_date, calcination.name AS calcination_name
                 FROM experiment
                 JOIN calcination ON experiment.calcination_id = calcination.id''')
    experiment_data = c.fetchall()
    if experiment_data:
        for row in experiment_data:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"ID: {row[0]}, Experiment Date: {row[1]}, Temperature: {row[2]}°C, LHSV: {row[3]} h⁻¹, Memo: {row[4]}, Linked Calcination: [ID: {row[5]}, Date: {row[6]}, Name: {row[7]}]")
            with col2:
                if st.button("🗑️", key=f"delete_experiment_{row[0]}"):
                    c.execute("DELETE FROM experiment WHERE id = ?", (row[0],))
                    conn.commit()
                    st.success(f"Experiment ID {row[0]} deleted!")
    else:
        st.write("No experiment data available.")

# 모든 데이터 보기
elif section == "View All Data":
    st.header("View All Data")

    st.subheader("Synthesis Data")
    c.execute("SELECT id, date, name, memo FROM synthesis")
    synthesis_all = c.fetchall()
    for row in synthesis_all:
        st.write(f"ID: {row[0]}, Date: {row[1]}, Name: {row[2]}, Memo: {row[3]}")

    st.subheader("Calcination Data")
    c.execute('''SELECT calcination.id, calcination.date, calcination.name, calcination.memo, synthesis.id AS synthesis_id, synthesis.date AS synthesis_date, synthesis.name AS synthesis_name
                 FROM calcination
                 JOIN synthesis ON calcination.synthesis_id = synthesis.id''')
    calcination_all = c.fetchall()
    for row in calcination_all:
        st.write(f"ID: {row[0]}, Calcination Date: {row[1]}, Name: {row[2]}, Memo: {row[3]}, Linked Synthesis: [ID: {row[4]}, Date: {row[5]}, Name: {row[6]}]")

    st.subheader("Experiment Data")
    c.execute('''SELECT experiment.id, experiment.date, experiment.temperature, experiment.lshv, experiment.memo, calcination.id AS calcination_id, calcination.date AS calcination_date, calcination.name AS calcination_name
                 FROM experiment
                 JOIN calcination ON experiment.calcination_id = calcination.id''')
    experiment_all = c.fetchall()
    for row in experiment_all:
        st.write(f"ID: {row[0]}, Experiment Date: {row[1]}, Temperature: {row[2]}°C, LHSV: {row[3]} h⁻¹, Memo: {row[4]}, Linked Calcination: [ID: {row[5]}, Date: {row[6]}, Name: {row[7]}]")
