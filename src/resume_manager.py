import os
from fpdf import FPDF
from src.logger import logger

def get_base_resumes(directory="resumes"):
    if not os.path.exists(directory): os.makedirs(directory)
    return [f for f in os.listdir(directory) if f.endswith(".md")]

def read_resume(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f: return f.read()
    except Exception as e:
        logger.error(f"Error reading resume {file_path}: {e}")
        return ""

def save_tailored_resume(content, job_id, output_dir="resumes/tailored"):
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    md_path = os.path.join(output_dir, f"{job_id}.md")
    pdf_path = os.path.join(output_dir, f"{job_id}.pdf")
    try:
        with open(md_path, "w", encoding="utf-8") as f: f.write(content)
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)
        lines = content.split("\n")
        for line in lines:
            # Use 'replace' for non-latin1 characters to avoid FPDF errors
            # Also handle potential empty lines more gracefully
            try:
                clean_line = line.encode('latin-1', 'replace').decode('latin-1')
            except:
                clean_line = "[Encoding Error]"
            
            if not clean_line.strip():
                pdf.ln(5)
            else:
                # Use multi_cell for automatic wrapping
                pdf.multi_cell(190, 6, clean_line)
        
        # Ensure the output directory is clean of half-written files
        if os.path.exists(pdf_path): os.remove(pdf_path)
        pdf.output(pdf_path)
        return pdf_path
    except Exception as e:
        logger.error(f"Error saving resume: {e}")
        return None
