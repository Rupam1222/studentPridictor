import streamlit as st
import pickle
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Student Performance App", layout="wide")

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================
if "users" not in st.session_state:
    st.session_state.users = {"admin": "admin123"}

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"

if "prediction_data" not in st.session_state:
    st.session_state.prediction_data = pd.DataFrame(
        columns=[
            "gender",
            "race_ethnicity",
            "parental_level_of_education",
            "lunch",
            "test_preparation_course",
            "reading_input",
            "writing_input",
            "predicted_math",
            "predicted_reading",
            "predicted_writing",
            "overall_average"
        ]
    )

# =====================================================
# LOGIN PAGE
# =====================================================
def login_page():
    st.title("🔐 Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

    if login_btn:
        if username in st.session_state.users and st.session_state.users[username] == password:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

    if st.button("🆕 Create new account"):
        st.session_state.auth_page = "register"
        st.rerun()

# =====================================================
# REGISTER PAGE
# =====================================================
def register_page():
    st.title("📝 Register")

    with st.form("register_form"):
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")
        register_btn = st.form_submit_button("Register")

    if register_btn:
        if new_user in st.session_state.users:
            st.error("Username already exists")
        elif new_pass != confirm_pass:
            st.error("Passwords do not match")
        else:
            st.session_state.users[new_user] = new_pass
            st.success("Account created successfully")
            st.session_state.auth_page = "login"
            st.rerun()

    if st.button("⬅ Back to Login"):
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
# LOAD MODEL & PREPROCESSOR
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
st.sidebar.title("📚 Navigation")
st.sidebar.success(f"Logged in as: {st.session_state.username}")
page = st.sidebar.radio("Go to", ["Predictor", "Dashboard", "Database"])
st.sidebar.button("🚪 Logout", on_click=logout)

# =====================================================
# PREDICTOR PAGE
# =====================================================
if page == "Predictor":

    st.title("🎯 Student Score Predictor")

    with st.form("prediction_form"):
        col1, col2 = st.columns(2)

        with col1:
            gender = st.selectbox("Gender", ["female", "male"])
            race_ethnicity = st.selectbox(
                "Race/Ethnicity",
                ["group A", "group B", "group C", "group D", "group E"]
            )
            parental_education = st.selectbox(
                "Parental Education",
                ["bachelor's degree", "some college",
                 "master's degree", "associate's degree",
                 "high school", "some high school"]
            )

        with col2:
            lunch = st.selectbox("Lunch Type", ["standard", "free/reduced"])
            test_prep = st.selectbox("Test Preparation Course", ["none", "completed"])

        r1, r2 = st.columns(2)
        reading_score = r1.number_input("Reading Score", 0, 100, 70)
        writing_score = r2.number_input("Writing Score", 0, 100, 70)

        submit_btn = st.form_submit_button("Predict Scores", type="primary")

    if submit_btn:
        input_df = pd.DataFrame({
            "gender": [gender],
            "race_ethnicity": [race_ethnicity],
            "parental_level_of_education": [parental_education],
            "lunch": [lunch],
            "test_preparation_course": [test_prep],
            "reading_score": [reading_score],
            "writing_score": [writing_score]
        })

        # Required engineered features
        input_df["total score"] = reading_score + writing_score
        input_df["average"] = (reading_score + writing_score) / 2
        input_df["Unnamed: 0"] = 0

        scaled = preprocessor.transform(input_df)
        math_pred = max(0, min(100, model.predict(scaled)[0]))

        # Derived subject predictions
        reading_pred = min(100, reading_score + 2)
        writing_pred = min(100, writing_score + 2)
        overall_avg = round((math_pred + reading_pred + writing_pred) / 3, 2)

        st.success("📊 Predicted Scores")

        c1, c2, c3 = st.columns(3)
        c1.metric("📐 Math", f"{math_pred:.2f}")
        c2.metric("📘 Reading", f"{reading_pred:.2f}")
        c3.metric("✍️ Writing", f"{writing_pred:.2f}")

        st.info(f"⭐ Overall Average Score: **{overall_avg}**")

        st.session_state.prediction_data.loc[len(st.session_state.prediction_data)] = [
            gender, race_ethnicity, parental_education, lunch, test_prep,
            reading_score, writing_score,
            math_pred, reading_pred, writing_pred, overall_avg
        ]

# =====================================================
# DASHBOARD PAGE
# =====================================================
elif page == "Dashboard":

    st.title("📊 Performance Dashboard")

    df = st.session_state.prediction_data
    if df.empty:
        st.warning("No predictions available yet.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Predictions", len(df))
    col2.metric("Avg Math Score", f"{df['predicted_math'].mean():.2f}")
    col3.metric("Highest Avg Score", f"{df['overall_average'].max():.2f}")

    st.markdown("---")
    st.subheader("📈 Math Score Trend")
    st.line_chart(df["predicted_math"])

    st.markdown("---")
    st.subheader("📊 Subject Comparison")
    st.bar_chart(df[["predicted_math", "predicted_reading", "predicted_writing"]])

    st.markdown("---")
    st.subheader("🎓 Avg Math Score by Parental Education")
    edu_avg = df.groupby("parental_level_of_education")["predicted_math"].mean()
    st.bar_chart(edu_avg.sort_values(ascending=False))

# =====================================================
# DATABASE PAGE
# =====================================================
elif page == "Database":

    st.title("🗄️ Prediction Records")

    df = st.session_state.prediction_data
    if df.empty:
        st.info("No data available.")
        st.stop()

    st.dataframe(df)
    st.caption(f"Total Records: {len(df)}")
