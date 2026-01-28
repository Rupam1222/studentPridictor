import streamlit as st
import pickle
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Student Performance App",
    layout="wide"
)

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================
if "users" not in st.session_state:
    st.session_state.users = {
        "admin": "admin123"
    }

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"

if "prediction_data" not in st.session_state:
    st.session_state.prediction_data = pd.DataFrame(
        columns=[
            'gender',
            'race_ethnicity',
            'parental_level_of_education',
            'lunch',
            'test_preparation_course',
            'reading_score',
            'writing_score',
            'predicted_math_score'
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
            st.success("✅ Login successful")
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

    st.markdown("---")
    if st.button("🆕 Create new account"):
        st.session_state.auth_page = "register"
        st.rerun()

# =====================================================
# REGISTER / SIGNUP PAGE
# =====================================================
def register_page():
    st.title("📝 Register / Sign Up")

    with st.form("register_form"):
        new_user = st.text_input("Choose Username")
        new_pass = st.text_input("Choose Password", type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")
        register_btn = st.form_submit_button("Register")

    if register_btn:
        if new_user in st.session_state.users:
            st.error("❌ Username already exists")
        elif new_pass != confirm_pass:
            st.error("❌ Passwords do not match")
        elif len(new_pass) < 4:
            st.error("❌ Password must be at least 4 characters")
        else:
            st.session_state.users[new_user] = new_pass
            st.success("✅ Account created successfully")
            st.info("Please login to continue")

    st.markdown("---")
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
# SIDEBAR NAVIGATION
# =====================================================
st.sidebar.title("📚 Navigation")
st.sidebar.success(f"Logged in as: {st.session_state.username}")

page = st.sidebar.radio(
    "Go to",
    ["Predictor", "Dashboard", "Database"]
)

st.sidebar.button("🚪 Logout", on_click=logout)

# =====================================================
# 1️⃣ PREDICTOR PAGE
# =====================================================
if page == "Predictor":

    st.title("🎯 Student Math Score Predictor")

    with st.form("prediction_form"):
        col1, col2 = st.columns(2)

        with col1:
            gender = st.selectbox("Gender", ["female", "male"])
            race_ethnicity = st.selectbox(
                "Race/Ethnicity",
                ['group A', 'group B', 'group C', 'group D', 'group E']
            )
            parental_education = st.selectbox(
                "Parental Education",
                ["bachelor's degree", "some college",
                 "master's degree", "associate's degree",
                 "high school", "some high school"]
            )

        with col2:
            lunch = st.selectbox("Lunch Type", ['standard', 'free/reduced'])
            test_prep = st.selectbox(
                "Test Preparation Course",
                ['none', 'completed']
            )

        c1, c2 = st.columns(2)
        reading_score = c1.number_input("Reading Score", 0, 100, 70)
        writing_score = c2.number_input("Writing Score", 0, 100, 70)

        submit_btn = st.form_submit_button("Predict Math Score", type="primary")

    if submit_btn:
        input_data = pd.DataFrame({
            'gender': [gender],
            'race_ethnicity': [race_ethnicity],
            'parental_level_of_education': [parental_education],
            'lunch': [lunch],
            'test_preparation_course': [test_prep],
            'reading_score': [reading_score],
            'writing_score': [writing_score]
        })

        input_data['total score'] = reading_score + writing_score
        input_data['average'] = (reading_score + writing_score) / 2
        input_data['Unnamed: 0'] = 0

        data_scaled = preprocessor.transform(input_data)
        prediction = model.predict(data_scaled)[0]
        prediction = max(0, min(100, prediction))

        st.success(f"📐 Estimated Math Score: **{prediction:.2f}**")

        st.session_state.prediction_data.loc[len(st.session_state.prediction_data)] = [
            gender, race_ethnicity, parental_education, lunch, test_prep,
            reading_score, writing_score, prediction
        ]

# =====================================================
# 2️⃣ DASHBOARD PAGE
# =====================================================
elif page == "Dashboard":

    st.title("📊 Live Student Performance Dashboard")

    df = st.session_state.prediction_data

    if df.empty:
        st.warning("No predictions yet.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Predictions", len(df))
    col2.metric("Average Math Score", f"{df['predicted_math_score'].mean():.2f}")
    col3.metric("Highest Math Score", f"{df['predicted_math_score'].max():.2f}")

    st.markdown("---")
    st.subheader("📈 Math Score Trend")
    st.line_chart(df['predicted_math_score'])

    st.markdown("---")
    st.subheader("📊 Reading, Writing vs Predicted Math")
    st.bar_chart(df[['reading_score', 'writing_score', 'predicted_math_score']])

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("👩‍🎓 Average Math Score by Gender")
        st.bar_chart(df.groupby('gender')['predicted_math_score'].mean())

    with col2:
        st.subheader("🎓 Average Math Score by Parental Education")
        edu_avg = df.groupby('parental_level_of_education')['predicted_math_score'].mean()
        st.bar_chart(edu_avg.sort_values(ascending=False))

# =====================================================
# 3️⃣ DATABASE PAGE
# =====================================================
elif page == "Database":

    st.title("🗄️ Prediction Database")

    df = st.session_state.prediction_data

    if df.empty:
        st.info("No records available yet.")
        st.stop()

    gender_filter = st.multiselect(
        "Filter by Gender",
        options=df['gender'].unique(),
        default=df['gender'].unique()
    )

    st.dataframe(df[df['gender'].isin(gender_filter)])
    st.caption(f"Total Records: {len(df)}")