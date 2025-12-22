import streamlit as st
import pickle
import pandas as pd


# page configuration

st.set_page_config(page_title= "Student Score Predictor", layout = 'centered')


st.title("Student Math Score Predictor")
st.markdown("Enter student details below to predict their math score")

# loading preprocessor
with open('preprocessor.pkl' , 'rb') as f:
    preprocessor = pickle.load(f)

# loading model
with open('model.pkl' , 'rb') as f:
    model = pickle.load(f)


# input form

with st.form("prediction_form"):
    st.subheader("Student Details")


    col1, col2 = st.columns(2)

    with col1:
        gender = st.selectbox("Gender",
                              options= ["female", "male"])

        race_ethnicity = st.selectbox("Race/Ethnicity",
                                      options = ['group A', 'group B', 'group C', 'group D', 'group E']
                                      )

        parental_education = st.selectbox("Parental Education",
                                          options= ["bachelor's degree", "some college",
                                                    "master's degree", "associate's degree",
                                                    "high school", "some high school"])

    with col2:
        lunch = st.selectbox("Lunch Type",
                             options= ['standard', 'free/reduced'])

        test_prep = st.selectbox("Test Preparation Course",
                                 options= ['none', 'completed'])


    st.markdown('---')
    st.subheader("Other Subjects")


    c1, c2 = st.columns(2)
    with c1:
        reading_score = st.number_input("Reading Score (0-100)", min_value= 0, max_value= 100, value= 70)

    with c2:
        writing_score = st.number_input("Writing Score (0-100)", min_value= 0, max_value= 100, value= 70)

    submit_btn = st.form_submit_button("Predict Math Score", type= 'primary')


# prediction logic

if submit_btn:
    # prepare dataframe
    input_data = pd.DataFrame({
        'gender': [gender],
        'race_ethnicity': [race_ethnicity],
        'parental_level_of_education': [parental_education],
        'lunch': [lunch],
        'test_preparation_course': [test_prep],
        'reading_score': [reading_score],
        'writing_score': [writing_score]
    }
    )

    # preprocessing data
    data_scaled = preprocessor.transform(input_data)

    # predict

    prediction = model.predict(data_scaled)

    # display result

    st.success("Estimated Math Score: **{:.2f}**".format(prediction[0]))