import os
from fpdf import FPDF
from .logger import logger

def get_base_resumes(directory="resumes"):
    if not os.path.exists(directory):
        os.makedirs(directory)
        return []
    return [f for f in os.listdir(directory) if f.endswith(".md")]

def read_resume(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading resume {file_path}: {e}")
        return ""

def save_tailored_resume(content, job_id, output_dir="resumes/tailored"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    md_path = os.path.join(output_dir, f"{job_id}.md")
    pdf_path = os.path.join(output_dir, f"{job_id}.pdf")
    
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Simple PDF generation from text (fpdf2)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        
        # Split content by lines and add to PDF
        for line in content.split("\n"):
            # Clean non-latin characters if necessary, or just encode as latin-1 for simplicity in this MVP
            line = line.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 5, line)
            
        pdf.output(pdf_path)
        return pdf_path
    except Exception as e:
        logger.error(f"Error saving tailored resume for job {job_id}: {e}")
        return None
