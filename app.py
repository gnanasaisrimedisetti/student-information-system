
import streamlit as st
import pandas as pd
import subprocess
import base64
import json
import shutil
from pathlib import Path

# ---------------- CONFIGURATION ----------------

st.set_page_config(
    page_title="Student Information System",
    page_icon="🎓",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR
JAVA_FILE = BASE_DIR / "StudentSystem.java"
CSV_FILE = BASE_DIR / "Students.csv"
# ---------------- JAVA COMPILATION ----------------

def compile_java():
    javac = shutil.which("javac")
    java = shutil.which("java")

    if not javac or not java:
        st.error("Java JDK is not installed.")
        st.stop()

    class_file = BACKEND_DIR / "StudentSystem.class"

    if (
        not class_file.exists()
        or class_file.stat().st_mtime < JAVA_FILE.stat().st_mtime
    ):
        result = subprocess.run(
            [javac, "-encoding", "UTF-8", str(JAVA_FILE)],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            st.error("Java compilation failed.")
            st.code(result.stderr)
            st.stop()

# ---------------- JAVA BRIDGE ----------------

def encode(value):
    return base64.urlsafe_b64encode(
        str(value).encode("utf-8")
    ).decode("ascii")

def java_command(command, values=None):
    compile_java()

    args = [
        shutil.which("java"),
        "-cp",
        str(BACKEND_DIR),
        "StudentSystem",
        command
    ]

    if values:
        args.extend([encode(v) for v in values])

    result = subprocess.run(
        args,
        cwd=BASE_DIR,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    output = result.stdout.strip()

    if output:
        return json.loads(output)

    return None

# ---------------- STUDENT OPERATIONS ----------------

COLUMNS = ["ID", "Name", "Department", "GPA", "Email"]

def get_students():
    records = java_command("list")

    if not records:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(records)
    df.columns = COLUMNS
    return df

def add_student(student):
    return java_command("add", student)

def update_student(student):
    return java_command("update", student)

def delete_student(student_id):
    return java_command("delete", [student_id])

# ---------------- SESSION STATE ----------------

if "refresh" not in st.session_state:
    st.session_state.refresh = 0

def refresh_data():
    st.session_state.refresh += 1

# ---------------- SIDEBAR ----------------

st.sidebar.title("🎓 Student System")
st.sidebar.caption("Student Information Management")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Add Student",
        "View Students",
        "Update Student",
        "Delete Student"
    ]
)

st.sidebar.divider()
st.sidebar.info("Java Backend | Streamlit Frontend")

# ---------------- LOAD DATA ----------------

try:
    df = get_students()
except Exception as e:
    st.error(f"Unable to load student records: {e}")
    st.stop()

# ---------------- DASHBOARD ----------------

if page == "Dashboard":

    st.title("🎓 Student Information Dashboard")
    st.write("Manage and monitor student information.")

    total = len(df)
    average = df["GPA"].mean() if total else 0
    highest = df["GPA"].max() if total else 0
    departments = df["Department"].nunique() if total else 0

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Students", total)
    col2.metric("Average GPA", f"{average:.2f}")
    col3.metric("Highest GPA", f"{highest:.2f}")
    col4.metric("Departments", departments)

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Students by Department")

        if total:
            department_counts = df["Department"].value_counts()
            st.bar_chart(department_counts)
        else:
            st.info("No student records available.")

    with right:
        st.subheader("GPA Distribution")

        if total:
            st.bar_chart(
                df.set_index("Name")["GPA"]
            )
        else:
            st.info("Add students to view GPA statistics.")

    st.subheader("Recent Student Records")
    st.dataframe(df.tail(5), use_container_width=True)

# ---------------- ADD STUDENT ----------------

elif page == "Add Student":

    st.title("➕ Add New Student")
    st.write("Enter the student's information below.")

    with st.form("add_form"):

        student_id = st.text_input("Student ID")
        name = st.text_input("Student Name")

        department = st.selectbox(
            "Department",
            [
                "Computer Science",
                "Data Science",
                "Information Technology",
                "Electronics",
                "Mechanical",
                "Civil",
                "Electrical"
            ]
        )

        gpa = st.number_input(
            "GPA",
            min_value=0.0,
            max_value=10.0,
            value=8.0,
            step=0.1
        )

        email = st.text_input("Email Address")

        submitted = st.form_submit_button(
            "Add Student",
            use_container_width=True
        )

        if submitted:
            if not all([
                student_id.strip(),
                name.strip(),
                email.strip()
            ]):
                st.error("Please fill all required fields.")

            else:
                try:
                    add_student([
                        student_id.strip(),
                        name.strip(),
                        department,
                        f"{gpa:.2f}",
                        email.strip()
                    ])

                    st.success("Student added successfully!")
                    refresh_data()

                except Exception as e:
                    st.error(str(e))

# ---------------- VIEW STUDENTS ----------------

elif page == "View Students":

    st.title("📋 Student Records")

    if not df.empty:

        search = st.text_input(
            "Search by Student ID or Name"
        )

        department_filter = st.selectbox(
            "Filter by Department",
            ["All"] + sorted(
                df["Department"].unique().tolist()
            )
        )

        filtered = df.copy()

        if search:
            filtered = filtered[
                filtered["ID"].str.contains(
                    search, case=False, na=False
                )
                |
                filtered["Name"].str.contains(
                    search, case=False, na=False
                )
            ]

        if department_filter != "All":
            filtered = filtered[
                filtered["Department"] == department_filter
            ]

        st.write(f"Showing {len(filtered)} student records.")

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True
        )

        csv_data = filtered.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Student Records",
            data=csv_data,
            file_name="student_records.csv",
            mime="text/csv"
        )

    else:
        st.info("No student records found. Add students first.")

