# ==========================================================
# AI TEXT DETECTOR PRO — PHASE 3.5
# FILE: main_app.py (PART 1/2)
# ==========================================================

import streamlit as st
import streamlit_authenticator as stauth
import yaml
import os
from yaml.loader import SafeLoader

# --- Local Imports ---
from models import load_models
from analysis import (
    get_full_analysis,
    proofreading_suggestions,
    rewrite_text_for_human_score,
    grammar_fix_only,
    paraphrase_text
)
from utils import (
    read_file_content,
    create_docx_export,
    create_html_export,
    create_json_export,
    generate_highlighted_text_html,
    highlight_grammar_diff
)

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="AI Text Detector Pro v3.5",
    page_icon="🔍",
    layout="wide"
)

# ==========================================================
# GLOBAL CONFIG
# ==========================================================
MAX_TEXT_LENGTH = 50000
SAFE_SCORE = 70

PLANS = {
    "free": {"name": "Free", "scans_limit": 10},
    "pro": {"name": "Pro", "scans_limit": 500},
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH) as f:
    config = yaml.load(f, Loader=SafeLoader)

# ==========================================================
# HELPERS
# ==========================================================
def update_scan_count(username):
    config["credentials"]["usernames"][username]["scans_used"] += 1
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f)

def validate_text(text):
    if not text or len(text.split()) < 10:
        st.warning("Please enter at least 10 words.")
        return False
    if len(text) > MAX_TEXT_LENGTH:
        st.error("Text too long.")
        return False
    return True

# ---------- Phase 3.5 UX Helpers ----------
def score_band(score):
    if score < 40:
        return "🔴 AI-leaning", "#ffdddd"
    elif score < 60:
        return "🟡 Mixed signals", "#fff4cc"
    elif score < 80:
        return "🟢 Mostly human", "#e6ffe6"
    else:
        return "🟢🟢 Strongly human", "#ccffcc"

def expected_score_range(score):
    if score < 40:
        return "45–55%"
    elif score < 60:
        return "60–70%"
    elif score < 80:
        return "75–85%"
    else:
        return "Already optimal"

