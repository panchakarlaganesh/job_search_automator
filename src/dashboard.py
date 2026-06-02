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
        st.sidebar.header("Search Settings")
        config_path = "config/search.json"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
            days_back = st.sidebar.slider("Search window (last N days)", 1, 30, config.get("days_since_posted", 7))
        else:
            days_back = 7

        status_list = [s.value for s in JobStatus] + ["all"]
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            status_filter = st.selectbox("Filter by Status", status_list, index=status_list.index("all"))
        with f_col2:
            regions = ["all"] + sorted([r[0] for r in db.query(Job.location).distinct().all() if r[0]])
            region_filter = st.selectbox("Filter by Region", regions)
        with f_col3:
            sources = ["all"] + sorted([s[0] for s in db.query(Job.source).distinct().all() if s[0]])
            source_filter = st.selectbox("Filter by Source", sources)

        # --- 2. QUERY ---
        since_date = datetime.now() - timedelta(days=days_back)
        query = db.query(Job).filter(Job.created_at >= since_date)
        if region_filter != "all": query = query.filter(Job.location == region_filter)
        if source_filter != "all": query = query.filter(Job.source == source_filter)
        if status_filter != "all": query = query.filter(Job.status == JobStatus(status_filter))

        jobs = query.order_by(Job.created_at.desc()).all()

        st.sidebar.metric("Total Found", len(jobs))

        # --- 3. UI ---
        if not jobs:
            st.info(f"No jobs found matching these filters within the last {days_back} days.")

        for job in jobs:
            with st.expander(f"{job.title} @ {job.company}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**Posted:** {job.posted_date.strftime('%Y-%m-%d') if job.posted_date else 'Unknown'} | **Location:** {job.location}")
                    
                    # --- RESUME PREVIEW & DOWNLOAD ---
                    st.divider()
                    st.subheader("Tailored Resume")
                    
                    if job.tailored_resume_path:
                        md_path = job.tailored_resume_path.replace(".pdf", ".md")
                        if os.path.exists(md_path):
                            with open(md_path, "r", encoding="utf-8") as f:
                                with st.expander("📄 View Resume Content"):
                                    st.markdown(f.read())
                        
                        if os.path.exists(job.tailored_resume_path):
                            col_dl1, col_dl2 = st.columns(2)
                            with col_dl1:
                                with open(job.tailored_resume_path, "rb") as f:
                                    st.download_button(
                                        label="💾 Download PDF",
                                        data=f,
                                        file_name=f"Resume_{job.company.replace(' ', '_')}.pdf",
                                        mime="application/pdf",
                                        key=f"dl_pdf_{job.id}",
                                    )
                            with col_dl2:
                                docx_path = job.tailored_resume_path.replace(".pdf", ".docx")
                                if os.path.exists(docx_path):
                                    with open(docx_path, "rb") as f:
                                        st.download_button(
                                            label="📝 Download DOCX",
                                            data=f,
                                            file_name=f"Resume_{job.company.replace(' ', '_')}.docx",
                                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                            key=f"dl_docx_{job.id}",
                                        )
                    else:
                        st.info("No tailored resume yet.")

                    if st.button("✨ Regenerate Tailored Resume", key=f"gen_{job.id}"):
                        progress = st.empty()
                        progress.info("Step 1/3: Reading your Apple Lead SRE resume...")
                        try:
                            from src.evaluator import tailor_resume
                            from src.resume_manager import read_resume, save_tailored_resume
                            
                            base_content = read_resume("resumes/base_resume.md")
                            if not base_content:
                                st.error("Could not find resumes/base_resume.md")
                            else:
                                progress.info("Step 2/3: AI is writing... (using local Ollama)")
                                new_content = tailor_resume(job.description, base_content)
                                if new_content and len(new_content) > 500:
                                    progress.info("Step 3/3: Finalizing PDF layout...")
                                    pdf_path = save_tailored_resume(job.id, new_content)
                                    if pdf_path:
                                        job.tailored_resume_path = pdf_path
                                        db.commit()
                                        progress.success("Finished! Open the expander above to see your tailored resume.")
                                        st.rerun()
                                    else:
                                        st.error("Failed to build PDF.")
                                else:
                                    st.error("AI returned invalid content. Check Ollama logs.")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

                    st.write(f"[Job Link]({job.url})")

                with col2:
                    new_status = st.selectbox("Status", [s.value for s in JobStatus], 
                                            index=[s.value for s in JobStatus].index(job.status.value),
                                            key=f"st_{job.id}")
                    if st.button("Update", key=f"btn_{job.id}"):
                        job.status = JobStatus(new_status)
                        db.commit()
                        st.rerun()
    finally:
        db.close()

if __name__ == "__main__":
    main()
