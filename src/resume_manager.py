import os
import re
import json
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
        if not text: return ""
        replacements = {'\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2022': '*', '\u2026': '...'}
        for char, replacement in replacements.items(): text = text.replace(char, replacement)
        try: return text.encode('latin-1', 'replace').decode('latin-1')
        except: return "".join(i for i in text if ord(i) < 128)

    def render_markdown(self, content):
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line: self.ln(5); continue
            self.set_x(self.l_margin)
            if line.startswith('# '):
                self.set_font("Helvetica", 'B', 16); self.multi_cell(0, 10, self.safe_text(line[2:])); self.ln(2)
            elif line.startswith('## '):
                self.ln(2); self.set_font("Helvetica", 'B', 14); self.multi_cell(0, 9, self.safe_text(line[3:])); self.ln(1)
            elif line.startswith('### '):
                self.set_font("Helvetica", 'B', 12); self.multi_cell(0, 8, self.safe_text(line[4:]))
            elif line.startswith('- ') or line.startswith('* '):
                self.set_font("Helvetica", '', 10); self.set_x(self.l_margin + 5); self.write(6, chr(149))
                self.set_x(self.l_margin + 10); eff_width = self.w - self.r_margin - (self.l_margin + 10)
                self.multi_cell(eff_width, 6, self.safe_text(line[2:]))
            else:
                self.set_font("Helvetica", '', 10); text = line.replace('**', '')
                self.multi_cell(0, 6, self.safe_text(text))

def save_tailored_resume(job_id, content, output_dir="resumes/tailored"):
    """Saves tailored resume as MD and PDF, preparing for advanced HTML rendering."""
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    md_path = os.path.join(output_dir, f"{job_id}.md")
    pdf_path = os.path.join(output_dir, f"{job_id}.pdf")
    html_path = os.path.join(output_dir, f"{job_id}.html")
    
    try:
        # 1. Save MD (Raw AI output)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # 2. Prepare HTML (For high-fidelity rendering)
        # We can eventually use jinja2 here, but for now a simple string replacement
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.4; margin: 0.5in; font-size: 10pt; color: #333; }
                h1 { text-align: center; font-size: 18pt; margin-bottom: 0; }
                .contact { text-align: center; margin-bottom: 15pt; }
                h3 { border-bottom: 1px solid #000; text-transform: uppercase; margin-top: 15pt; }
                .job { margin-top: 10pt; }
                .job-header { font-weight: bold; display: flex; justify-content: space-between; }
                ul { margin-top: 2pt; padding-left: 20pt; }
                li { margin-bottom: 2pt; }
                .skills b { display: inline-block; width: 120px; }
            </style>
        </head>
        <body>
            [CONTENT]
        </body>
        </html>
        """
        # Simple markdown to HTML conversion for the preview/future-mcp
        import markdown2
        html_body = markdown2.markdown(content)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_template.replace("[CONTENT]", html_body))

        # 3. Generate PDF (Using hardened local engine)
        pdf = ResumePDF()
        pdf.add_page()
        pdf.render_markdown(content)
        pdf.output(pdf_path)
        
        return pdf_path
    except Exception as e:
        logger.error(f"Failed to save tailored resume {job_id}: {e}")
        return None

def generate_professional_pdf(job_id, html_content, output_dir="resumes/tailored"):
    """
    Placeholder for future MCP-based high-fidelity PDF generation.
    This will use the constant_quadruped/pdf-mcp-server:pdf.create_from_html tool.
    """
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    pdf_path = os.path.join(output_dir, f"{job_id}.pdf")
    # Log that we are ready for high-fidelity conversion
    logger.info(f"High-fidelity conversion requested for {job_id}. Pending MCP tool availability.")
    return None
