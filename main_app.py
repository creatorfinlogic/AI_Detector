# /ai_detector_pro/main_app.py

import streamlit as st
import streamlit_authenticator as stauth
import yaml
import os
import stripe
from yaml.loader import SafeLoader

# --- Local Imports ---
from models import load_models
from analysis import get_full_analysis
from utils import (
    read_file_content, create_docx_export, create_html_export, create_json_export,
    generate_highlighted_text_html, generate_rewrite_suggestions, get_unique_key
)

# ==========================================================
# PAGE CONFIGURATION
# Must be the first Streamlit command.
# ==========================================================
st.set_page_config(
    page_title="AI Text Detector Pro",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# GLOBAL VARIABLES & MOCKS (for stability)
# ==========================================================
MAX_TEXT_LENGTH = 50000
PLANS = {
    'free': {'name': 'Free', 'scans_limit': 10},
    'pro': {'name': 'Pro', 'scans_limit': 500, 'stripe_price_id': os.environ.get("STRIPE_PRO_PRICE_ID", "price_123_mock")}
}
# Load Stripe key from environment or secrets, fallback to mock
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_mock_key")
stripe.api_key = STRIPE_SECRET_KEY

# ==========================================================
# AUTHENTICATION SETUP
# ==========================================================
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

def load_or_create_config():
    """Loads config file or creates a default one if it doesn't exist."""
    if not os.path.exists(CONFIG_PATH):
        hashed_password = stauth.Hasher().hash('demo123')
        default_config = {
            'credentials': {'usernames': {
                'demo': {
                    'email': 'demo@example.com',
                    'name': 'Demo User',
                    'password': hashed_password,
                    'plan': 'free',
                    'scans_used': 0
                }
            }},
            'cookie': {'name': 'ai_detector_cookie', 'key': 'a_secret_key', 'expiry_days': 30}
        }
        with open(CONFIG_PATH, 'w') as file:
            yaml.dump(default_config, file, default_flow_style=False)
        return default_config
    
    with open(CONFIG_PATH) as file:
        return yaml.load(file, Loader=SafeLoader)

config = load_or_create_config()

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# ==========================================================
# HELPER FUNCTIONS (SPECIFIC TO APP LOGIC)
# ==========================================================
def update_scan_count(username):
    """Increments the scan count for a user."""
    config['credentials']['usernames'][username]['scans_used'] += 1
    with open(CONFIG_PATH, 'w') as file:
        yaml.dump(config, file, default_flow_style=False)

def handle_analysis_request(text_to_analyze, models):
    """Manages the analysis process and updates session state."""
    if not text_to_analyze or len(text_to_analyze.split()) < 10:
        st.warning("Please provide at least 10 words to analyze.")
        return

    # Check if the text has changed since the last scan
    if text_to_analyze != st.session_state.get('last_scanned_text'):
        with st.spinner("Performing deep analysis..."):
            results = get_full_analysis(text_to_analyze, models)
            st.session_state['analysis_results'] = results
            st.session_state['last_scanned_text'] = text_to_analyze
            update_scan_count(st.session_state['username'])
            st.success("Analysis complete!")
    
# ==========================================================
# MAIN APPLICATION RENDER
# ==========================================================
def run_app():
    """Main function to run the Streamlit app."""
    
    # --- AUTHENTICATION FLOW ---
    authenticator.login(location='main')

    if st.session_state["authentication_status"] == False:
        st.error('Username/password is incorrect')
        st.info("**Hint:** Use `demo` and `demo123`")
    elif st.session_state["authentication_status"] == None:
        st.warning('Please enter your username and password')
        st.info("Use the sidebar to register if you are a new user.")
    
    # --- LOGGED-IN USER VIEW ---
    if st.session_state["authentication_status"]:
        render_main_app()

def render_main_app():
    """Renders the main application interface for logged-in users."""
    
    # --- Load Models ---
    models = load_models()
    if not models:
        st.error("AI models failed to load. The application cannot proceed.")
        st.stop()
        
    # --- Sidebar ---
    with st.sidebar:
        st.title(f"Welcome, {st.session_state['name']}!")
        authenticator.logout('Logout', 'sidebar')

        user_data = config['credentials']['usernames'][st.session_state['username']]
        plan = user_data.get('plan', 'free')
        scans_used = user_data.get('scans_used', 0)
        scans_limit = PLANS[plan]['scans_limit']

        st.markdown("---")
        st.markdown(f"### Plan: **{PLANS[plan]['name']}**")
        st.progress(min(scans_used / scans_limit, 1.0))
        st.caption(f"**{scans_used}** / {scans_limit} scans used")

        if plan == 'free':
            st.warning("Free plan limits apply.")
            if st.button("🚀 Upgrade to Pro", use_container_width=True):
                st.info("Pro plan integration is currently in development.")

    # --- Main App Body ---
    st.title("🔍 AI Text Detector Pro")
    
    if scans_used >= scans_limit:
        st.error(f"❌ Scan limit of {scans_limit} reached for your '{plan}' plan.")
        st.stop()

    # --- Input Area ---
    input_method = st.radio("Choose input method:", ["📝 Paste Text", "📄 Upload File"], horizontal=True)

    if input_method == "📝 Paste Text":
        text_input = st.text_area("Enter text to analyze:", height=250, key="text_area_input")
        if st.button("Analyze Text", type="primary", use_container_width=True):
            handle_analysis_request(text_input, models)
    else:
        uploaded_file = st.file_uploader("Upload a document (.txt, .pdf, .docx)", type=['txt', 'pdf', 'docx'])
        if uploaded_file:
            file_content = read_file_content(uploaded_file)
            if "ERROR:" in file_content:
                st.error(file_content)
            else:
                st.text_area("Extracted Text (preview):", value=file_content, height=250, key="file_text_area", disabled=True)
                if st.button("Analyze Uploaded File", type="primary", use_container_width=True):
                    handle_analysis_request(file_content, models)

    st.markdown("---")

    # --- Results Display ---
    if 'analysis_results' in st.session_state and st.session_state['analysis_results']:
        results = st.session_state['analysis_results']
        
        # --- Overall Scores ---
        st.subheader("📊 Overall Score")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Human-Likeness Score", f"{results['composite_human_score']:.1f}%")
        col2.metric("AI Probability (Classifier)", f"{100 - results['roberta_detection_score']:.1f}%")
        col3.metric("Text Perplexity", f"{results['perp_overall']:.2f}")
        col4.metric("Sentence Burstiness", f"{results['burst_overall']:.2f}")

        # --- Tabbed View for Details ---
        tab1, tab2, tab3 = st.tabs(["🖍️ Revision View", "✏️ Sentence Coaching", "📥 Export Results"])

        with tab1:
            st.markdown("#### Highlighted Text Analysis")
            st.caption("Sentences are color-coded based on AI-like patterns. Hover over a sentence for more details.")
            highlighted_html = generate_highlighted_text_html(results['sentence_analysis'])
            st.markdown(highlighted_html, unsafe_allow_html=True)
        
        with tab2:
            st.markdown("#### Sentence-by-Sentence Feedback")
            st.caption("Expand each sentence to get detailed feedback and rewrite suggestions.")
            for i, item in enumerate(results['sentence_analysis']):
                key = get_unique_key(item['sentence'], i)
                with st.expander(f"{item['suggestion_data']['symbol']} {item['sentence'][:80]}..."):
                    st.markdown(f"**Full Sentence:** *{item['sentence']}*")
                    st.info(f"💡 **Suggestion:** {item['suggestion_data']['suggestion']}")
                    
                    if item['flag'] not in ["HUMAN", "MIXED"]:
                        st.markdown("##### Rewrite Ideas")
                        rewrites = generate_rewrite_suggestions(item['sentence'], item['flag'])
                        for rw in rewrites:
                            st.markdown(f"**{rw['strategy']}:** `{rw['rewrite']}`")

        with tab3:
            st.markdown("#### Download Your Analysis")
            
            # --- NEW: Add try-except blocks to find hidden errors ---
            
            d_col1, d_col2, d_col3 = st.columns(3)
    
            with d_col1:
                try:
                    # This is the same logic, but now it's safely wrapped
                    if user_data.get('plan', 'free') == 'pro' or st.session_state['username'] == 'demo':
                        docx_bytes = create_docx_export(results)
                        if docx_bytes:
                            st.download_button(
                                "📄 Download DOCX", 
                                docx_bytes, 
                                "analysis.docx", 
                                key="docx_download"
                            )
                        else:
                            # This message will now appear if the function fails
                            st.warning("Could not generate DOCX file. Check terminal for warnings.")
                    else:
                        st.info("DOCX Export is a Pro feature.")
                except Exception as e:
                    st.error(f"Error in DOCX export: {e}")
    
            with d_col2:
                try:
                    html_bytes = create_html_export(results)
                    st.download_button(
                        "🌐 Download HTML", 
                        html_bytes, 
                        "analysis.html", 
                        key="html_download"
                    )
                except Exception as e:
                    st.error(f"Error in HTML export: {e}")
            
            with d_col3:
                try:
                    json_bytes = create_json_export(results)
                    st.download_button(
                        "📋 Download JSON", 
                        json_bytes, 
                        "analysis.json", 
                        key="json_download"
                    )
                except Exception as e:
                    st.error(f"Error in JSON export: {e}")


if __name__ == '__main__':
    run_app()