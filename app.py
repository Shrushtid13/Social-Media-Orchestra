# app.py
import sys
import io

# ── Fix Windows Unicode/Emoji encoding error ──────────────────
# Windows terminal defaults to cp1252 which can't print emojis.
# Force UTF-8 so graph node print() calls with emoji don't crash.
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import streamlit as st
import uuid
import os
from dotenv import load_dotenv
from langgraph.types import Command

load_dotenv()

from graph import graph

def _save_upload(uploaded_file, platform: str) -> str:
    """Saves Streamlit uploaded file to disk. Returns path."""

    save_dir = "uploads"
    os.makedirs(save_dir, exist_ok=True)

    filename = f"{platform}_{uploaded_file.name}"
    filepath = os.path.join(save_dir, filename)

    with open(filepath, "wb") as f:
        f.write(uploaded_file.read())

    return filepath


def _find_image_for_platform(state: dict, platform: str) -> str | None:
    """Retrieves the specific image path from the graph state for a platform."""
    
    # Prioritize the path directly returned by the format_and_post node
    proj_results = state.get("platform_results", {}).get(platform, {})
    if "image_path" in proj_results:
        return proj_results["image_path"]
        
    # Fallback to image_settings if not in results yet
    image_settings = state.get("image_settings", {})
    settings       = image_settings.get(platform, {})
    mode           = settings.get("mode", "none")

    if mode == "upload":
        return settings.get("uploaded_path")
        
    return None


def _reset_session():
    """Clears all session state to start fresh."""

    for key in [
        "thread_id", "phase", "graph_result",
        "image_choices", "review_data",
        "input_data", "decision"
    ]:
        if key in st.session_state:
            del st.session_state[key]

    st.session_state.phase         = "input"
    st.session_state.image_choices = {}


def _build_summary_text(result: dict) -> str:
    """Builds a plain text summary for copying."""

    lines   = ["SOCIAL MEDIA POST SUMMARY", "=" * 40]
    summary = result.get("aggregator_summary", {})
    posts   = result.get("formatted_posts",   {})

    for platform, post_result in summary.get("successes", {}).items():
        lines.append(f"\n{platform.upper()}")
        lines.append(f"URL: {post_result.get('url', 'N/A')}")
        lines.append(f"Post: {posts.get(platform, '')[:200]}")

    return "\n".join(lines)

# # ── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Social Media Pro Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

    /* Global Foundation - Light Theme */
    .main {
        background-color: #f8fafc;
    }
    
    [data-testid="stAppViewContainer"] {
        background-color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }

    [data-testid="stHeader"] {
        background-color: rgba(248, 250, 252, 0.8);
        backdrop-filter: blur(10px);
    }

    /* Sidebar - Crisp White SaaS look */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    
    [data-testid="stSidebarContent"] {
        padding-top: 2rem;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: #0f172a !important;
        font-family: 'Lexend', sans-serif;
    }

    /* Targeted Typography - No more overlapping icons */
    h1, h2, h3, .main-title, .st-card h3, .st-card p {
        font-family: 'Lexend', sans-serif !important;
        color: #0f172a !important;
    }

    p, li, .stMarkdown p {
        font-family: 'Inter', sans-serif !important;
        color: #475569 !important;
    }

    .main-title {
        font-size: 3.2rem !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        letter-spacing: -0.04em !important;
        margin-bottom: 0px !important;
    }

    /* SaaS Card System */
    .st-card {
        background: #ffffff;
        border: 1px solid #f1f5f9;
        border-radius: 24px;
        padding: 35px;
        margin-bottom: 30px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    
    .st-card:hover {
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
    }

    .section-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 2rem;
        margin-bottom: 1.5rem;
    }

    .section-header h3 {
        margin: 0 !important;
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        color: #1e293b !important;
    }

    /* Buttons - Lumina Style */
    .stButton > button {
        border-radius: 14px !important;
        padding: 14px 28px !important;
        font-family: 'Lexend', sans-serif !important;
        font-weight: 600 !important;
        border: none !important;
    }

    .stButton > button[kind="primary"] {
        background: #f97316 !important;
        color: white !important;
        font-weight: 800 !important;
        font-size: 1.1rem !important;
        box-shadow: 0 4px 14px rgba(249, 115, 22, 0.3) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .stButton > button[kind="primary"]:hover {
        background: #ea580c !important;
        box-shadow: 0 6px 20px rgba(249, 115, 22, 0.5) !important;
        transform: translateY(-2px);
    }
    
    .stButton > button[kind="secondary"] {
        background: #f1f5f9 !important;
        color: #475569 !important;
    }

    /* Input Fields */
    .stTextArea textarea, .stTextInput input, .stSelectbox select {
        background-color: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        color: #0f172a !important;
    }
    
    .stTextArea textarea:focus {
        border-color: #6366f1 !important;
        background-color: #ffffff !important;
    }

    /* Status Badges */
    .status-badge {
        background: #e0e7ff;
        color: #4338ca;
        padding: 6px 14px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }

    .error-badge {
        background: #fee2e2;
        color: #b91c1c;
        padding: 6px 14px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
    }

    /* Metrics Styling */
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #f1f5f9;
        padding: 20px;
        border-radius: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }

    [data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 800 !important;
    }

    /* Expander Header Polish */
    .stExpander details summary p {
        font-family: 'Lexend', sans-serif !important;
        font-weight: 600 !important;
        color: #0f172a !important;
    }

    [data-testid="stExpander"] {
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        background-color: #ffffff !important;
        margin-bottom: 10px !important;
    }

    /* Platform Grid Cards (Review screen) */
    .platform-container {
        border-top: 4px solid #6366f1;
        background: #ffffff;
        padding: 24px;
        border-radius: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.04);
        margin-bottom: 20px;
    }

