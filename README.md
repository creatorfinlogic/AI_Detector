# AI_Detector
Write More Human -AI Text Detector Pro is a web application that provides a deep, multi-signal analysis to determine the likelihood of AI-generated content. It goes beyond a simple binary classification by offering a "Human-Likeness Score," sentence-by-sentence coaching, and specific suggestions to help writers make their text more authentic.

**Go Beyond Detection. Write More Human.**

AI Text Detector Pro is a web application built with Streamlit that provides a deep, multi-signal analysis to determine the likelihood of AI-generated content. It goes beyond a simple binary classification by offering a "Human-Likeness Score," sentence-by-sentence coaching, and specific suggestions to help writers make their text more authentic.

### ✨ Features

- **Dual-Model Analysis:** Uses GPT-2 for perplexity scoring and a RoBERTa-based classifier for AI probability.
- **Heuristic Metrics:** Incorporates burstiness, lexical diversity, and readability to create a robust score.
- **Sentence-Level Coaching:** Provides specific feedback and rewrite suggestions for each sentence.
- **Multiple Input Formats:** Supports pasted text and file uploads (.txt, .pdf, .docx).
- **Exportable Results:** Download your analysis as a DOCX, HTML, or JSON file.

### 🚀 How to Run Locally

1. Clone this repository.
2. Install the required packages: `pip install -r requirements.txt`
3. Run the app: `streamlit run main_app.py`
