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
        
        # Set a safe margin and content width
        margin = 20
        pdf.set_left_margin(margin)
        pdf.set_right_margin(margin)
        content_width = 210 - (2 * margin)
        
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln(4)
                continue

            # Basic Markdown Parsing for PDF
            try:
                if line.startswith("# "):
                    pdf.set_font("Helvetica", 'B', 16)
                    clean_line = line[2:].encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(content_width, 10, clean_line)
                elif line.startswith("## "):
                    pdf.set_font("Helvetica", 'B', 14)
                    clean_line = line[3:].encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(content_width, 9, clean_line)
                elif line.startswith("### "):
                    pdf.set_font("Helvetica", 'B', 12)
                    clean_line = line[4:].encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(content_width, 8, clean_line)
                elif line.startswith("**") and line.endswith("**"):
                    pdf.set_font("Helvetica", 'B', 10)
                    clean_line = line.strip("*").encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(content_width, 6, clean_line)
                elif line.startswith("- "):
                    pdf.set_font("Helvetica", size=10)
                    clean_line = f"• {line[2:]}".encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(content_width, 6, clean_line)
                else:
                    pdf.set_font("Helvetica", size=10)
                    clean_line = line.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(content_width, 6, clean_line)
            except Exception as e:
                logger.error(f"Line render error: {e}")
                continue
        
        if os.path.exists(pdf_path): os.remove(pdf_path)
        pdf.output(pdf_path)
        return pdf_path
    except Exception as e:
        logger.error(f"Error saving resume: {e}")
        return None
