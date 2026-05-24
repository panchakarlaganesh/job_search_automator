import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Job, JobStatus, RunLog
from .logger import logger

st.set_page_config(page_title="Job Search Automator", layout="wide")

def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

def main():
    st.title("🎯 Job Search Automator Dashboard")
    
    db = get_db()
    if not db:
        return

    # Sidebar Stats
    st.sidebar.header("Statistics")
    total_jobs = db.query(Job).count()
    applied_jobs = db.query(Job).filter(Job.status == JobStatus.APPLIED).count()
    matching_jobs = db.query(Job).filter(Job.status == JobStatus.MATCHED).count()
    intervention_jobs = db.query(Job).filter(Job.status == JobStatus.MANUAL_INTERVENTION).count()
    
    st.sidebar.metric("Total Found", total_jobs)
    st.sidebar.metric("Applied", applied_jobs)
    st.sidebar.metric("Matched", matching_jobs)
    st.sidebar.metric("Needs Action", intervention_jobs)

    # Main Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Job Pipeline", "🤖 Run Logs", "🧠 Q&A Memory"])

    with tab1:
        st.header("Application Pipeline")
        status_filter = st.selectbox("Filter by Status", [s.value for s in JobStatus] + ["all"], index=len(JobStatus))
        
        query = db.query(Job)
        if status_filter != "all":
            query = query.filter(Job.status == JobStatus(status_filter))
        
        jobs = query.order_by(Job.created_at.desc()).all()
        
        if not jobs:
            st.info("No jobs found with the selected filter.")
        else:
            for job in jobs:
                with st.expander(f"{job.title} @ {job.company} ({job.status.value})"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Location:** {job.location}")
                        st.write(f"**Source:** {job.source}")
                        st.write(f"**Score:** {job.match_score if job.match_score else 'N/A'}")
                        st.write(f"**Reason:** {job.match_reason if job.match_reason else 'N/A'}")
                        st.write(f"[Link to Job]({job.url})")
                    
                    with col2:
                        new_status = st.selectbox("Update Status", [s.value for s in JobStatus], 
                                                index=[s.value for s in JobStatus].index(job.status.value),
                                                key=f"status_{job.id}")
                        if st.button("Save Status", key=f"btn_{job.id}"):
                            job.status = JobStatus(new_status)
                            db.commit()
                            st.success("Updated!")
                            st.rerun()

    with tab2:
        st.header("Recent Automation Runs")
        runs = db.query(RunLog).order_by(RunLog.start_time.desc()).limit(10).all()
        if runs:
            df_runs = pd.DataFrame([{
                "Start": r.start_time,
                "End": r.end_time,
                "Status": r.status,
                "Found": r.jobs_found,
                "Applied": r.jobs_applied,
                "Error": r.error_message
            } for r in runs])
            st.table(df_runs)
        else:
            st.write("No run history yet.")

    with tab3:
        st.header("Learning Mode Memory")
        st.info("This is where the bot stores answers to common application questions.")
        # Logic to view/edit QAMemory could go here

    db.close()

if __name__ == "__main__":
    main()
