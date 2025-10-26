"""
Helper functions module.

Example utility functions can be housed here.
"""

# /ai_detector_pro/utils.py

import io, re, json, fitz, hashlib
from datetime import datetime

# --- DOCX IMPORTS ---
DOCX_AVAILABLE = False
try:
    import docx
    from docx.oxml import parse_xml
    DOCX_AVAILABLE = True
except ImportError:
    print("Warning: python-docx is not installed. DOCX export will be disabled.")


# ==========================================================
# SECTION 1: FILE READING UTILITIES
# ==========================================================

def read_file_content(uploaded_file):
    """Reads content from an uploaded file (txt, pdf, docx)."""
    try:
        uploaded_file.seek(0)
        file_extension = uploaded_file.name.split('.')[-1].lower()
        file_bytes = uploaded_file.read()

        if file_extension in ['txt', 'md']:
            return file_bytes.decode('utf-8')

        elif file_extension == 'docx':
            if not DOCX_AVAILABLE:
                return "ERROR: python-docx library is not available for DOCX processing."
            document = docx.Document(io.BytesIO(file_bytes))
            return '\n'.join([paragraph.text for paragraph in document.paragraphs])

        elif file_extension == 'pdf':
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                text = "".join(page.get_text("text") for page in doc)
                return text.strip() if text.strip() else "ERROR: PDF contains no extractable text."

        return "ERROR: Unsupported file type."
    except Exception as e:
        return f"ERROR: Could not read file. Details: {str(e)}"

# ==========================================================
# SECTION 2: EXPORT GENERATION
# ==========================================================

def create_docx_export(results):
    """
    Generates a DOCX file with highlighted analysis results using a stable table-based method.
    """
    if not DOCX_AVAILABLE:
        return None

    try:
        document = docx.Document()
        color_map = {
            "AI_VERY_PREDICTABLE": 'FFDDDD', "AI_PREDICTABLE": 'FFF0CC', "UNIFORM_RHYTHM": 'FFFFCC',
            "BOILERPLATE": 'E0E0FF', "LOW_DIVERSITY": 'CCEFFF', "MIXED": 'CCFFCC', "HUMAN": 'FFFFFF'
        }

        # --- Document Header ---
        document.add_heading('AI Analysis Report', 0)
        document.add_paragraph(f"Overall Human-Likeness Score: {results['composite_human_score']}%")
        document.add_paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        document.add_heading('Sentence Analysis', 1)

        # --- Create a Table for Stability ---
        table = document.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        
        # --- Table Header ---
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Flag'
        hdr_cells[1].text = 'Sentence'

        # --- Populate Table with Sentences and Shading ---
        for item in results['sentence_analysis']:
            row_cells = table.add_row().cells
            
            # Column 1: The flag/suggestion short name
            row_cells[0].text = f"{item['suggestion_data']['symbol']} {item['suggestion_data']['short']}"
            
            # Column 2: The sentence
            row_cells[1].text = item['sentence']
            
            # Apply shading to the sentence cell
            flag = item['flag']
            hex_color = color_map.get(flag, "FFFFFF") # Default to white
            
            # This is the stable way to shade a table cell
            shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(
                'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"',
                hex_color
            ))
            row_cells[1]._tc.get_or_add_tcPr().append(shading_elm)

        # --- Save to Memory ---
        doc_io = io.BytesIO()
        document.save(doc_io)
        doc_io.seek(0)
        return doc_io.read()

    except Exception as e:
        # This will print the exact error to your terminal if it still fails
        print(f"ERROR creating DOCX file: {e}")
        return None

