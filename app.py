import streamlit as st
from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
from bson.objectid import ObjectId

# -----------------------
# MongoDB Connection
# -----------------------
client = MongoClient("mongodb://localhost:27017/")
db = client["school"]
students = db["students"]

# -----------------------
# App Title
# -----------------------
st.title("🎓 Student Marks Tracker & Analyzer")

# -----------------------
# Input Mode Selection
# -----------------------
mode = st.radio("Select Input Method:", ["Manual Entry", "Upload CSV"])

if mode == "Manual Entry":
    with st.form("entry_form"):
        st.subheader("➕ Add Student Details")
        name = st.text_input("Student Name")
        math = st.number_input("Math Marks", min_value=0, max_value=100)
        science = st.number_input("Science Marks", min_value=0, max_value=100)
        english = st.number_input("English Marks", min_value=0, max_value=100)
        submitted = st.form_submit_button("Submit")

        if submitted:
            mark_dict = {"Math": math, "Science": science, "English": english}
            students.insert_one({"name": name, "marks": mark_dict, "source": "manual"})
            st.success("✅ Student record added!")

elif mode == "Upload CSV":
    st.subheader("📁 Upload CSV File")
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded_file:
        source_tag = uploaded_file.name
        try:
            df_csv = pd.read_csv(uploaded_file)
            inserted_count = 0
            for _, row in df_csv.iterrows():
                name = row.get("name")
                if not name:
                    continue
                marks_raw = row.get("marks", "{}")
                if isinstance(marks_raw, str):
                    marks = eval(marks_raw)
                elif isinstance(marks_raw, dict):
                    marks = marks_raw
                else:
                    marks = {}
                for subject in ["Math", "Science", "English"]:
                    marks[subject] = marks.get(subject, 0)
                students.insert_one({"name": name, "marks": marks, "source": source_tag})
                inserted_count += 1
            st.success(f"✅ {inserted_count} records from {source_tag} added to database!")
        except Exception as e:
            st.error(f"❌ Error processing file: {e}")

# -----------------------
# Fetch All Sources
# -----------------------
all_data = list(students.find())
if all_data:
    sources = sorted(set(d.get("source", "manual") for d in all_data))
    selected_source = st.selectbox("📂 Select Data Source to Analyze:", options=sources)

    # Filter only selected source
    filtered_data = [d for d in all_data if d.get("source") == selected_source]

    # Normalize data
    normalized_data = []
    for d in filtered_data:
        d["_id"] = str(d["_id"])
        marks = d.get("marks", {})
        for subject in ["Math", "Science", "English"]:
            marks[subject] = marks.get(subject, 0)
        d.update(marks)
        d["average"] = round(sum(marks.values()) / 3, 2)
        normalized_data.append(d)

    df = pd.DataFrame(normalized_data)

    required_cols = ["name", "Math", "Science", "English", "average", "source"]
    if all(col in df.columns for col in required_cols):
        st.subheader(f"📋 Student Records from: {selected_source}")
        st.dataframe(df[required_cols])

        # -----------------------
        # Edit/Delete Functionality
        # -----------------------
        st.subheader("✏️ Edit or ❌ Delete Student")
        student_names = df["name"].tolist()
        selected_name = st.selectbox("Select Student", options=student_names)
        selected_student = next((s for s in normalized_data if s["name"] == selected_name), None)

        if selected_student:
            with st.form("edit_form"):
                new_name = st.text_input("Edit Name", selected_student["name"])
                new_math = st.number_input("Edit Math Marks", value=selected_student.get("Math", 0))
                new_science = st.number_input("Edit Science Marks", value=selected_student.get("Science", 0))
                new_english = st.number_input("Edit English Marks", value=selected_student.get("English", 0))

                edit_btn = st.form_submit_button("Update")

                if edit_btn:
                    new_data = {
                        "name": new_name,
                        "marks": {"Math": new_math, "Science": new_science, "English": new_english},
                        "source": selected_student.get("source", "manual")
                    }
                    students.update_one({"_id": ObjectId(selected_student["_id"])}, {"$set": new_data})
                    st.success("✅ Record updated. Please refresh.")

            if st.button("Delete Student"):
                students.delete_one({"_id": ObjectId(selected_student["_id"])})
                st.warning("⚠️ Student record deleted. Please refresh.")

        # -----------------------
        # Data Analysis
        # -----------------------
        st.subheader("📈 Data Analysis")
        all_marks = []
        for student in df[["Math", "Science", "English"]].values:
            all_marks.extend(student)

        if all_marks:
            st.write(f"**Total Students:** {len(df)}")
            st.write(f"**Average Score:** {round(sum(all_marks) / len(all_marks), 2)}")
            st.write(f"**Highest Score:** {max(all_marks)}")
            st.write(f"**Lowest Score:** {min(all_marks)}")
            top_student = df.loc[df['average'].idxmax()]
            st.write(f"**Top Scorer:** {top_student['name']} with average {top_student['average']}")

            chart_type = st.selectbox("📊 Choose Chart Type", [
                "Top N Students in Subject (Ascending)",
                "Subject-wise Highest Marks (Line Graph)",
                "Donut Chart of Subject Averages"
            ])

            if chart_type == "Top N Students in Subject (Ascending)":
                subject = st.selectbox("Choose subject", ["Math", "Science", "English"])
                top_n = st.slider("Select Top N Students", min_value=3, max_value=len(df), value=min(10, len(df)))
                sorted_df = df.sort_values(by=subject, ascending=True).tail(top_n)
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.barh(sorted_df["name"], sorted_df[subject], color='skyblue')
                ax.set_title(f"Top {top_n} Students in {subject}")
                ax.set_xlabel("Marks")
                st.pyplot(fig)

            elif chart_type == "Subject-wise Highest Marks (Line Graph)":
                subject_max = df[["Math", "Science", "English"]].max()
                fig, ax = plt.subplots()
                ax.plot(subject_max.index, subject_max.values, marker='o', linestyle='-', color='green')
                ax.set_title("📈 Highest Marks in Each Subject")
                ax.set_ylabel("Marks")
                st.pyplot(fig)

            elif chart_type == "Donut Chart of Subject Averages":
                avg_subjects = df[["Math", "Science", "English"]].mean()
                fig, ax = plt.subplots()
                wedges, texts, autotexts = ax.pie(
                    avg_subjects,
                    labels=[f"{subj}: {round(val, 1)}" for subj, val in avg_subjects.items()],
                    autopct='%1.1f%%',
                    startangle=90,
                    wedgeprops=dict(width=0.4)
                )
                ax.set_title("📊 Average Marks per Subject")
                st.pyplot(fig)

        # -----------------------
        # Export to CSV
        # -----------------------
        st.subheader("⬇️ Export Data")
        csv = df[required_cols].to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv, file_name=f"{selected_source}_records.csv", mime="text/csv")
else:
    st.info("ℹ️ No student data available. Add some records to begin.")
