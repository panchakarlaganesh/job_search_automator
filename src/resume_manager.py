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
        # Save Markdown
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Robust PDF generation
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)
        
        # Set margins explicitly
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        
        # Split content into manageable chunks
        lines = content.split("\n")
        for line in lines:
            # Clean string for FPDF
            clean_line = line.encode('latin-1', 'replace').decode('latin-1')
            if clean_line.strip() == "":
                pdf.ln(5)
            else:
                # Use a safe width (e.g., 190mm for A4)
                pdf.multi_cell(190, 6, clean_line)
            
        pdf.output(pdf_path)
        logger.info(f"Saved tailored resume: {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.error(f"Error saving tailored resume for job {job_id}: {e}")
        return None
