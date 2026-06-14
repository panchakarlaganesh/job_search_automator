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
            match_threshold = st.sidebar.slider("Min Match Percentage %", 0, 100, 0)
        else:
            days_back = 7
            match_threshold = 0

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
        
        # Apply match percentage filter
        if match_threshold > 0:
            query = query.filter(Job.match_score >= (match_threshold / 100.0))
            
        if region_filter != "all": query = query.filter(Job.location == region_filter)
        if source_filter != "all": query = query.filter(Job.source == source_filter)
        if status_filter != "all": query = query.filter(Job.status == JobStatus(status_filter))

        jobs = query.order_by(Job.created_at.desc()).all()

        st.sidebar.metric("Total Found", len(jobs))

        # --- 3. UI ---
        tab1, tab2 = st.tabs(["🎯 Jobs", "🧠 Learning Memory"])

        with tab1:
            if not jobs:
                st.info(f"No jobs found matching these filters within the last {days_back} days.")

            for job in jobs:
                with st.expander(f"{job.title} @ {job.company} ({job.status.value})"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Posted:** {job.posted_date.strftime('%Y-%m-%d') if job.posted_date else 'Unknown'} | **Location:** {job.location}")
                        
                        # --- QUICK ACTIONS ---
                        qa_col1, qa_col2, qa_col3, qa_col4 = st.columns(4)
                        if qa_col1.button("✅ Applied", key=f"qa_app_{job.id}"):
                            job.status = JobStatus.APPLIED
                            db.commit()
                            st.rerun()
                        if qa_col2.button("⏳ Hold", key=f"qa_hold_{job.id}"):
                            job.status = JobStatus.HOLD
                            db.commit()
                            st.rerun()
                        if qa_col3.button("❌ Reject", key=f"qa_rej_{job.id}"):
                            job.status = JobStatus.REJECTED
                            db.commit()
                            st.rerun()
                        if qa_col4.button("🔍 Review", key=f"qa_rev_{job.id}"):
                            job.status = JobStatus.REVIEW
                            db.commit()
                            st.rerun()

                        # --- ADVANCED MATCH ANALYTICS ---
                        if st.button("📊 Calculate Detailed Match %", key=f"eval_{job.id}"):
                            with st.spinner("Analyzing profile alignment..."):
                                from src.evaluator import evaluate_match
                                from src.resume_manager import read_resume
                                base_content = read_resume("resumes/base_resume.md")
                                analysis = evaluate_match(job.description, base_content)
                                
                                if analysis:
                                    score = analysis.get("score", 0.0)
                                    st.metric("Overall Match", f"{int(score * 100)}%")
                                    
                                    breakdown = analysis.get("breakdown", {})
                                    b_col1, b_col2, b_col3 = st.columns(3)
                                    b_col1.write(f"**Tech:** {breakdown.get('technical', 'N/A')}")
                                    b_col2.write(f"**Seniority:** {breakdown.get('seniority', 'N/A')}")
                                    b_col3.write(f"**Domain:** {breakdown.get('domain', 'N/A')}")
                                    
                                    if analysis.get("missing_critical_keywords"):
                                        st.warning(f"**Missing Keywords:** {', '.join(analysis['missing_critical_keywords'])}")
                                    
                                    st.info(f"**Expert Insight:** {analysis.get('reason', 'Analysis complete.')}")

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
                            try:
                                from src.evaluator import tailor_resume
                                from src.resume_manager import read_resume, save_tailored_resume, select_best_base_resume
                                
                                progress.info("🔍 Selecting best base resume for this role...")
                                base_resume_path = select_best_base_resume(job.title, job.description)
                                
                                if not base_resume_path:
                                    st.error("Could not find any base resumes in resumes/ directory.")
                                else:
                                    progress.info(f"📄 Using base resume: {os.path.basename(base_resume_path)}")
                                    base_content = read_resume(base_resume_path)
                                    
                                    progress.warning("⏳ Step 2/3: AI is identifying missing skills and generating new pointers... (1-2 mins)")
                                    new_content = tailor_resume(job.description, base_content)
                                    
                                    if new_content and len(new_content) > 1000:
                                        progress.info("🎨 Step 3/3: Finalizing PDF and DOCX layouts...")
                                        
                                        # Add Targeting Notes like job-application-agent
                                        targeting_notes = f"""## Targeting Notes
Role: {job.title}
Company: {job.company}
Match Score: {int((job.match_score or 0) * 100)}%

---

"""
                                        final_content = targeting_notes + new_content
                                        pdf_path = save_tailored_resume(job.id, final_content)
                                        
                                        if pdf_path:
                                            job.tailored_resume_path = pdf_path
                                            db.commit()
                                            progress.success("✅ Success! Your tailored resume is ready.")
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to build PDF/DOCX.")
                                    else:
                                        st.error("❌ AI returned invalid content.")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")

                        st.write(f"[Job Link]({job.url})")

                    with col2:
                        new_status = st.selectbox("Status", [s.value for s in JobStatus], 
                                                index=[s.value for s in JobStatus].index(job.status.value),
                                                key=f"st_{job.id}")
                        if st.button("Update", key=f"btn_{job.id}"):
                            job.status = JobStatus(new_status)
                            db.commit()
                            st.rerun()

        with tab2:
            st.header("🧠 Interview & Application Q&A")
            
            from src.memory import save_qa, get_all_qa
            
            with st.form("new_memory"):
                st.subheader("Add New Memory")
                q = st.text_area("Question")
                a = st.text_area("Saved Answer")
                c = st.text_input("Category", value="General")
                if st.form_submit_button("Save to Memory"):
                    if q and a:
                        save_qa(q, a, c)
                        st.success("Memory saved!")
                        st.rerun()
                    else:
                        st.error("Question and Answer are required.")

            st.divider()
            st.subheader("Stored Memories")
            memories = get_all_qa()
            if not memories:
                st.info("No memories saved yet.")
            else:
                for mem in memories:
                    with st.expander(f"**{mem.category}:** {mem.question}"):
                        st.write(mem.answer)
                        st.caption(f"Saved on {mem.created_at.strftime('%Y-%m-%d')}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
