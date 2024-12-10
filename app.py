import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from hashlib import sha256

# 데이터베이스 연결
def get_connection():
    return sqlite3.connect("experiment_manager.db", check_same_thread=False)

# 비밀번호 해싱 함수
def hash_password(password):
    return sha256(password.encode()).hexdigest()

# 데이터베이스 초기화
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

# 결과 섹션
def result_section():
    try:
        st.header("Result Analysis")
        conn = get_connection()
        c = conn.cursor()

        user_id = st.session_state.get('user_id', None)
        c.execute("""SELECT reaction.id, reaction.date, reaction.temperature, reaction.pressure, 
                            reaction.catalyst_amount, synthesis.name
                     FROM reaction
                     JOIN synthesis ON reaction.synthesis_id = synthesis.id
                     WHERE reaction.user_id = ?""", (user_id,))
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
        conn.close()
    except Exception as e:
        st.error(f"An error occurred: {e}")

# 비밀번호 변경 섹션
def change_password():
    st.header("Change Password")

    user_id = st.session_state.get('user_id', None)
    if not user_id:
        st.error("You must be logged in to change your password.")
        return

    current_password = st.text_input("Current Password", type="password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")

    if st.button("Change Password"):
        if not current_password or not new_password or not confirm_password:
            st.error("All fields are required.")
            return

        if new_password != confirm_password:
            st.error("New passwords do not match.")
            return

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()

        if not user or user[0] != hash_password(current_password):
            st.error("Current password is incorrect.")
            return

        c.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(new_password), user_id))
        conn.commit()
        conn.close()
        st.success("Password changed successfully!")

# 메인 함수
def main():
    initialize_database()

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None

    if st.session_state['logged_in']:
        st.sidebar.title("Navigation")
        section = st.sidebar.radio("Select Section", ["Synthesis", "Reaction", "Results", "Change Password"])

        if section == "Results":
            result_section()
        elif section == "Change Password":
            change_password()

        st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"logged_in": False, "user_id": None}))
    else:
        page = st.sidebar.radio("Choose an option", ["Login", "Sign Up"])
        if page == "Login":
            login()
        elif page == "Sign Up":
            signup()

if __name__ == "__main__":
    main()