def create_html_export(results):
    """Generates a simple HTML report of the analysis."""
    color_map = {"AI_VERY_PREDICTABLE": "#ffdcdc", "AI_PREDICTABLE": "#fff0cc", "UNIFORM_RHYTHM": "#ffffcc", "BOILERPLATE": "#f0f0ff", "LOW_DIVERSITY": "#cceeff", "MIXED": "#ccffcc", "HUMAN": "#f0fff0"}
    html_content = f"""
    <html>
    <head><title>AI Analysis Report</title></head>
    <body>
        <h1>AI Analysis Report</h1>
        <p><b>Overall Human-Likeness Score:</b> {results['composite_human_score']}%</p>
        <p><b>Analysis Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        <h2>Highlighted Text</h2>
        <div style="font-size: 1.1em; line-height: 2.0; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px;">
    """
    for item in results['sentence_analysis']:
        color = color_map.get(item['flag'], "#ffffff")
        tooltip = f"{item['suggestion_data']['short']} (Perplexity: {item['perplexity']:.1f})"
        html_content += f'<span style="background-color: {color}; padding: 3px 5px; border-radius: 4px;" title="{tooltip}">{item["sentence"]}</span> '

    html_content += "</div></body></html>"
    return html_content.encode('utf-8')

def create_json_export(results):
    """Generates a JSON file with detailed analysis results."""
    export_data = {
        'metadata': {
            'report_date': datetime.now().isoformat(),
            'human_score': results['composite_human_score'],
        },
        'metrics': {k: results[k] for k in ['perp_overall', 'burst_overall', 'diversity_overall', 'roberta_detection_score']},
        'sentences': results['sentence_analysis']
    }
    return json.dumps(export_data, indent=2).encode('utf-8')


# ==========================================================
# SECTION 3: UI & TEXT HELPERS
# ==========================================================

def generate_highlighted_text_html(sentence_data):
    """Creates an HTML string with color-coded sentences for Streamlit display."""
    color_map = {"AI_VERY_PREDICTABLE": "#ffdcdc", "AI_PREDICTABLE": "#fff0cc", "UNIFORM_RHYTHM": "#ffffcc", "BOILERPLATE": "#f0f0ff", "LOW_DIVERSITY": "#cceeff", "MIXED": "#ccffcc", "HUMAN": "transparent"}
    html_pieces = []
    for item in sentence_data:
        flag = item['flag']
        color = color_map.get(flag, "#ffffff")
        tooltip = f"{item['suggestion_data']['short']} (Perplexity: {item['perplexity']:.1f})"
        html_pieces.append(f'<span style="background-color: {color}; padding: 3px 5px; border-radius: 4px; margin: 2px; display: inline-block;" title="{tooltip}">{item["sentence"]}</span>')
    return f'<div style="font-size: 1.1em; line-height: 2.0; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px;">{" ".join(html_pieces)}</div>'


def generate_rewrite_suggestions(sentence, flag):
    """Generates rewrite ideas based on the sentence flag."""
    rewrites = []
    def strip_trailing_punct(s): return re.sub(r'[.?!]+$', '', s)

    if flag in ["AI_VERY_PREDICTABLE", "AI_PREDICTABLE"]:
        rewrites.append({"strategy": "Add concrete details", "rewrite": f"[Add a specific example or number here] {sentence}"})
        rewrites.append({"strategy": "Make it personal", "rewrite": f"In my experience, {sentence.lower()}"})
        stripped = strip_trailing_punct(sentence)
        rewrites.append({"strategy": "Add a surprise element", "rewrite": f"{stripped}—but the surprising part is [add unexpected insight]."})
    elif flag == "UNIFORM_RHYTHM":
        rewrites.append({"strategy": "Vary sentence structure", "rewrite": f"Consider breaking this into a shorter and a longer sentence to create a more dynamic rhythm."})
    elif flag == "BOILERPLATE":
        cleaned = re.sub(r'^(In conclusion|Furthermore|Moreover|Thus|Hence)[,\s]+', '', sentence, flags=re.IGNORECASE)
        rewrites.append({"strategy": "Remove formal opener", "rewrite": cleaned})
    elif flag == "LOW_DIVERSITY":
        rewrites.append({"strategy": "Replace repeated words", "rewrite": "[Identify repeated words and use synonyms like: crucial, vital, pivotal, essential]"})
    else:
        rewrites.append({"strategy": "Already strong", "rewrite": "This sentence is well-written and appears authentic."})

    return rewrites

def get_unique_key(element, idx):
    """Generates a stable, unique key for Streamlit widgets in loops."""
    return hashlib.md5(f"{element}-{idx}".encode()).hexdigest()