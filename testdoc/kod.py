from striprtf.striprtf import rtf_to_text

def convert_rtf_to_html(rtf_path):
    with open(rtf_path, 'r') as file:
        rtf_text = file.read()
    
    plain_text = rtf_to_text(rtf_text)
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    </head>
    <body>
        {content}
    </body>
    </html>
    """
    
    # Basic conversion - you'll need to add your math processing logic here
    content = plain_text.replace('\n', '<br>')
    
    return html_template.format(content=content)

# Use this instead for RTF files
html_output = convert_rtf_to_html("rtr.rtf")
with open("output.html", "w", encoding="utf-8") as f:
    f.write(html_output)