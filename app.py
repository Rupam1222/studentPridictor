import streamlit as st
import pickle
import pandas as pd
import sqlite3

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Student Performance App", layout="wide")

# =====================================================
# DATABASE (SQLite)
# =====================================================
def get_connection():
    return sqlite3.connect("student_predictions.db", check_same_thread=False)

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            gender TEXT,
            race_ethnicity TEXT,
            parental_education TEXT,
            lunch TEXT,
            test_prep TEXT,
            reading_input INTEGER,
            writing_input INTEGER,
            predicted_math REAL,
            predicted_reading REAL,
            predicted_writing REAL,
            overall_average REAL
        )
    """)

    conn.commit()
    conn.close()

create_tables()

# =====================================================
# SESSION STATE
# =====================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"

# =====================================================
# LOGIN
# =====================================================
def login_page():
    st.title("🔐 Login")

    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        btn = st.form_submit_button("Login")

    if btn:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = cur.fetchone()
        conn.close()

        if user:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid credentials")

    if st.button("Create new account"):
        st.session_state.auth_page = "register"
        st.rerun()

# =====================================================
# REGISTER
# =====================================================
def register_page():
    st.title("📝 Register")

    with st.form("register"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        btn = st.form_submit_button("Register")

    if btn:
        if password != confirm:
            st.error("Passwords do not match")
            return

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
            st.success("Account created. Please login.")
            st.session_state.auth_page = "login"
            st.rerun()
        except:
            st.error("Username already exists")
        finally:
            conn.close()

    if st.button("Back to Login"):
        st.session_state.auth_page = "login"
        st.rerun()

# =====================================================
# LOGOUT
# =====================================================
def logout():
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.auth_page = "login"
    st.rerun()

# =====================================================
# LOAD MODEL
# =====================================================
@st.cache_resource
def load_model():
    with open("model.pkl", "rb") as f:
        return pickle.load(f)

@st.cache_resource
def load_preprocessor():
    with open("preprocessor.pkl", "rb") as f:
        return pickle.load(f)

model = load_model()
preprocessor = load_preprocessor()

# =====================================================
# AUTH CONTROLLER
# =====================================================
if not st.session_state.authenticated:
    if st.session_state.auth_page == "login":
        login_page()
    else:
        register_page()
    st.stop()

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.success(f"Logged in as: {st.session_state.username}")
page = st.sidebar.radio("Navigate", ["Predictor", "Dashboard", "Database"])
st.sidebar.button("Logout", on_click=logout)

# =====================================================
# PREDICTOR
# =====================================================
if page == "Predictor":

    st.title("🎯 Student Score Predictor")

    with st.form("predict"):
        gender = st.selectbox("Gender", ["female", "male"])
        race = st.selectbox("Race/Ethnicity", ["group A","group B","group C","group D","group E"])
        parent = st.selectbox("Parental Education", [
            "bachelor's degree","some college","master's degree",
            "associate's degree","high school","some high school"
        ])
        lunch = st.selectbox("Lunch Type", ["standard","free/reduced"])
        prep = st.selectbox("Test Preparation", ["none","completed"])
        read = st.number_input("Reading Score", 0, 100, 70)
        write = st.number_input("Writing Score", 0, 100, 70)
        btn = st.form_submit_button("Predict")

    if btn:
        df = pd.DataFrame({
            "gender":[gender],
            "race_ethnicity":[race],
            "parental_level_of_education":[parent],
            "lunch":[lunch],
            "test_preparation_course":[prep],
            "reading_score":[read],
            "writing_score":[write]
        })

        df["total score"] = read + write
        df["average"] = (read + write) / 2
        df["Unnamed: 0"] = 0

        scaled = preprocessor.transform(df)
        math = max(0, min(100, model.predict(scaled)[0]))
        reading = min(100, read + 2)
        writing = min(100, write + 2)
        overall = round((math + reading + writing) / 3, 2)

        st.success("Predicted Scores")
        st.metric("Math", f"{math:.2f}")
        st.metric("Reading", f"{reading:.2f}")
        st.metric("Writing", f"{writing:.2f}")
        st.info(f"Overall Average: {overall}")

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO predictions (
                username, gender, race_ethnicity, parental_education,
                lunch, test_prep, reading_input, writing_input,
                predicted_math, predicted_reading, predicted_writing, overall_average
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            st.session_state.username, gender, race, parent,
            lunch, prep, read, write,
            math, reading, writing, overall
        ))
        conn.commit()
        conn.close()

# =====================================================
# DASHBOARD
# =====================================================
elif page == "Dashboard":

    st.title("📊 Dashboard")

    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM predictions WHERE username=?",
        conn,
        params=(st.session_state.username,)
    )
    conn.close()

    if df.empty:
        st.info("No predictions yet")
        st.stop()

    st.metric("Total Predictions", len(df))
    st.line_chart(df["predicted_math"])
    st.bar_chart(df[["predicted_math","predicted_reading","predicted_writing"]])

# =====================================================
# DATABASE
# =====================================================
elif page == "Database":

    st.title("🗄️ Prediction Records")

    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM predictions WHERE username=?",
        conn,
        params=(st.session_state.username,)
    )
    conn.close()

    st.dataframe(df)
