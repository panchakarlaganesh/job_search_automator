import os
import re
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

class ResumePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_left_margin(20)
        self.set_right_margin(20)
        self.set_font('Helvetica', '', 10)

    def header(self): pass
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def safe_text(self, text):
        """Clean and encode text for latin-1 PDF compatibility."""
        if not text: return ""
        replacements = {
            '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
            '\u201c': '"', '\u201d': '"', '\u2022': '*', '\u2026': '...'
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        try:
            return text.encode('latin-1', 'replace').decode('latin-1')
        except:
            return "".join(i for i in text if ord(i) < 128)

    def render_markdown(self, content):
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                self.ln(5)
                continue

            # Ensure we are at the left margin before every element
            self.set_x(self.l_margin)

            # Headers
            if line.startswith('# '):
                self.set_font("Helvetica", 'B', 16)
                self.multi_cell(0, 10, self.safe_text(line[2:]))
                self.ln(2)
            elif line.startswith('## '):
                self.ln(2)
                self.set_font("Helvetica", 'B', 14)
                self.multi_cell(0, 9, self.safe_text(line[3:]))
                self.ln(1)
            elif line.startswith('### '):
                self.set_font("Helvetica", 'B', 12)
                self.multi_cell(0, 8, self.safe_text(line[4:]))
            # Bullet points
            elif line.startswith('- ') or line.startswith('* '):
                self.set_font("Helvetica", '', 10)
                # Drawing bullet manually
                self.set_x(self.l_margin + 5)
                self.write(6, chr(149))
                # Indented text
                self.set_x(self.l_margin + 10)
                # Calculate remaining width to avoid horizontal space error
                eff_width = self.w - self.r_margin - (self.l_margin + 10)
                self.multi_cell(eff_width, 6, self.safe_text(line[2:]))
            else:
                self.set_font("Helvetica", '', 10)
                # Strip internal markdown bolding for stability
                text = line.replace('**', '')
                self.multi_cell(0, 6, self.safe_text(text))

def save_tailored_resume(job_id, content, output_dir="resumes/tailored"):
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    md_path = os.path.join(output_dir, f"{job_id}.md")
    pdf_path = os.path.join(output_dir, f"{job_id}.pdf")
    try:
        with open(md_path, "w", encoding="utf-8") as f: f.write(content)
        pdf = ResumePDF()
        pdf.add_page()
        pdf.render_markdown(content)
        pdf.output(pdf_path)
        return pdf_path
    except Exception as e:
        logger.error(f"Failed to save tailored resume {job_id}: {e}")
        return None
