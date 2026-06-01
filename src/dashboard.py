import streamlit as st
import sys
import os
import json
from datetime import datetime, timedelta

# Add project root to path for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src.models import Job, JobStatus

st.set_page_config(page_title="Job Search Automator", layout="wide")


def main():
    st.title("Job Search Automator Dashboard")

    db = SessionLocal()
    try:
        # --- 1. SETTINGS & FILTERS ---

        # Sidebar: Search Window (Last N Days)
        st.sidebar.header("Search Settings")
        config_path = "config/search.json"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)

            days_back = st.sidebar.slider("Search window (last N days)", 1, 30, config.get("days_since_posted", 3))
            if days_back != config.get("days_since_posted"):
                config["days_since_posted"] = days_back
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=4)
                st.sidebar.success(f"Config updated to {days_back} days!")
        else:
            days_back = 7
            st.sidebar.warning("Config file not found.")

        # Top Filters (Jobs Tab)
        status_list = [s.value for s in JobStatus] + ["all"]
        try:
            default_index = status_list.index("review")
        except ValueError:
            default_index = len(status_list) - 1

        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            status_filter = st.selectbox("Filter by Status", status_list, index=default_index)
        with f_col2:
            regions = ["all"] + sorted([r[0] for r in db.query(Job.location).distinct().all() if r[0]])
            region_filter = st.selectbox("Filter by Region", regions)
        with f_col3:
            sources = ["all"] + sorted([s[0] for s in db.query(Job.source).distinct().all() if s[0]])
            source_filter = st.selectbox("Filter by Source", sources)
        with f_col4:
            seniorities = ["all"] + sorted([s[0] for s in db.query(Job.seniority).distinct().all() if s[0]])
            seniority_filter = st.selectbox("Filter by Seniority", seniorities)

        # --- 2. DYNAMIC QUERY BUILDING ---

        since_date = datetime.now() - timedelta(days=days_back)
        query = db.query(Job).filter(Job.created_at >= since_date)

        if region_filter != "all":
            query = query.filter(Job.location == region_filter)
        if source_filter != "all":
            query = query.filter(Job.source == source_filter)
        if seniority_filter != "all":
            query = query.filter(Job.seniority == seniority_filter)

        total_found = query.count()
        applied_count = query.filter(Job.status == JobStatus.APPLIED).count()
        ready_count = query.filter(Job.status == JobStatus.REVIEW).count()

        st.sidebar.header("Statistics (Filtered)")
        st.sidebar.metric("Total Found", total_found)
        st.sidebar.metric("Applied", applied_count)
        st.sidebar.metric("Ready for Review", ready_count)

        # --- 3. UI TABS ---

        tab1, tab2 = st.tabs(["Jobs", "Learning Mode (Q&A)"])

        with tab1:
            list_query = query
            if status_filter != "all":
                list_query = list_query.filter(Job.status == JobStatus(status_filter))

            jobs = list_query.order_by(Job.created_at.desc()).all()

            if not jobs:
                st.info(f"No jobs found matching these filters within the last {days_back} days.")

            for job in jobs:
                with st.expander(f"{job.title} @ {job.company} ({job.status.value})"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Source:** {job.source} | **Location:** {job.location}")
                        if job.salary and job.salary != "Not specified":
                            st.success(f"**Salary:** {job.salary}")
                        if job.seniority and job.seniority != "Unknown":
                            st.warning(f"**Seniority:** {job.seniority}")

                        if job.tech_stack:
                            try:
                                tools = json.loads(job.tech_stack)
                                if tools:
                                    st.write("**Tech Stack:** " + ", ".join([f"`{t}`" for t in tools]))
                            except (TypeError, ValueError):
                                pass

                        posted_str = job.posted_date.strftime("%Y-%m-%d") if job.posted_date else "Unknown"
                        st.write(f"**Posted Date:** {posted_str}")
                        st.write(f"**Match Score:** {job.match_score if job.match_score else 'N/A'}")

                        if job.match_reason:
                            st.info(f"**Reason:** {job.match_reason}")

                        if st.button("Draft Outreach Email", key=f"rec_{job.id}"):
                            primary_skill = "the field"
                            if job.tech_stack:
                                try:
                                    tools = json.loads(job.tech_stack)
                                    if tools:
                                        primary_skill = tools[0]
                                except (TypeError, ValueError):
                                    pass
                            draft = (
                                f"Subject: Application for {job.title} - [Your Name]\n\n"
                                f"Hi [Recruiter Name],\n\n"
                                f"I recently saw the {job.title} position at {job.company} and was very impressed "
                                f"by your work in {primary_skill}.\n\n"
                                f"My background matches your requirements for a {job.seniority} role. "
                                f"I've attached my tailored resume for your review.\n\n"
                                f"Best,\n[Your Name]"
                            )
                            st.text_area("Copy this draft:", draft, height=200)

                        st.write(f"[Link to Job]({job.url})")
                        if job.tailored_resume_path and os.path.exists(job.tailored_resume_path):
                            with open(job.tailored_resume_path, "rb") as f:
                                st.download_button(
                                    label="Download Tailored Resume (PDF)",
                                    data=f,
                                    file_name=f"Resume_{job.company.replace(' ', '_')}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_{job.id}",
                                )
                    with col2:
                        new_status = st.selectbox(
                            "Change Status",
                            [s.value for s in JobStatus],
                            index=[s.value for s in JobStatus].index(job.status.value),
                            key=f"st_{job.id}",
                        )
                        if st.button("Update Status", key=f"btn_{job.id}"):
                            job.status = JobStatus(new_status)
                            db.commit()
                            st.rerun()

        with tab2:
            st.subheader("Question & Answer Memory")
            from src.memory import get_all_qa, save_qa

            with st.form("new_qa_form"):
                q = st.text_area("New Question")
                a = st.text_area("Answer")
                cat = st.selectbox("Category", ["general", "experience", "technical", "personal", "salary"])
                if st.form_submit_button("Save to Memory"):
                    if q and a:
                        save_qa(q, a, cat)
                        st.success("Saved!")
                        st.rerun()

            qas = get_all_qa()
            for qa in qas:
                with st.expander(f"{qa.question[:100]}..."):
                    st.write(f"**Category:** {qa.category}")
                    st.write(f"**Answer:** {qa.answer}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
