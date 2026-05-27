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
        
        margin = 20
        pdf.set_left_margin(margin)
        pdf.set_right_margin(margin)
        content_width = 170 # 210 - 20*2
        
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln(2) # Smaller line break
                continue

            # Section Headers
            if line.startswith("# "):
                pdf.set_font("Helvetica", 'B', 16)
                pdf.cell(0, 10, line[2:], ln=True)
            elif line.startswith("## "):
                pdf.set_font("Helvetica", 'B', 14)
                pdf.cell(0, 9, line[3:], ln=True)
            elif line.startswith("### "):
                pdf.set_font("Helvetica", 'B', 12)
                pdf.cell(0, 8, line[4:], ln=True)
            else:
                # Handle line-level bolding (e.g. **Job Title**)
                # Simple implementation: if line starts/ends with **, make whole line bold
                is_bold = False
                clean_text = line
                if line.startswith("**") and line.endswith("**"):
                    is_bold = True
                    clean_text = line.strip("*")
                
                # Check for bullet points
                if clean_text.startswith("- "):
                    clean_text = "  - " + clean_text[2:]
                
                # Render the text
                font_style = 'B' if is_bold else ''
                pdf.set_font("Helvetica", font_style, 10)
                
                # Use multi_cell to ensure it wraps correctly within the margins
                # We encode and decode to latin-1 to avoid FPDF errors with special chars
                try:
                    safe_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(content_width, 6, safe_text)
                except Exception as e:
                    logger.error(f"Text render error: {e}")
                    pdf.multi_cell(content_width, 6, "[Text Error]")
        
        if os.path.exists(pdf_path): os.remove(pdf_path)
        pdf.output(pdf_path)
        return pdf_path
    except Exception as e:
        logger.error(f"Error saving resume: {e}")
        return None
