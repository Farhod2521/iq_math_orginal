from docx import Document
import re

def escape_latex(text):
    """Escape special LaTeX characters in text"""
    special_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}',
        '\n': ' \\\\ '
    }
    for char, escape in special_chars.items():
        text = text.replace(char, escape)
    return text

def convert_math_expressions(text):
    """Convert simple fractions and math expressions to LaTeX format"""
    # Convert fractions like 3/7 to \frac{3}{7}
    text = re.sub(r'(\d+)/(\d+)', r'\\frac{\1}{\2}', text)
    # Convert mixed numbers like 1 3/32 to 1\frac{3}{32}
    text = re.sub(r'(\d+)\s+(\d+)/(\d+)', r'\1\\frac{\2}{\3}', text)
    return text

def docx_to_latex_table(docx_file, latex_file):
    """
    Convert Word tables containing math problems to LaTeX format
    
    :param docx_file: Input DOCX filename
    :param latex_file: Output LaTeX filename
    """
    doc = Document(docx_file)
    
    with open(latex_file, 'w', encoding='utf-8') as f:
        # LaTeX document preamble
        f.write("\\documentclass{article}\n")
        f.write("\\usepackage[utf8]{inputenc}\n")
        f.write("\\usepackage[T1]{fontenc}\n")
        f.write("\\usepackage[russian, english, uzbek]{babel}\n")
        f.write("\\usepackage{amsmath} % For math symbols\n")
        f.write("\\usepackage{array} % For better table formatting\n")
        f.write("\\usepackage{booktabs} % For professional tables\n\n")
        f.write("\\begin{document}\n\n")
        
        # Process each table in the document
        for table in doc.tables:
            f.write("\\begin{table}[h]\n")
            f.write("\\centering\n")
            f.write("\\begin{tabular}{|" + "l|" * len(table.columns) + "}\n")
            f.write("\\hline\n")
            
            for i, row in enumerate(table.rows):
                row_data = []
                for cell in row.cells:
                    text = cell.text.strip()
                    # Escape LaTeX special characters
                    text = escape_latex(text)
                    # Convert math expressions
                    text = convert_math_expressions(text)
                    row_data.append(text)
                
                # Join cells with & and end with \\
                f.write(" & ".join(row_data) + " \\\\\n")
                
                # Add horizontal line after header row
                if i == 0:
                    f.write("\\hline\n")
                
            f.write("\\hline\n")
            f.write("\\end{tabular}\n")
            f.write("\\end{table}\n\n")
        
        f.write("\\end{document}\n")

if __name__ == "__main__":
    input_file = "5.docx"  # Input DOCX file
    output_file = "math_problems.tex"  # Output LaTeX file
    
    docx_to_latex_table(input_file, output_file)
    print(f"Conversion complete: {input_file} → {output_file}")