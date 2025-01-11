import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
from pathlib import Path

# Constants for database connection
BASE_DIR = Path(__file__).resolve().parent
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'admin!@#123'
DB_NAME = 'quiz_db2'  # Update database connection details

# Function to paginate a dataframe
def paginate_dataframe(df, page_size, page_number):
    start_index = page_number * page_size
    end_index = start_index + page_size
    return df.iloc[start_index:end_index]

# Function to show the admin panel
def show_admin_panel():
    st.title("Admin Panel")
    st.subheader("View and Analyze Student Scores and Responses")

    # Query database for all responses
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        query = "SELECT * FROM responses"
        df = pd.read_sql(query, conn)

        # Calculate total correct and incorrect answers
        question_cols = [col for col in df.columns if "q" in col and "score" in col]
        df["total_correct"] = df[question_cols].apply(lambda row: (row > 0).sum(), axis=1)
        df["total_incorrect"] = df[question_cols].apply(lambda row: (row == 0).sum(), axis=1)

        total_correct = df["total_correct"].sum()
        total_incorrect = df["total_incorrect"].sum()

        st.metric("Total Correct Answers", total_correct)
        st.metric("Total Incorrect Answers", total_incorrect)

        # Pie chart for correct and incorrect answers
        pie_data = pd.DataFrame({
            "Category": ["Correct Answers", "Incorrect Answers"],
            "Count": [total_correct, total_incorrect]
        })
        pie_chart = px.pie(pie_data, values="Count", names="Category", title="Correct vs Incorrect Answers")
        st.plotly_chart(pie_chart)

        # Score Distribution Chart
        st.subheader("Score Distribution")
        st.bar_chart(df["score"].value_counts().sort_index())

        # Filters
        st.subheader("Filter Results")

        # Dropdown for student name filter
        student_name_filter = st.selectbox("Select Student Name", ["All"] + sorted(df["student_name"].unique()))
        if student_name_filter != "All":
            df = df[df["student_name"].str.contains(student_name_filter, case=False)]

            # Breakdown of correct and incorrect answers for selected student
            st.subheader(f"Question Breakdown for {student_name_filter}")
            correct_questions = df["total_correct"].sum()
            incorrect_questions = df["total_incorrect"].sum()

            st.write(f"**Correct Questions:** {correct_questions}")
            st.write(f"**Incorrect Questions:** {incorrect_questions}")

            # Pie chart for correct vs incorrect questions
            pie_data_student = pd.DataFrame({
                "Category": ["Correct Questions", "Incorrect Questions"],
                "Count": [correct_questions, incorrect_questions]
            })
            pie_chart_student = px.pie(pie_data_student, values="Count", names="Category", title="Correct vs Incorrect Questions")
            st.plotly_chart(pie_chart_student)

        # Pagination
        st.subheader("Filtered Results")
        page_size = 10  # Number of records per page
        total_pages = len(df) // page_size + (1 if len(df) % page_size > 0 else 0)
        page_number = st.number_input("Page Number", min_value=1, max_value=total_pages, step=1, value=1) - 1
        paginated_df = paginate_dataframe(df, page_size, page_number)

        # Display the filtered and paginated data
        st.dataframe(paginated_df)

        st.write(f"Showing page {page_number + 1} of {total_pages}")

    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
    finally:
        if conn.is_connected():
            conn.close()

# Admin Panel (optional)
def download_studentanswers():
    st.header("Admin Panel")
    st.write("This section is for administrative tasks, like managing students or viewing quiz results.")

    # Display all responses
    if st.button("Show All Responses"):
        try:
            conn = mysql.connector.connect(
                                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            df = pd.read_sql_query("SELECT * FROM responses", conn)
            st.dataframe(df)
        except Exception as e:
            st.error(f"Error loading responses: {e}")
        finally:
            if conn.is_connected():
                conn.close()

    # Download responses
    if st.button("Download Responses as CSV"):
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            df = pd.read_sql_query("SELECT * FROM responses", conn)
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name='responses.csv',
                mime='text/csv',
            )
        except Exception as e:
            st.error(f"Error generating CSV: {e}")
        finally:
            if conn.is_connected():
                conn.close()

# Main function for the Streamlit app
def main():
    # Authentication part
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        st.subheader("Login to Admin Panel")

        # Login form
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if username == "admin" and password == "password":  # Replace with secure authentication
                st.session_state["authenticated"] = True
                st.success("Login successful!")
                show_admin_panel()
                download_studentanswers()
            else:
                st.error("Invalid credentials. Please try again.")
    else:
        # If authenticated, show the admin panel
        show_admin_panel()
        download_studentanswers()

# Run the app
if __name__ == "__main__":
    main()
