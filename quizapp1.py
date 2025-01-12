import mysql.connector
import pandas as pd
import streamlit as st
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import re
import time

# Modify your database connections to use environment variables
import os
from pathlib import Path

# Constants
BASE_DIR = Path(__file__).resolve().parent
import toml

# Load secrets from secrets.toml

#DB_HOST = 'localhost'
#DB_USER = 'root'
#DB_PASSWORD = 'admin!@#123'
#DB_NAME = 'quiz_db2'  # Update database connection details

DB_HOST = st.secrets["database"]["host"]
DB_USER = st.secrets["database"]["user"]
DB_PASSWORD = st.secrets["database"]["password"]
DB_NAME = st.secrets["database"]["name"]
DB_CONFIG = {
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'database': DB_NAME,
    'port': 3306,
}

def test_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("Successfully connected!")
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

test_connection()
QUIZ_DURATION = 300  # 5 minutes in seconds

# Example set of questions
questions = [
    {"id": "q1", "type": "text", "question": "What is the capital of France?", "correct_answer": "Paris", "score": 2},
    {"id": "q2", "type": "text", "question": "What is 5 + 3?", "correct_answer": "8", "score": 1},
    {"id": "q3", "type": "single", "question": "What is the largest planet?", "options": ["Earth", "Mars", "Jupiter", "Venus"], "correct_answer": "Jupiter", "score": 2},
    {"id": "q4", "type": "multi", "question": "Which are programming languages? (Choose all that apply)", 
     "options": ["Python", "HTML", "C++", "CSS"], "correct_answers": ["Python", "C++"], "score": 3}
]

# Function to execute SQL queries
def execute_sql(query, params=()):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
    finally:
        cursor.close()
        conn.close()

def check_if_taken(student_name, student_seat):
    query = 'SELECT * FROM responses WHERE student_name = %s AND student_seat = %s'
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(query, (student_name, student_seat))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None

def create_tables():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute('''CREATE TABLE IF NOT EXISTS responses (
                            student_name VARCHAR(255),
                            student_seat VARCHAR(255),
                            submitted_name VARCHAR(255),
                            submitted_seat VARCHAR(255),
                            score INT,
                            timestamp DATETIME,
                            student_email VARCHAR(255)
                        )''')
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        # You can also log this error if necessary

