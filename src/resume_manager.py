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
        # Save the Markdown version
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Professional PDF Settings
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Standard US Letter/A4 safe margins
        margin_left = 20
        margin_right = 20
        pdf.set_left_margin(margin_left)
        pdf.set_right_margin(margin_right)
        
        # Calculate available content width (A4 is 210mm wide)
        content_width = 210 - margin_left - margin_right
        
        lines = content.split("\n")
        for line in lines:
            # Collapse multiple spaces and remove tabs to prevent floating text
            line = " ".join(line.split()).strip()
            
            # Explicitly reset X position for every line to prevent horizontal drift
            pdf.set_x(margin_left)

            if not line:
                pdf.ln(5)
                continue

            # 1. Handle Headers
            if line.startswith("# "):
                pdf.set_font("Helvetica", 'B', 16)
                clean_text = line.replace("#", "").replace("**", "").strip()
                pdf.multi_cell(0, 10, clean_text)
                pdf.ln(2)
            elif line.startswith("## "):
                pdf.set_font("Helvetica", 'B', 14)
                clean_text = line.replace("#", "").replace("**", "").strip()
                pdf.multi_cell(0, 9, clean_text)
                pdf.ln(1)
            elif line.startswith("### "):
                pdf.set_font("Helvetica", 'B', 12)
                clean_text = line.replace("#", "").replace("**", "").strip()
                pdf.multi_cell(0, 8, clean_text)
            else:
                # 2. Handle Body Text & Bullets
                # Determine if the whole line or parts of it are bold
                is_bold = "**" in line
                clean_text = line.replace("**", "").strip()
                
                # Render bullet points
                if clean_text.startswith("- "):
                    pdf.set_font("Helvetica", 'B' if is_bold else '', 10)
                    pdf.multi_cell(0, 6, f"  - {clean_text[2:]}")
                else:
                    pdf.set_font("Helvetica", 'B' if is_bold else '', 10)
                    try:
                        safe_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
                        pdf.multi_cell(0, 6, safe_text)
                    except Exception as e:
                        logger.error(f"Render error: {e}")

        # Clean and save the final PDF
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        pdf.output(pdf_path)
        
        return pdf_path
    except Exception as e:
        logger.error(f"Critical error saving PDF for job {job_id}: {e}")
        return None