# ---------------- UPDATE STUDENT ----------------

elif page == "Update Student":

    st.title("✏️ Update Student Details")

    if not df.empty:

        student_ids = df["ID"].tolist()

        selected_id = st.selectbox(
            "Select Student ID",
            student_ids
        )

        student = df[
            df["ID"] == selected_id
        ].iloc[0]

        with st.form("update_form"):

            name = st.text_input(
                "Student Name",
                value=student["Name"]
            )

            departments = [
                "Computer Science",
                "Data Science",
                "Information Technology",
                "Electronics",
                "Mechanical",
                "Civil",
                "Electrical"
            ]

            current_department = student["Department"]

            if current_department not in departments:
                departments.append(current_department)

            department = st.selectbox(
                "Department",
                departments,
                index=departments.index(current_department)
            )

            gpa = st.number_input(
                "GPA",
                min_value=0.0,
                max_value=10.0,
                value=float(student["GPA"]),
                step=0.1
            )

            email = st.text_input(
                "Email",
                value=student["Email"]
            )

            submitted = st.form_submit_button(
                "Update Student",
                use_container_width=True
            )

            if submitted:
                try:
                    update_student([
                        selected_id,
                        name.strip(),
                        department,
                        f"{gpa:.2f}",
                        email.strip()
                    ])

                    st.success("Student updated successfully!")
                    refresh_data()

                except Exception as e:
                    st.error(str(e))

    else:
        st.info("No students available to update.")

# ---------------- DELETE STUDENT ----------------

elif page == "Delete Student":

    st.title("🗑️ Delete Student Record")

    if not df.empty:

        selected_id = st.selectbox(
            "Select Student ID",
            df["ID"].tolist()
        )

        selected = df[
            df["ID"] == selected_id
        ].iloc[0]

        st.warning(
            f"Student: {selected['Name']} | "
            f"Department: {selected['Department']}"
        )

        confirm = st.checkbox(
            "I confirm that I want to delete this student."
        )

        if st.button(
            "Delete Student",
            type="primary",
            disabled=not confirm
        ):
            try:
                delete_student(selected_id)

                st.success("Student deleted successfully!")
                refresh_data()

            except Exception as e:
                st.error(str(e))

    else:
        st.info("No student records available to delete.")

# ---------------- FOOTER ----------------

st.sidebar.divider()
st.sidebar.caption("Student Information System")
st.sidebar.caption("Developed using Java and Python")