def add_columns_dynamically(num_questions):
    cursor = None
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        for q_num in range(1, num_questions + 1):
            column_checks = [
                f"q{q_num}_student_answer",
                f"q{q_num}_correct_answer",
                f"q{q_num}_score"
            ]
            for column in column_checks:
                cursor.execute(f"SHOW COLUMNS FROM responses LIKE '{column}'")
                result = cursor.fetchone()
                if not result:
                    cursor.execute(f"ALTER TABLE responses ADD COLUMN {column} TEXT")
            conn.commit()
    except mysql.connector.Error as e:
        print(f"Error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()



create_tables()
add_columns_dynamically(len(questions))

def format_time(seconds):
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"

def initialize_session_state():
    if 'page' not in st.session_state:
        st.session_state['page'] = 'home'
    if 'student_name' not in st.session_state:
        st.session_state['student_name'] = None
    if 'student_seat' not in st.session_state:
        st.session_state['student_seat'] = None
    if 'student_email' not in st.session_state:
        st.session_state['student_email'] = st.session_state['student_email'] = None
    if 'responses' not in st.session_state:
        st.session_state['responses'] = {}
    if 'score' not in st.session_state:
        st.session_state['score'] = 0
    if 'timer' not in st.session_state:
        st.session_state['timer'] = QUIZ_DURATION
    if 'timer_active' not in st.session_state:
        st.session_state['timer_active'] = False
    if 'auto_submitted' not in st.session_state:
        st.session_state['auto_submitted'] = False

def main():
    st.set_page_config(
        page_title="Quiz Application",
        page_icon="📝",
        layout="wide"
    )
    initialize_session_state()

    if st.session_state['page'] == 'home':
        show_home()
    elif st.session_state['page'] == 'student_data':
        show_student_data()
    elif st.session_state['page'] == 'quiz':
        show_quiz()
    elif st.session_state['page'] == 'already_taken':
        show_already_taken()
    elif st.session_state['page'] == 'result':
        show_result()

def show_home():
    st.title("Welcome to the Quiz Application")
    
    st.header("Exam Description")
    st.write("""
        This quiz is designed to assess your knowledge in various subjects. 
        You will be asked a series of questions, and you will need to answer them to the best of your ability.
    """)
    
    st.header("Instructions")
    st.write(f"""
    - Please enter your name, seat number, and email to start the quiz.
    - You have {QUIZ_DURATION//60} minutes to complete the quiz.
    - The quiz will automatically submit when the timer reaches zero.
    - Answer all questions to the best of your knowledge.
    - After completing the quiz, your score will be displayed along with the email status.
    - You can only take the quiz once. If you have already completed the quiz, you cannot retake it.
    """)

    if st.button("Start Quiz"):
        st.session_state['page'] = 'student_data'

def show_student_data():
    st.subheader("Enter Your Details")
    
    student_name = st.text_input("Name", placeholder="ادخل اسمك بالعربى")
    student_seat = st.text_input("Seat Number", placeholder="ادخل رقم الجلوس")
    student_email = st.text_input("Email", placeholder="ادخل الايميل الخاص بك")

    if st.button("Next"):
        if not validate_student_details(student_name, student_seat):
            st.error("Invalid name or seat number. Please try again.")
        else:
            if check_if_taken(student_name, student_seat):
                st.session_state.update({
                    'student_name': student_name,
                    'student_seat': student_seat,
                    'student_email': student_email,
                    'page': 'already_taken'
                })
            else:
                st.session_state.update({
                    'student_name': student_name,
                    'student_seat': student_seat,
                    'student_email': student_email,
                    'timer_active': True,
                    'page': 'quiz'
                })
                st.rerun()

def show_quiz():
    if not st.session_state.get('timer_active', False):
        st.session_state['timer_active'] = True
        
    # Display timer at the top
    time_placeholder = st.empty()
    time_placeholder.markdown(
        f"""
        <div style="display: flex; justify-content: center; margin: 20px 0;">
            <div style="background-color: #f0f2f6; padding: 10px 20px; border-radius: 10px; text-align: center;">
                <span style="font-size: 24px; font-weight: bold; color: {'red' if st.session_state['timer'] < 60 else 'black'}">
                    Time Remaining: {format_time(st.session_state['timer'])}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Display questions
    st.subheader("Quiz Questions")
    for question in questions:
        q_id = question["id"]
        st.write(f"\n**{question['question']}**")
        
        if question["type"] == "text":
            st.session_state['responses'][q_id] = st.text_input(
                "Your answer",
                key=q_id,
                value=st.session_state['responses'].get(q_id, "")
            )
        elif question["type"] == "single":
            st.session_state['responses'][q_id] = st.radio(
                "Select one answer",
                question["options"],
                key=q_id,
                index=question["options"].index(st.session_state['responses'].get(q_id, question["options"][0]))
                if q_id in st.session_state['responses'] and st.session_state['responses'][q_id] in question["options"]
                else 0
            )
        elif question["type"] == "multi":
            st.session_state['responses'][q_id] = st.multiselect(
                "Select all that apply",
                question["options"],
                key=q_id,
                default=st.session_state['responses'].get(q_id, [])
            )

    # Submit button
    if st.button("Submit Quiz"):
        calculate_score()
        return

    # Update timer
    if st.session_state['timer_active']:
        if st.session_state['timer'] > 0:
            time.sleep(1)
            st.session_state['timer'] -= 1
            st.rerun()
        elif not st.session_state['auto_submitted']:
            st.session_state['auto_submitted'] = True
            calculate_score()
            return

def validate_student_details(name, seat):
    cursor = None
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM student_list WHERE name = %s AND seat_number = %s', (name, seat))
        result = cursor.fetchone()
        return result is not None
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def calculate_score():
    responses = st.session_state.responses
    total_score = 0
    response_details = {}

    for question in questions:
        q_id = question["id"]
        student_answer = responses.get(q_id)
        correct_answer = question.get("correct_answer")
        correct_answers = question.get("correct_answers")
        
        is_correct = False
        if question["type"] == "text":
            is_correct = str(student_answer).strip().lower() == str(correct_answer).strip().lower()
        elif question["type"] == "single":
            is_correct = student_answer == correct_answer
        elif question["type"] == "multi":
            if isinstance(student_answer, list):
                is_correct = set(student_answer) == set(correct_answers)

        question_score = question["score"] if is_correct else 0
        total_score += question_score

        response_details[q_id] = {
            "student_answer": student_answer if student_answer else "N/A",
            "correct_answer": correct_answer if correct_answer else correct_answers,
            "score": question_score,
        }

    # Save to database
    student_name = st.session_state.get("student_name", "Unknown")
    student_seat = st.session_state.get("student_seat", "Unknown")
    student_email = st.session_state.get("student_email", "Unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    question_columns = ", ".join(
        [f"q{idx+1}_student_answer, q{idx+1}_correct_answer, q{idx+1}_score" for idx in range(len(questions))]
    )
    placeholders = ", ".join(["%s"] * (3 * len(questions)))
    sql_query = f'''INSERT INTO responses (
                        student_name, student_seat, submitted_name, submitted_seat,
                        score, timestamp, student_email, {question_columns}
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, {placeholders})'''

    question_values = []
    for idx, question in enumerate(questions):
        q_id = question["id"]
        student_answer = response_details[q_id]["student_answer"]
        correct_answer = response_details[q_id]["correct_answer"]
        
        if isinstance(student_answer, list):
            student_answer = ", ".join(student_answer)
        if isinstance(correct_answer, list):
            correct_answer = ", ".join(correct_answer)
        
        question_values.extend([student_answer, correct_answer, response_details[q_id]["score"]])

    execute_sql(sql_query, (
        student_name, student_seat, student_name, student_seat, total_score, timestamp, student_email, *question_values
    ))

    st.session_state['score'] = total_score
    st.session_state['timer_active'] = False
    st.session_state['page'] = 'result'
    st.rerun()

def show_already_taken():
    st.subheader("Quiz Already Taken")
    st.write("You have already taken the quiz. You cannot retake it.")

    student_name = st.session_state.get('student_name')
    student_seat = st.session_state.get('student_seat')

    if not student_name or not student_seat:
        st.write("Missing student information. Cannot retrieve score.")
        return

    query = '''
        SELECT score FROM responses
        WHERE student_name = %s AND student_seat = %s
        ORDER BY timestamp DESC LIMIT 1
    '''
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query,         (student_name, student_seat))
        result = cursor.fetchone()

        if result:
            score = result[0]
            st.write(f"Your previous score: {score}")
        else:
            st.write("No previous quiz attempt found.")
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
    finally:
        cursor.close()
        conn.close()

def show_result():
    st.header("Your Results")
    
    if st.session_state.get('auto_submitted'):
        st.warning("Time's up! Your quiz was automatically submitted.")
    
    score = st.session_state.get('score', 0)
    st.write(f"Your total score: {score}")
    
    send_email_result()



def send_email_result():
    student_email = st.session_state.get('student_email')
    score = st.session_state.get('score', 0)

    try:
        msg = MIMEText(f"Hello, \n\nYou have completed the quiz. Your score is {score}.\n\nBest regards!")
        msg['Subject'] = 'Quiz Results'
        msg['From'] = st.secrets["email"]["sender"]
        msg['To'] = student_email

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            # Use email credentials from secrets
            server.login(
                st.secrets["email"]["sender"],
                st.secrets["email"]["password"]
            )
            server.sendmail(
                st.secrets["email"]["sender"],
                student_email, 
                msg.as_string()
            )

        st.success(f"Result sent via email: {student_email}")
    except Exception as e:
        st.error(f"Failed to send email: {e}")

if __name__ == "__main__":
    main()
