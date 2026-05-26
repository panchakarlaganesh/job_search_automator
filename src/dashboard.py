import streamlit as st
import pandas as pd
import sys
import os
from sqlalchemy.orm import Session

# Add project root to path for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal, engine
from src.models import Job, JobStatus, RunLog
from src.logger import logger

st.set_page_config(page_title="Job Search Automator", layout="wide")

def main():
    st.title("🎯 Job Search Automator Dashboard")
    
    db = SessionLocal()
    try:
        # Sidebar Stats
        st.sidebar.header("Statistics")
        total_jobs = db.query(Job).count()
        applied_jobs = db.query(Job).filter(Job.status == JobStatus.APPLIED).count()
        matching_jobs = db.query(Job).filter(Job.status == JobStatus.TAILORED).count()
        
        st.sidebar.metric("Total Found", total_jobs)
        st.sidebar.metric("Applied", applied_jobs)
        st.sidebar.metric("Matched", matching_jobs)

        st.header("📋 Job Application Pipeline")
        
        tab1, tab2 = st.tabs(["Jobs", "🧠 Learning Mode (Q&A)"])
        
        with tab1:
            status_filter = st.selectbox("Filter by Status", [s.value for s in JobStatus] + ["all"], index=len(JobStatus))
            
            query = db.query(Job)
            if status_filter != "all":
                query = query.filter(Job.status == JobStatus(status_filter))
            
            jobs = query.order_by(Job.created_at.desc()).all()
            
            if not jobs:
                st.info("No jobs found for this filter.")
            
            for job in jobs:
                with st.expander(f"{job.title} @ {job.company} ({job.status.value})"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Source:** {job.source} | **Location:** {job.location}")
                        st.write(f"**Match Score:** {job.match_score if job.match_score else 'N/A'}")
                        if job.match_reason:
                            st.info(f"**Reason:** {job.match_reason}")
                        st.write(f"[Link to Job]({job.url})")
                        if job.tailored_resume_path:
                            # Adjust path for Streamlit link if necessary, for now showing literal path
                            st.success(f"📄 [Tailored Resume Available]({job.tailored_resume_path})")
                    
                    with col2:
                        new_status = st.selectbox("Change Status", [s.value for s in JobStatus], 
                                                index=[s.value for s in JobStatus].index(job.status.value),
                                                key=f"st_{job.id}")
                        if st.button("Update Status", key=f"btn_{job.id}"):
                            job.status = JobStatus(new_status)
                            db.commit()
                            st.rerun()

        with tab2:
            st.subheader("Question & Answer Memory")
            from src.memory import get_all_qa, save_qa
            
            # Form to add new Q&A
            with st.form("new_qa_form"):
                q = st.text_area("New Question")
                a = st.text_area("Answer")
                cat = st.selectbox("Category", ["general", "experience", "technical", "personal", "salary"])
                if st.form_submit_button("Save to Memory"):
                    if q and a:
                        save_qa(q, a, cat)
                        st.success("Saved!")
                        st.rerun()
            
            # List existing Q&A
            qas = get_all_qa()
            for qa in qas:
                with st.expander(f"{qa.question[:100]}..."):
                    st.write(f"**Category:** {qa.category}")
                    st.write(f"**Answer:** {qa.answer}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