</style>
""", unsafe_allow_html=True)

# ── Sidebar Settings ──────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🤖 Engine Configuration")
    llm_name = st.selectbox(
        "Model Selection",
        options=["mistral-large", "mistral-small", "mistral-nemo"]
    )
    temperature = st.slider("Creativity", 0.0, 1.0, 0.7, 0.1)
    
    st.markdown("---")
    if st.button("Start Over / Reset App", type="secondary", use_container_width=True):
        _reset_session()
        st.rerun()

# ── Session State Init ────────────────────────────────────────
for key in ["thread_id", "graph_result", "review_data"]:
    if key not in st.session_state:
        st.session_state[key] = None

if "phase" not in st.session_state:
    st.session_state.phase = "input"

if "image_choices" not in st.session_state:
    st.session_state.image_choices = {}

# ── Main Header ───────────────────────────────────────────────
st.markdown('<div style="margin-top: 1rem; margin-bottom: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 1.5rem;">', unsafe_allow_html=True)
st.markdown('<h1 class="main-title">Campaign Intelligence</h1>', unsafe_allow_html=True)
st.markdown('<p style="color: #64748b; font-size: 1.1rem; margin-top: 0.5rem;">Orchestrate your cross-platform content with AI-driven automated workflows.</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# PHASE 1: INPUT FORM
# ══════════════════════════════════════════════════════════════

if st.session_state.phase == "input":
    
    # ── Section A: Strategy ──
    st.markdown('<div class="section-header"><h3>Core Strategy</h3></div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns([2.5, 1.5], gap="large")
    with c1:
        topic = st.text_area(
            "Campaign Narrative / Objectives",
            placeholder="Describe the primary message or goal of this content cycle...",
            height=160
        )
    with c2:
        brand_voice = st.selectbox(
            "Intelligence Tone",
            options=["professional", "casual & friendly", "witty & humorous", "inspirational", "educational"]
        )
        posting_mode = st.radio(
            "Orchestration Mode",
            options=["simultaneous", "single"],
            format_func=lambda x: "Cross-Platform Sync" if x == "simultaneous" else "Linear Priority"
        )
    
    st.markdown('<hr style="border: 0.5px solid #f1f5f9; margin: 2rem 0;">', unsafe_allow_html=True)

    # ── Section B: Channels ──
    st.markdown('<div class="section-header"><h3>Deployment Nodes</h3></div>', unsafe_allow_html=True)
    
    ch_col1, ch_col2, ch_col3, ch_col4 = st.columns(4)
    with ch_col1: twitter   = st.checkbox("🐦 Twitter / X", value=True)
    with ch_col2: instagram = st.checkbox("📸 Instagram",  value=True)
    with ch_col3: linkedin  = st.checkbox("💼 LinkedIn",   value=True)
    with ch_col4: facebook  = st.checkbox("👥 Facebook",   value=True)
    
    selected_platforms = []
    if twitter:   selected_platforms.append("twitter")
    if instagram: selected_platforms.append("instagram")
    if linkedin:  selected_platforms.append("linkedin")
    if facebook:  selected_platforms.append("facebook")

    st.markdown('<hr style="border: 0.5px solid #f1f5f9; margin: 2rem 0;">', unsafe_allow_html=True)

    # ── Section C: Media Configuration ──
    if selected_platforms:
        st.markdown('<div class="section-header"><h3>Visual Asset Matrix</h3></div>', unsafe_allow_html=True)
        st.caption("Define the creative parameters for individual generation sub-tasks.")
        
        image_settings = {}
        # ...
        # Platform expanders for clean UI
        for plat in selected_platforms:
            with st.expander(f"Media for {plat.upper()}", expanded=True):
                m_col1, m_col2 = st.columns(2)
                with m_col1:
                    mode = st.radio(
                        f"Asset for {plat}",
                        options=["none", "generate", "upload", "both"],
                        horizontal=True,
                        key=f"mode_{plat}"
                    )
                plat_set = {"mode": mode}
                
                with m_col2:
                    if mode in ["generate", "both"]:
                        plat_set["style"] = st.selectbox("AI Style", ["realistic", "cinematic", "illustration", "minimalist"], key=f"sty_{plat}")
                    if mode in ["upload", "both"]:
                        up_file = st.file_uploader("Upload", type=["png", "jpg"], key=f"uo_{plat}")
                        if up_file: plat_set["uploaded_path"] = _save_upload(up_file, plat)
                
                image_settings[plat] = plat_set
        st.markdown('<hr style="border: 0.5px solid #f1f5f9; margin: 2rem 0;">', unsafe_allow_html=True)

        # ── Step 4: Finalize ──
        if st.button("ORCHESTRATE CAMPAIGN →", type="primary", use_container_width=True, disabled=not topic):
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.phase     = "running"
            st.session_state.input_data = {
                "topic": topic, "brand_voice": brand_voice, "target_platforms": selected_platforms,
                "posting_mode": posting_mode, "llm_name": llm_name, "temperature": temperature,
                "image_settings": image_settings,
            }
            st.rerun()
    else:
        st.error("Please select at least one social channel above.")


# ══════════════════════════════════════════════════════════════
# PHASE 2: RUNNING
# ══════════════════════════════════════════════════════════════

elif st.session_state.phase == "running":
    st.markdown('<div class="st-card" style="text-align: center; padding: 3rem;">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Engine is processing...")
    st.markdown("Mistral AI is crafting your multi-platform strategy.")
    
    progress_bar = st.progress(0)
    status_text  = st.empty()
    data = st.session_state.input_data

    try:
        status_text.markdown("*Initializing AI chains...*")
        progress_bar.progress(20)
        
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        graph.invoke({
            "llm_name": data["llm_name"], "temperature": data["temperature"], "llm": None,
            "topic": data["topic"], "brand_voice": data["brand_voice"], "target_platforms": data["target_platforms"],
            "posting_mode": data["posting_mode"], "image_settings": data["image_settings"],
            "image_candidates": {}, "chosen_images": {}, "raw_content": "", "formatted_posts": {},
            "platform_results": {}, "human_decision": "", "revision_notes": "", "review_count": 0,
            "errors": [], "current_platform": "", "aggregator_summary": {}
        }, config)

        progress_bar.progress(100)
        st.session_state.review_data = graph.get_state(config).values
        st.session_state.phase = "review"
        st.rerun()
    except Exception as e:
        st.error(f"Execution Error: {str(e)}")
        if st.button("← Back to Strategy"):
            st.session_state.phase = "input"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# PHASE 3: HUMAN REVIEW
# ══════════════════════════════════════════════════════════════

elif st.session_state.phase == "review":
    st.markdown('<div style="text-align: center; margin-bottom: 4rem;">', unsafe_allow_html=True)
    st.markdown('<p style="color: #6366f1; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;">Verification phase</p>', unsafe_allow_html=True)
    st.markdown("### 🔍 Strategic Review")
    st.markdown('<p style="color: #94a3b8;">Review and finalize intelligence output before worldwide deployment.</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    state = st.session_state.review_data
    formatted_posts = state.get("formatted_posts", {})
    image_candidates = state.get("image_candidates", {})

    for platform, caption in formatted_posts.items():
        st.markdown(f'<div class="platform-container">', unsafe_allow_html=True)
        st.markdown(f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">'
                    f'<h3 style="margin:0;">{platform.upper()}</h3>'
                    f'<span class="status-badge">ORCHESTRATION READY</span>'
                    f'</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns([1.3, 0.7], gap="large")
        with c1:
            st.markdown('<p style="font-size: 0.8rem; font-weight: 700; color: #64748b; margin-bottom: 0.5rem; text-transform: uppercase;">Generated Narrative</p>', unsafe_allow_html=True)
            st.text_area("Caption", value=caption, height=280, disabled=True, key=f"cp_{platform}", label_visibility="collapsed")
        with c2:
            st.markdown('<p style="font-size: 0.8rem; font-weight: 700; color: #64748b; margin-bottom: 0.5rem; text-transform: uppercase;">Visual Intelligence</p>', unsafe_allow_html=True)
            
            # Check for error result (e.g. image generation failed)
            plat_res = state.get("platform_results", {}).get(platform, {})
            error_status = plat_res.get("error", "")

            if "Image generation limit is over" in error_status:
                st.markdown('<div class="error-badge">LIMIT EXCEEDED</div>', unsafe_allow_html=True)
                st.error("Image generation limit is over")
            
            elif platform in image_candidates:
                choice = st.radio("Asset Revision", ["generated", "uploaded"], key=f"ch_{platform}", horizontal=True)
                st.session_state.image_choices[platform] = choice
                st.image(image_candidates[platform][choice], use_container_width=True)
            else:
                img_path = _find_image_for_platform(state, platform)
                if img_path and os.path.exists(img_path): 
                    st.image(img_path, use_container_width=True)
                else: 
                    st.info("Text-optimized dispatch")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Final Action ──
    st.markdown('<div class="st-card" style="border-top: 4px solid #6366f1;">', unsafe_allow_html=True)
    d_col1, d_col2 = st.columns([2, 1])
    with d_col1:
        decision = st.radio("Action", ["approve", "revise", "reject"], format_func=lambda x: x.capitalize(), horizontal=True)
        notes = ""
        if decision == "revise":
            notes = st.text_area("Revision Notes", placeholder="e.g. Use more emojis...")
    with d_col2:
        if st.button("CONFIRM ACTION →", type="primary", use_container_width=True):
            st.session_state.phase = "publishing"; st.session_state.decision = {"action": decision, "notes": notes, "image_choices": st.session_state.image_choices}
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# PHASE 4: PUBLISHING
# ══════════════════════════════════════════════════════════════

elif st.session_state.phase == "publishing":
    decision = st.session_state.decision

    if decision["action"] == "reject":
        st.error("❌ Workflow cancelled.")
        if st.button("← Start New Post", type="primary"):
            _reset_session()
            st.rerun()
    else:
        with st.spinner("🚀 Publishing your posts... Please wait."):
            try:
                config = {"configurable": {"thread_id": st.session_state.thread_id}}

                # NOTE: Do NOT call graph.update_state() here.
                # LangGraph's MemorySaver already holds the full state (including
                # platform_results from format_and_post) across the interrupt.
                # Calling update_state() would overwrite those results with empty dicts.
                result = graph.invoke(Command(resume=decision), config)

                if decision["action"] == "revise":
                    st.session_state.review_data   = graph.get_state(config).values
                    st.session_state.phase         = "review"
                    st.session_state.image_choices = {}
                else:
                    st.session_state.graph_result = result
                    st.session_state.phase        = "done"
                st.rerun()

            except Exception as e:
                st.error(f"❌ Publishing Error: {e}")
                st.caption("Check the terminal for the full error traceback.")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("← Try Again", use_container_width=True):
                        st.session_state.phase = "review"
                        st.rerun()
                with col2:
                    if st.button("Start Over", use_container_width=True):
                        _reset_session()
                        st.rerun()


# ══════════════════════════════════════════════════════════════
# PHASE 5: DONE
# ══════════════════════════════════════════════════════════════

elif st.session_state.phase == "done":
    st.markdown('<div style="text-align: center; margin-bottom: 3rem;">', unsafe_allow_html=True)
    st.markdown('<p style="color: #6366f1; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;">Success</p>', unsafe_allow_html=True)
    st.markdown("### 📊 Distribution Intelligence")
    st.markdown('</div>', unsafe_allow_html=True)
    
    res = st.session_state.graph_result
    summ = res.get("aggregator_summary", {})
    
    # Metrics Row
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Total Nodes", summ.get("total", 0))
    with m2: st.metric("Success Rate", f"{(summ.get('succeeded', 0)/summ.get('total', 1))*100:.0f}%")
    with m3: st.metric("Active Deployments", summ.get("succeeded", 0))
    
    st.markdown("<br>", unsafe_allow_html=True)

    for plat, p_res in summ.get("successes", {}).items():
        st.markdown(f'<div class="platform-card">', unsafe_allow_html=True)
        st.markdown(f"#### {plat.upper()}")
        st.markdown(f'<div class="status-pill">✓ Published</div>', unsafe_allow_html=True)
        st.markdown(f'<p style="margin-top: 10px; color: #94a3b8; font-size: 0.9rem;">{res.get("formatted_posts", {}).get(plat, "")[:120]}...</p>', unsafe_allow_html=True)
        if p_res.get("url"): st.link_button(f"View on {plat.capitalize()}", p_res["url"])
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🚀 CREATE ANOTHER CAMPAIGN", type="primary", use_container_width=True): _reset_session(); st.rerun()

# ── End of App ───────────────────────────────────────────────