# ==========================================================
# MAIN APP
# ==========================================================
def run_app():

    # ------------------------------------------------------
    # DEV LOGIN BYPASS
    # ------------------------------------------------------
    st.session_state["authentication_status"] = True
    st.session_state["name"] = "Demo User"
    st.session_state["username"] = "demo"

    # ------------------------------------------------------
    # LOAD MODELS
    # ------------------------------------------------------
    models = load_models()
    if not models:
        st.error("Failed to load AI models.")
        st.stop()

    # ------------------------------------------------------
    # SESSION STATE
    # ------------------------------------------------------
    if "analysis_results" not in st.session_state:
        st.session_state["analysis_results"] = None
    if "current_text" not in st.session_state:
        st.session_state["current_text"] = ""
    if "previous_score" not in st.session_state:
        st.session_state["previous_score"] = None

    # ------------------------------------------------------
    # SIDEBAR
    # ------------------------------------------------------
    with st.sidebar:
        st.title(f"👋 {st.session_state['name']}")
        user = config["credentials"]["usernames"][st.session_state["username"]]
        plan = user.get("plan", "pro")
        used = user.get("scans_used", 0)
        limit = PLANS[plan]["scans_limit"]

        st.markdown(f"**Plan:** {PLANS[plan]['name']}")
        st.progress(min(used / limit, 1.0))
        st.caption(f"{used} / {limit} scans used")

    # ------------------------------------------------------
    # TITLE
    # ------------------------------------------------------
    st.title("🔍 AI Text Detector Pro v3.5")

    # ------------------------------------------------------
    # MODE
    # ------------------------------------------------------
    mode = st.radio(
        "Choose Mode",
        ["🧠 AI Detection", "✍️ Proofreading"],
        horizontal=True
    )

    # ------------------------------------------------------
    # INPUT
    # ------------------------------------------------------
    input_method = st.radio(
        "Input Method",
        ["📝 Paste Text", "📄 Upload File"],
        horizontal=True
    )

    text = ""
    if input_method == "📝 Paste Text":
        text = st.text_area("Enter text", height=260)
    else:
        uploaded = st.file_uploader("Upload (.txt, .pdf, .docx)")
        if uploaded:
            text = read_file_content(uploaded)
            st.text_area("Preview", text[:1000], height=150, disabled=True)

    # ------------------------------------------------------
    # RUN ANALYSIS
    # ------------------------------------------------------
    if st.button("Run Analysis", type="primary", use_container_width=True):

        if not validate_text(text):
            return

        api_key = config.get("openai_api_key")

        if mode == "🧠 AI Detection":
            with st.spinner("Running AI detection..."):
                res = get_full_analysis(text, models)
                st.session_state["analysis_results"] = res
                st.session_state["current_text"] = text
                st.session_state["previous_score"] = res["composite_human_score"]
                update_scan_count(st.session_state["username"])

        else:
            with st.spinner("Proofreading..."):
                revised = proofreading_suggestions(text, api_key)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("❌ Original")
                    st.error(text)
                with col2:
                    st.markdown("✅ Improved")
                    st.success(revised)
    # ======================================================
    # RESULTS (AI DETECTION)
    # ======================================================
    if st.session_state["analysis_results"] is None:
        return

    res = st.session_state["analysis_results"]
    current_text = st.session_state["current_text"]
    api_key = config.get("openai_api_key")

    st.markdown("---")

    # ------------------------------------------------------
    # TOP METRICS
    # ------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Human Score", f"{res['composite_human_score']:.1f}%")
    c2.metric("AI Probability", f"{100 - res['roberta_detection_score']:.1f}%")
    c3.metric("Complexity", f"{res['perp_overall']:.2f}")
    c4.metric("Burstiness", f"{res['burst_overall']:.2f}")

    # ------------------------------------------------------
    # OVERALL ASSESSMENT (PHASE 3.5)
    # ------------------------------------------------------
    label, bg = score_band(res["composite_human_score"])

    st.markdown(
        f"""
        <div style="background:{bg};padding:14px;border-radius:10px;margin-top:10px;">
            <b>Overall Assessment:</b> {label}
        </div>
        """,
        unsafe_allow_html=True
    )

    progress = min(res["composite_human_score"] / SAFE_SCORE, 1.0)
    st.markdown("#### 🎯 Progress toward safe human score (70%)")
    st.progress(progress)

    st.caption(
        f"{SAFE_SCORE - res['composite_human_score']:.1f}% more needed to reach the safe zone."
        if res["composite_human_score"] < SAFE_SCORE
        else "✅ You are in the safe human-written zone."
    )

    st.markdown(
        """
        **Recommended workflow:**  
        1️⃣ Improve Score → 2️⃣ Grammar → 3️⃣ Paraphrase → 4️⃣ Export
        """
    )

    # ------------------------------------------------------
    # TABS
    # ------------------------------------------------------
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["🖍️ Highlights", "✏️ Coaching", "🧠 Improve Score", "✍️ Grammar", "🔁 Paraphrase", "📥 Export"]
    )

    # ------------------------------------------------------
    # TAB 1: HIGHLIGHTS
    # ------------------------------------------------------
    with tab1:
        html = generate_highlighted_text_html(res["sentence_analysis"])
        st.markdown(html, unsafe_allow_html=True)

    # ------------------------------------------------------
    # TAB 2: COACHING
    # ------------------------------------------------------
    with tab2:
        for item in res["sentence_analysis"]:
            with st.expander(item["sentence"][:80] + "..."):
                st.write(item["sentence"])
                st.info(item["suggestion_data"]["suggestion"])

    # ------------------------------------------------------
    # TAB 3: IMPROVE SCORE
    # ------------------------------------------------------
    with tab3:
        expected = expected_score_range(res["composite_human_score"])
        st.info(f"✨ Expected score after rewrite: ~{expected}")

        intensity = st.select_slider(
            "Rewrite intensity",
            ["Conservative", "Balanced", "Aggressive"],
            value="Balanced"
        )

        if st.button("🪄 Rewrite Entire Text", use_container_width=True):
            with st.spinner("Rewriting and re-scoring..."):
                rewritten = rewrite_text_for_human_score(
                    current_text,
                    res,
                    api_key,
                    intensity=intensity
                )

                new_res = get_full_analysis(rewritten, models)
                delta = new_res["composite_human_score"] - res["composite_human_score"]

                st.session_state["analysis_results"] = new_res
                st.session_state["current_text"] = rewritten

                col1, col2 = st.columns(2)
                with col1:
                    st.error(current_text)
                with col2:
                    st.success(rewritten)

                st.metric(
                    "Human Score After Rewrite",
                    f"{new_res['composite_human_score']:.1f}%",
                    f"{delta:+.1f}"
                )

    # ------------------------------------------------------
    # TAB 4: GRAMMAR
    # ------------------------------------------------------
    with tab4:
        if res["composite_human_score"] < SAFE_SCORE:
            st.warning("Improve score before grammar.")
        else:
            if st.button("Fix Grammar", use_container_width=True):
                fixed = grammar_fix_only(current_text, api_key)
                orig_html, fixed_html = highlight_grammar_diff(current_text, fixed)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(orig_html, unsafe_allow_html=True)
                with col2:
                    st.markdown(fixed_html, unsafe_allow_html=True)

    # ------------------------------------------------------
    # TAB 5: PARAPHRASE
    # ------------------------------------------------------
    with tab5:
        if res["composite_human_score"] < SAFE_SCORE:
            st.warning("Improve score before paraphrasing.")
        else:
            mode = st.selectbox(
                "Paraphrase mode",
                ["Simplify", "Shorten", "Expand", "Formal", "Conversational"]
            )
            if st.button("Paraphrase", use_container_width=True):
                para = paraphrase_text(current_text, api_key, mode)
                col1, col2 = st.columns(2)
                with col1:
                    st.error(current_text)
                with col2:
                    st.success(para)

    # ------------------------------------------------------
    # TAB 6: EXPORT
    # ------------------------------------------------------
    with tab6:
        d1, d2, d3 = st.columns(3)
        d1.download_button("DOCX", create_docx_export(res), "analysis.docx")
        d2.download_button("HTML", create_html_export(res), "analysis.html")
        d3.download_button("JSON", create_json_export(res), "analysis.json")


if __name__ == "__main__":
    run_app()
