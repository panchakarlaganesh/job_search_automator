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

    def header(self):
        pass # No default header

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def render_markdown(self, content):
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                self.ln(4)
                continue

            # Headers
            if line.startswith('# '):
                self.set_font('Helvetica', 'B', 16)
                self.multi_cell(0, 10, line[2:].strip())
                self.ln(2)
            elif line.startswith('## '):
                self.ln(2)
                self.set_font('Helvetica', 'B', 14)
                self.multi_cell(0, 9, line[3:].strip())
                self.ln(1)
            elif line.startswith('### '):
                self.set_font('Helvetica', 'B', 12)
                self.multi_cell(0, 8, line[4:].strip())
            # Bullet points
            elif line.startswith('- ') or line.startswith('* '):
                self.set_font('Helvetica', '', 10)
                text = line[2:].strip()
                # Handle bolding within bullets
                self._render_text_with_formatting(text, is_bullet=True)
            else:
                self.set_font('Helvetica', '', 10)
                self._render_text_with_formatting(line)

    def _render_text_with_formatting(self, text, is_bullet=False):
        """Renders text with basic markdown formatting support."""
        # Simplified: Remove bolding tags for now to ensure stable rendering
        clean_text = text.replace('**', '').strip()
        
        # Use latin-1 for FPDF compatibility
        try:
            safe_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
        except:
            safe_text = clean_text

        if is_bullet:
            # Set a temporary left margin for the bullet and its text
            orig_margin = self.l_margin
            self.set_left_margin(orig_margin + 10)
            
            # Draw the bullet symbol at the original margin position
            self.set_x(orig_margin + 5)
            self.write(6, chr(149) + " ")
            
            # Render the multi-line text (it will now wrap to the new margin)
            self.multi_cell(0, 6, safe_text)
            
            # Reset the margin
            self.set_left_margin(orig_margin)
        else:
            self.multi_cell(0, 6, safe_text)

def save_tailored_resume(job_id, content, output_dir="resumes/tailored"):
    """Saves tailored resume as MD and PDF."""
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    md_path = os.path.join(output_dir, f"{job_id}.md")
    pdf_path = os.path.join(output_dir, f"{job_id}.pdf")
    
    try:
        # Save MD
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Save PDF
        pdf = ResumePDF()
        pdf.add_page()
        pdf.render_markdown(content)
        pdf.output(pdf_path)
        
        return pdf_path
    except Exception as e:
        logger.error(f"Failed to save tailored resume {job_id}: {e}")
        return None
