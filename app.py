import streamlit as st
import pickle
import pandas as pd
import sqlite3

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Student Performance App", layout="wide")
DB_NAME = "student_predictions.db"

# =====================================================
# DATABASE HELPERS
# =====================================================
def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def get_columns(table):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    conn.close()
    return cols

def create_and_migrate_tables():
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
            writing_input INTEGER
        )
    """)

    existing_cols = get_columns("predictions")
    new_columns = {
        "math": "REAL",
        "science": "REAL",
        "computer": "REAL",
        "english": "REAL",
        "overall_average": "REAL"
    }

    for col, dtype in new_columns.items():
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE predictions ADD COLUMN {col} {dtype}")

    conn.commit()
    conn.close()

create_and_migrate_tables()

# =====================================================
# BACKFILL MISSING PREDICTIONS
# =====================================================
def fill_missing_predictions(df):
    for idx, row in df.iterrows():
        if pd.isna(row["math"]):
            math = round((row["reading_input"] + row["writing_input"]) / 2 * 0.5, 2)
            science = round((math + row["reading_input"]) / 2 + 2, 2)
            computer = round((math + row["writing_input"]) / 2 + 2, 2)
            english = round((row["reading_input"] + row["writing_input"]) / 2 + 1, 2)
            overall = round((math + science + computer + english) / 4, 2)

            df.loc[idx, ["math","science","computer","english","overall_average"]] = [
                math, science, computer, english, overall
            ]
    return df

# =====================================================
# SESSION STATE
# =====================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =====================================================
# AUTH PAGES
# =====================================================
def login_page():
    st.title("🔐 Login")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        btn = st.form_submit_button("Login")

    if btn:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
        if cur.fetchone():
            st.session_state.authenticated = True
            st.session_state.username = u
            st.rerun()
        else:
            st.error("Invalid credentials")
        conn.close()

    if st.button("Create new account"):
        st.session_state.auth_page = "register"
        st.rerun()

def register_page():
    st.title("📝 Register")
    with st.form("register"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        c = st.text_input("Confirm Password", type="password")
        btn = st.form_submit_button("Register")

    if btn:
        if p != c:
            st.error("Passwords do not match")
            return
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users VALUES (?,?)", (u, p))
            conn.commit()
            st.success("Account created. Please login.")
            st.session_state.auth_page = "login"
            st.rerun()
        except:
            st.error("Username already exists")
        conn.close()

    if st.button("Back to Login"):
        st.session_state.auth_page = "login"
        st.rerun()

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
    with open("model.pkl","rb") as f:
        return pickle.load(f)

@st.cache_resource
def load_preprocessor():
    with open("preprocessor.pkl","rb") as f:
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
page = st.sidebar.radio("Navigate", ["Predictor","Dashboard","Database","Chatbot"])
st.sidebar.button("Logout", on_click=logout)

# =====================================================
# PREDICTOR
# =====================================================
if page == "Predictor":
    st.title("🎯 Multi-Subject Score Predictor")

    with st.form("predict"):
        gender = st.selectbox("Gender", ["female","male"])
        race = st.selectbox("Race/Ethnicity", ["group A","group B","group C","group D","group E"])
        parent = st.selectbox("Parental Education", [
            "bachelor's degree","some college","master's degree",
            "associate's degree","high school","some high school"
        ])
        lunch = st.selectbox("Lunch", ["standard","free/reduced"])
        prep = st.selectbox("Test Prep", ["none","completed"])
        read = st.number_input("Reading Score",0,100,70)
        write = st.number_input("Writing Score",0,100,70)
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
        df["average"] = (read + write)/2
        df["Unnamed: 0"] = 0

        math = round(max(0,min(100,model.predict(preprocessor.transform(df))[0])),2)
        science = round((math + read)/2 + 2,2)
        computer = round((math + write)/2 + 2,2)
        english = round((read + write)/2 + 1,2)
        overall = round((math+science+computer+english)/4,2)

        st.success("📊 Predicted Scores")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Math",math)
        c2.metric("Science",science)
        c3.metric("Computer",computer)
        c4.metric("English",english)
        st.info(f"⭐ Overall Average: {overall}")

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO predictions (
                username, gender, race_ethnicity, parental_education,
                lunch, test_prep, reading_input, writing_input,
                math, science, computer, english, overall_average
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            st.session_state.username, gender, race, parent,
            lunch, prep, read, write,
            math, science, computer, english, overall
        ))
        conn.commit()
        conn.close()

# =====================================================
# DASHBOARD
# =====================================================
elif page == "Dashboard":
    st.title("📊 Dashboard")
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM predictions WHERE username=?", conn,
                     params=(st.session_state.username,))
    conn.close()
    if df.empty:
        st.info("No data yet")
        st.stop()

    df = fill_missing_predictions(df)
    st.metric("Total Predictions", len(df))
    st.line_chart(df[["math","science","computer","english"]])
    st.bar_chart(df[["math","science","computer","english"]].mean())

# =====================================================
# DATABASE (UPDATED SECTION)
# =====================================================
elif page == "Database":
    st.title("🗄️ Prediction Records")
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM predictions WHERE username=?", conn,
                     params=(st.session_state.username,))
    conn.close()
    if df.empty:
        st.info("No records found")
        st.stop()

    df = fill_missing_predictions(df)

    st.subheader("📋 Raw Input Data")
    st.dataframe(df[[
        "gender","race_ethnicity","parental_education",
        "lunch","test_prep","reading_input","writing_input"
    ]])

    st.markdown("---")

    st.subheader("📊 Predicted Subject Scores")
    st.dataframe(df[[
        "math","science","computer","english","overall_average"
    ]])

# =====================================================
# CHATBOT
# =====================================================
elif page == "Chatbot":
    st.title("🤖 Student Assistant Chatbot")

    conn = get_connection()
    df = pd.read_sql("SELECT * FROM predictions WHERE username=?", conn,
                     params=(st.session_state.username,))
    conn.close()

    df = fill_missing_predictions(df)

    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])

    user_input = st.chat_input("Ask about your performance...")

    if user_input:
        st.session_state.chat_history.append({"role":"user","content":user_input})
        txt = user_input.lower()

        if df.empty:
            reply = "Please make a prediction first 🙂"
        elif "math" in txt:
            reply = f"📐 Avg Math score: {round(df['math'].mean(),2)}"
        elif "science" in txt:
            reply = f"🔬 Avg Science score: {round(df['science'].mean(),2)}"
        elif "computer" in txt:
            reply = f"💻 Avg Computer score: {round(df['computer'].mean(),2)}"
        elif "english" in txt:
            reply = f"📘 Avg English score: {round(df['english'].mean(),2)}"
        elif "best" in txt:
            reply = f"🌟 Best subject: {df[['math','science','computer','english']].mean().idxmax().title()}"
        elif "average" in txt:
            reply = f"⭐ Overall Average: {round(df['overall_average'].mean(),2)}"
        else:
            reply = "Ask me about subject scores, best subject, or overall average."

        st.session_state.chat_history.append({"role":"assistant","content":reply})
        with st.chat_message("assistant"):
            st.markdown(reply)
