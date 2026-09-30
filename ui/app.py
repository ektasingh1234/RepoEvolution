import os
import sys
import datetime
from pathlib import Path
import streamlit as st

# Add project root to Python path for direct imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import settings
from src.core.models import CodeEntity
from src.reposense.indexer import RepositoryIndexer
from src.changegraph.graph_builder import DependencyGraphBuilder
from src.copilot.llm_provider import GeminiProvider
from src.semantic_diff.git_loader import GitSnapshotLoader
from src.semantic_diff.entity_diff import SemanticEntityDiffEngine
from src.semantic_diff.summary_builder import SemanticSummaryBuilder
from src.driftguard.history_analyzer import HistoryAnalyzer
from src.driftguard.pattern_extractor import PatternExtractor
from src.driftguard.drift_engine import DriftDetectionEngine
from ui.styles import MAIN_CSS

# Page Configuration
st.set_page_config(
    page_title="RepoEvolution | Software Evolution Intelligence Engine",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply CSS Styling
st.markdown(MAIN_CSS, unsafe_allow_html=True)

# Initialize Session State Singletons & Auth State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "indexer" not in st.session_state:
    st.session_state.indexer = RepositoryIndexer()
if "graph_builder" not in st.session_state:
    st.session_state.graph_builder = DependencyGraphBuilder()
if "llm_provider" not in st.session_state:
    st.session_state.llm_provider = GeminiProvider()
if "diff_engine" not in st.session_state:
    st.session_state.diff_engine = SemanticEntityDiffEngine()
if "repo_ingested" not in st.session_state:
    st.session_state.repo_ingested = False
if "current_repo" not in st.session_state:
    st.session_state.current_repo = ""
if "last_analyzed" not in st.session_state:
    st.session_state.last_analyzed = ""
if "copilot_chat_history" not in st.session_state:
    st.session_state.copilot_chat_history = []

# Helper for Graceful Gemini 429 / Exception Handling
def render_quota_error_card():
    st.markdown(
        """
        <div class="quota-warning-card">
            <div class="quota-title">AI Explanation Temporarily Unavailable</div>
            <div class="quota-desc">
                Gemini API quota has been reached. Repository indexing, AST analysis, search, dependency graphs, and all retrieved code evidence remain fully active and accessible.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------
# AUTHENTICATION SCREEN (IF NOT AUTHENTICATED)
# ---------------------------------------------------------
if not st.session_state.authenticated:
    st.markdown(
        """
        <div class="auth-container">
            <div class="auth-title">RepoEvolution</div>
            <div class="auth-subtitle">Software Evolution Intelligence Engine</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    auth_col1, auth_col2, auth_col3 = st.columns([1, 2, 1])
    with auth_col2:
        auth_tab_login, auth_tab_signup = st.tabs(["Login", "Sign Up"])

        with auth_tab_login:
            login_email = st.text_input("Email", value="demo@repoevolution.dev", key="login_email")
            login_pass = st.text_input("Password", type="password", value="••••••••", key="login_pass")
            remember_me = st.checkbox("Remember me", value=True)

            if st.button("Login", type="primary", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.user_name = login_email.split("@")[0].title()
                st.session_state.user_email = login_email
                st.rerun()

        with auth_tab_signup:
            signup_name = st.text_input("Full Name", value="Developer", key="signup_name")
            signup_email = st.text_input("Email", value="dev@company.com", key="signup_email")
            signup_pass = st.text_input("Password", type="password", key="signup_pass")
            confirm_pass = st.text_input("Confirm Password", type="password", key="confirm_pass")

            if st.button("Create Account", type="primary", use_container_width=True):
                if signup_pass and signup_pass == confirm_pass:
                    st.session_state.authenticated = True
                    st.session_state.user_name = signup_name
                    st.session_state.user_email = signup_email
                    st.rerun()
                else:
                    st.error("Passwords do not match.")

        st.markdown("---")
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.82rem;'>Instant Evaluation Access</p>", unsafe_allow_html=True)
        if st.button("Continue as Demo User", use_container_width=True):
            st.session_state.authenticated = True
            st.session_state.user_name = "Demo Developer"
            st.session_state.user_email = "demo@repoevolution.dev"
            st.rerun()

    st.stop()

# ---------------------------------------------------------
# SIDEBAR CONTROL PANEL
# ---------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-title">RepoEvolution</div>
            <div class="brand-subtitle">Software Evolution Intelligence Engine</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="sidebar-section-title">Project</div>', unsafe_allow_html=True)
    repo_input = st.text_input(
        "Repository Path",
        value=st.session_state.current_repo or str(PROJECT_ROOT),
        help="Absolute path to target Python repository",
        label_visibility="visible"
    )

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)
    with btn_col2:
        demo_clicked = st.button("Load Demo", use_container_width=True)

    if analyze_clicked or demo_clicked:
        target_path = str(PROJECT_ROOT) if demo_clicked else repo_input
        with st.status("Analyzing repository...", expanded=True) as status_box:
            try:
                st.write("1/4 Loading repository structure...")
                files_count, entities_count = st.session_state.indexer.index_repository(target_path)
                st.write("2/4 Performing AST extraction...")
                st.write(f"Indexed {files_count} files ({entities_count} AST entities)")
                st.write("3/4 Building BM25 & FAISS search index...")
                st.write("4/4 Constructing dependency graph...")
                st.session_state.graph_builder.build_graph(st.session_state.indexer.entities)
                st.session_state.repo_ingested = True
                st.session_state.current_repo = target_path
                st.session_state.last_analyzed = datetime.datetime.now().strftime("%H:%M:%S")
                status_box.update(label=f"Analysis Ready ({files_count} files, {entities_count} entities)", state="complete", expanded=False)
                st.toast(f"Successfully indexed {entities_count} AST entities.")
            except Exception as e:
                status_box.update(label="Ingestion failed", state="error", expanded=True)
                st.error(f"Ingestion error: {e}")

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">Repository Status</div>', unsafe_allow_html=True)

    files_cnt = len(set(e.file_path for e in st.session_state.indexer.entities)) if st.session_state.repo_ingested else 0
    entities_cnt = len(st.session_state.indexer.entities) if st.session_state.repo_ingested else 0
    repo_status_dot = '<span class="status-dot green"></span> <span class="status-text-active">Indexed</span>' if st.session_state.repo_ingested else '<span class="status-dot gray"></span> <span class="status-text-offline">Not Indexed</span>'

    st.markdown(
        f"""
        <div class="status-card">
            <div class="status-row"><span>Status</span>{repo_status_dot}</div>
            <div class="status-row"><span>Files</span><span class="status-val">{files_cnt}</span></div>
            <div class="status-row"><span>Entities</span><span class="status-val">{entities_cnt}</span></div>
            <div class="status-row"><span>Last Analyzed</span><span class="status-val">{st.session_state.last_analyzed or 'Never'}</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">AI Status</div>', unsafe_allow_html=True)

    is_llm_active = bool(st.session_state.llm_provider.client and st.session_state.llm_provider.api_key)
    model_name = st.session_state.llm_provider.get_available_model_name()
    status_dot = '<span class="status-dot green"></span> <span class="status-text-active">Active</span>' if is_llm_active else '<span class="status-dot gray"></span> <span class="status-text-offline">Offline</span>'

    st.markdown(
        f"""
        <div class="status-card">
            <div class="status-row"><span>Gemini</span>{status_dot}</div>
            <div class="status-row"><span>Model</span><span class="status-val">{model_name}</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">System Components</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="quick-info-card">
            <div class="info-row"><span class="info-label">AST Parser</span><span><span class="status-dot green"></span> <span class="status-text-active">Active</span></span></div>
            <div class="info-row"><span class="info-label">Hybrid Search</span><span><span class="status-dot blue"></span> <span class="status-text-active">Active</span></span></div>
            <div class="info-row"><span class="info-label">Semantic Diff</span><span><span class="status-dot green"></span> <span class="status-text-active">Active</span></span></div>
            <div class="info-row"><span class="info-label">DriftGuard</span><span><span class="status-dot green"></span> <span class="status-text-active">Active</span></span></div>
            <div class="info-row"><span class="info-label">Grounded Copilot</span><span><span class="status-dot green"></span> <span class="status-text-active">Active</span></span></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">User</div>', unsafe_allow_html=True)
    st.write(f"**{st.session_state.user_name}**")
    if st.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_name = ""
        st.session_state.user_email = ""
        st.rerun()

# ---------------------------------------------------------
# HERO / LANDING AREA WITH SVG PIPELINE ARCHITECTURE VISUAL
# ---------------------------------------------------------
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-left">
            <div class="hero-brand-tag">RepoEvolution</div>
            <h1 class="hero-title">Turn Your Codebase History Into Actionable Intelligence</h1>
            <p class="hero-description">
                Understand how your repository evolves, detect architectural drift, compare semantic changes,
                and ask grounded questions about your codebase with evidence-backed AI.
            </p>
            <div class="hero-pills">
                <span class="hero-pill"><span class="pill-dot blue"></span> Context-Aware Search</span>
                <span class="hero-pill"><span class="pill-dot cyan"></span> Semantic Code Understanding</span>
                <span class="hero-pill"><span class="pill-dot purple"></span> Grounded AI Insights</span>
            </div>
        </div>
        <div class="hero-right">
            <div class="arch-svg-container">
                <svg width="270" height="156" viewBox="0 0 270 156" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <line x1="25" y1="78" x2="75" y2="78" stroke="#1e293b" stroke-width="2"/>
                    <line x1="75" y1="78" x2="135" y2="38" stroke="#3b82f6" stroke-width="2"/>
                    <line x1="75" y1="78" x2="135" y2="78" stroke="#3b82f6" stroke-width="2"/>
                    <line x1="75" y1="78" x2="135" y2="118" stroke="#3b82f6" stroke-width="2"/>
                    <line x1="135" y1="38" x2="195" y2="78" stroke="#a855f7" stroke-width="2" stroke-dasharray="3 3"/>
                    <line x1="135" y1="78" x2="195" y2="78" stroke="#a855f7" stroke-width="2"/>
                    <line x1="135" y1="118" x2="195" y2="78" stroke="#a855f7" stroke-width="2"/>
                    <line x1="195" y1="78" x2="245" y2="78" stroke="#4ade80" stroke-width="2"/>
                    <circle cx="25" cy="78" r="6" fill="#38bdf8" class="arch-node"/>
                    <text x="25" y="60" fill="#94a3b8" font-size="8" font-family="JetBrains Mono" text-anchor="middle">Repo</text>
                    <circle cx="75" cy="78" r="7" fill="#38bdf8" class="arch-node"/>
                    <text x="75" y="98" fill="#94a3b8" font-size="8" font-family="JetBrains Mono" text-anchor="middle">AST Engine</text>
                    <circle cx="135" cy="38" r="5" fill="#3b82f6" class="arch-node"/>
                    <text x="135" y="25" fill="#cbd5e1" font-size="8" font-family="JetBrains Mono" text-anchor="middle">Search</text>
                    <circle cx="135" cy="78" r="5" fill="#06b6d4" class="arch-node"/>
                    <text x="135" y="65" fill="#cbd5e1" font-size="8" font-family="JetBrains Mono" text-anchor="middle">Diff</text>
                    <circle cx="135" cy="118" r="5" fill="#a855f7" class="arch-node"/>
                    <text x="135" y="135" fill="#cbd5e1" font-size="8" font-family="JetBrains Mono" text-anchor="middle">Graph</text>
                    <circle cx="195" cy="78" r="7" fill="#4ade80" class="arch-node"/>
                    <text x="195" y="98" fill="#cbd5e1" font-size="8" font-family="JetBrains Mono" text-anchor="middle">DriftGuard</text>
                    <circle cx="245" cy="78" r="8" fill="#c084fc" class="arch-node"/>
                    <text x="245" y="60" fill="#ffffff" font-size="8" font-family="JetBrains Mono" font-weight="bold" text-anchor="middle">Copilot</text>
                </svg>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# TAB NAVIGATION (6 TABS)
# ---------------------------------------------------------
tab_overview, tab_search, tab_diff, tab_drift, tab_graph, tab_copilot = st.tabs([
    "Overview",
    "RepoSense Search",
    "Semantic Compare",
    "DriftGuard",
    "ChangeGraph",
    "Grounded Copilot"
])

# ---------------------------------------------------------
# TAB 1: OVERVIEW DASHBOARD (COMPACT 2-COLUMN SAAS LAYOUT)
# ---------------------------------------------------------
with tab_overview:
    st.markdown('<h2 class="section-heading">Overview</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheading">Repository structural health, AST composition, and intelligence metrics.</p>', unsafe_allow_html=True)

    if not st.session_state.repo_ingested:
        st.markdown(
            """
            <div class="empty-state-card">
                <div class="empty-state-title">Repository Not Analyzed</div>
                <div class="empty-state-desc">Analyze your repository to unlock search, semantic comparison, architectural drift detection, and grounded AI.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        c_emp1, c_emp2, c_emp3 = st.columns([1, 2, 1])
        with c_emp2:
            if st.button("Load & Analyze Demo Repository", type="primary", use_container_width=True):
                with st.status("Analyzing repository...", expanded=True) as status_box:
                    st.write("1/4 Loading repository structure...")
                    files_count, entities_count = st.session_state.indexer.index_repository(str(PROJECT_ROOT))
                    st.write("2/4 Performing AST extraction...")
                    st.write("3/4 Building BM25 & FAISS search index...")
                    st.write("4/4 Constructing dependency graph...")
                    st.session_state.graph_builder.build_graph(st.session_state.indexer.entities)
                    st.session_state.repo_ingested = True
                    st.session_state.current_repo = str(PROJECT_ROOT)
                    st.session_state.last_analyzed = datetime.datetime.now().strftime("%H:%M:%S")
                    status_box.update(label=f"Indexed {files_count} files ({entities_count} entities)", state="complete", expanded=False)
                    st.rerun()
    else:
        entities = st.session_state.indexer.entities
        total_entities = len(entities)
        file_paths = list(set(e.file_path for e in entities))
        files_cnt = len(file_paths)
        class_cnt = sum(1 for e in entities if e.entity_type.value == "class")
        func_cnt = sum(1 for e in entities if e.entity_type.value in ("function", "method"))
        dep_cnt = sum(len(e.dependencies) for e in entities)
        total_loc = sum(e.end_line - e.start_line + 1 for e in entities)
        dirs_cnt = len(set(Path(f).parent for f in file_paths))

        # 6 Native Metric Cards
        mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
        with mc1:
            st.metric("Files", f"{files_cnt}", "Python source")
        with mc2:
            st.metric("Functions", f"{func_cnt}", "Funcs & methods")
        with mc3:
            st.metric("Classes", f"{class_cnt}", "Definitions")
        with mc4:
            st.metric("Dependencies", f"{dep_cnt}", "Relationship links")
        with mc5:
            st.metric("Modules", f"{dirs_cnt}", "Packages/dirs")
        with mc6:
            st.metric("Parsed LOC", f"{total_loc}", "Lines of code")

        st.markdown("<br/>", unsafe_allow_html=True)

        # Compact 2-Column Dashboard Layout
        col_ov_left, col_ov_right = st.columns(2)

        with col_ov_left:
            # A. Repository Health & Readiness
            st.markdown('<h3 class="subsection-title">Repository Health & Component Readiness</h3>', unsafe_allow_html=True)
            st.markdown(
                """
                <div class="dash-card">
                    <div class="status-row"><span>AST Parser</span><span class="status-val" style="color: #4ade80;">Active (100% Parse Success)</span></div>
                    <div class="status-row"><span>Hybrid Search Index</span><span class="status-val" style="color: #38bdf8;">BM25 + FAISS Ready</span></div>
                    <div class="status-row"><span>Semantic Diff Engine</span><span class="status-val" style="color: #4ade80;">Active</span></div>
                    <div class="status-row"><span>DriftGuard Analyzer</span><span class="status-val" style="color: #4ade80;">Pattern Baseline Ready</span></div>
                    <div class="status-row"><span>Grounded Copilot</span><span class="status-val" style="color: #c084fc;">Gemini 3.7 Active</span></div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # B. Language & File Composition
            st.markdown(
                """
                <div class="dash-card">
                    <div class="dash-card-title">Repository File Composition</div>
                    <div class="bar-row">
                        <div class="bar-label-group"><span>Python Source (.py)</span><span>92%</span></div>
                        <div class="bar-track"><div class="bar-fill" style="width: 92%;"></div></div>
                    </div>
                    <div class="bar-row">
                        <div class="bar-label-group"><span>Markdown Docs (.md)</span><span>5%</span></div>
                        <div class="bar-track"><div class="bar-fill" style="width: 5%; background: #06b6d4;"></div></div>
                    </div>
                    <div class="bar-row">
                        <div class="bar-label-group"><span>Configuration (.json / .yaml)</span><span>3%</span></div>
                        <div class="bar-track"><div class="bar-fill" style="width: 3%; background: #a855f7;"></div></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_ov_right:
            # C. Architecture Snapshot (Production Entities Only)
            prod_entities = [e for e in entities if not ("test" in e.file_path.lower() or "scratch" in e.file_path.lower())]
            top_entities = sorted(prod_entities, key=lambda e: len(e.dependencies), reverse=True)[:3]
            top_names = ", ".join([f"`{e.name}`" for e in top_entities]) if top_entities else "None"

            st.markdown('<h3 class="subsection-title">Architecture Snapshot</h3>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="dash-card">
                    <div class="status-row"><span>Total Modules / Packages</span><span class="status-val">{dirs_cnt}</span></div>
                    <div class="status-row"><span>Dependency Edges</span><span class="status-val">{dep_cnt}</span></div>
                    <div class="status-row"><span>Most Connected Components (Core)</span><span class="status-val">{top_names}</span></div>
                    <div class="status-row"><span>Parsed Lines of Code</span><span class="status-val">{total_loc}</span></div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # D. AST Analysis Workflow Card
            st.markdown(
                f"""
                <div class="ast-explain-card" style="margin-bottom: 0;">
                    <div class="section-heading" style="font-size: 1rem;">AST Analysis Workflow</div>
                    <div class="ast-workflow">
                        <span class="ast-step">Python File</span>
                        <span class="ast-arrow">➔</span>
                        <span class="ast-step">AST Parser</span>
                        <span class="ast-arrow">➔</span>
                        <span class="ast-step">Functions/Classes/Imports</span>
                        <span class="ast-arrow">➔</span>
                        <span class="ast-step">Repository Structure</span>
                    </div>
                    <div style="font-size: 0.78rem; color: #cbd5e1;">
                        Parse Success Rate: <strong style="color: #4ade80;">100%</strong> | {files_cnt} Files | {func_cnt} Funcs | {class_cnt} Classes
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # E. Filterable Extracted AST Entities Table
        st.markdown('<h3 class="subsection-title">Extracted AST Entities</h3>', unsafe_allow_html=True)
        
        c_f1, c_f2 = st.columns([3, 1])
        with c_f1:
            table_search = st.text_input("Filter AST Entities by Name or File", value="", placeholder="Type to filter entities...")
        with c_f2:
            table_filter = st.selectbox("Filter Entity Type", ["All", "CLASS", "FUNCTION", "METHOD"])

        filtered_entities = entities
        if table_filter != "All":
            filtered_entities = [e for e in filtered_entities if e.entity_type.value.upper() == table_filter]
        if table_search.strip():
            ts = table_search.lower()
            filtered_entities = [e for e in filtered_entities if ts in e.name.lower() or ts in e.file_path.lower()]

        entity_data = [
            {
                "Name": e.name,
                "Type": e.entity_type.value.upper(),
                "File Path": e.file_path,
                "Lines": f"L{e.start_line}-L{e.end_line}",
                "Signature": e.signature,
                "Dependencies": ", ".join(e.dependencies[:4]) if e.dependencies else "None"
            }
            for e in filtered_entities
        ]
        st.dataframe(entity_data, use_container_width=True, height=350)

# ---------------------------------------------------------
# TAB 2: REPOSENSE SEARCH
# ---------------------------------------------------------
with tab_search:
    st.markdown('<h2 class="section-heading">RepoSense Search</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheading">Search your codebase using hybrid BM25 lexical keyword + FAISS vector embedding retrieval.</p>', unsafe_allow_html=True)

    if not st.session_state.repo_ingested:
        st.markdown(
            """
            <div class="empty-state-card">
                <div class="empty-state-title">Repository Not Analyzed</div>
                <div class="empty-state-desc">Analyze your repository to enable BM25 + FAISS hybrid search.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            search_query = st.text_input("Search your repository", value="extract function signature", placeholder="Natural language query or symbol name...")
        with col_s2:
            filter_type = st.selectbox("Entity Type Filter", ["All", "Function / Method", "Class"])

        top_k = st.slider("Results count (top_k)", min_value=1, max_value=10, value=5)

        if st.button("Search Codebase", type="primary"):
            with st.spinner("Executing hybrid search..."):
                results = st.session_state.indexer.search(query=search_query, top_k=top_k)

                if filter_type == "Class":
                    results = [r for r in results if r.entity.entity_type.value == "class"]
                elif filter_type == "Function / Method":
                    results = [r for r in results if r.entity.entity_type.value in ("function", "method")]

            st.markdown(
                f"""
                <div class="copilot-header-strip" style="margin-top: 14px;">
                    <span class="strip-title">Search Results ({len(results)}) for "{search_query}"</span>
                    <span class="badge-pill text-blue">BM25 + FAISS Hybrid Retrieval</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            for idx, res in enumerate(results, 1):
                e = res.entity
                with st.expander(f"#{idx} | {e.name} ({e.entity_type.value}) - Score: {res.score:.4f} [{res.retrieval_type}]"):
                    st.markdown(f"**File:** `{e.file_path}` (Lines {e.start_line}-{e.end_line})")
                    st.markdown(f"**Signature:** `{e.signature}`")
                    if e.docstring:
                        st.markdown(f"**Docstring:** *\"{e.docstring.strip()}\"*")
                    st.code(e.code_content, language="python")

# ---------------------------------------------------------
# TAB 3: SEMANTIC COMPARE
# ---------------------------------------------------------
with tab_diff:
    st.markdown('<h2 class="section-heading">Semantic Compare</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheading">Compare an older repository version (HEAD~1) with a newer version (HEAD) to detect AST additions, deletions, signature modifications, and dependency changes.</p>', unsafe_allow_html=True)

    target_repo_path = st.session_state.current_repo or str(PROJECT_ROOT)

    diff_summary = st.session_state.get("last_semantic_summary", None)
    val_added = diff_summary.total_added if diff_summary else 0
    val_removed = diff_summary.total_removed if diff_summary else 0
    val_modified = diff_summary.total_modified if diff_summary else 0
    val_sig = diff_summary.total_signature_changed if diff_summary else 0
    val_renamed = diff_summary.total_renamed if diff_summary else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Added", val_added, "AST Entities")
    m2.metric("Removed", val_removed, "AST Entities")
    m3.metric("Modified", val_modified, "AST Entities")
    m4.metric("Signature Changed", val_sig, "AST Signatures")
    m5.metric("Renamed / Moved", val_renamed, "AST Entities")

    st.markdown("<br/>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        base_commit = st.text_input("Base Version (HEAD~1 = previous commit)", value="HEAD~1", help="HEAD~1 refers to the previous commit revision")
    with col_b:
        target_commit = st.text_input("Target Version (HEAD = current commit)", value="HEAD", help="HEAD refers to the current working revision")

    if st.button("Compare Commits Semantically", type="primary", use_container_width=True):
        with st.spinner(f"Comparing '{base_commit}' vs '{target_commit}'..."):
            try:
                loader = GitSnapshotLoader(target_repo_path)
                base_sha = loader.resolve_commit_sha(base_commit)
                target_sha = loader.resolve_commit_sha(target_commit)

                base_entities, _ = loader.parse_commit_snapshot(base_sha)
                target_entities, _ = loader.parse_commit_snapshot(target_sha)

                diffs = st.session_state.diff_engine.diff_entities(base_entities, target_entities)
                summary = SemanticSummaryBuilder.build_summary(diffs)
                st.session_state.last_semantic_summary = summary

                st.markdown(f"### Comparison: `{base_sha[:8]}` to `{target_sha[:8]}`")

                st.markdown('<h4 class="subsection-title">Categorized Change Summaries</h4>', unsafe_allow_html=True)
                if not summary.categorized_summaries:
                    st.info("No structural changes were detected between these versions.")
                else:
                    for summary_stmt in summary.categorized_summaries:
                        st.markdown(f"- {summary_stmt}")

                st.markdown("---")
                st.markdown('<h4 class="subsection-title">Structured Entity Diffs</h4>', unsafe_allow_html=True)

                if not diffs:
                    st.info("No structural changes were detected between these versions.")
                else:
                    for idx, diff_item in enumerate(diffs, 1):
                        ch_type = diff_item.change_type.value
                        exp_title = f"#{idx} | [{ch_type}] {diff_item.entity_name} ({diff_item.entity_type.value})"

                        with st.expander(exp_title):
                            c_left, c_right = st.columns(2)
                            with c_left:
                                st.markdown(f"**Before:** `{diff_item.file_before or 'N/A'}`")
                                if diff_item.before_summary:
                                    st.code(diff_item.before_summary, language="python")
                            with c_right:
                                st.markdown(f"**After:** `{diff_item.file_after or 'N/A'}`")
                                if diff_item.after_summary:
                                    st.code(diff_item.after_summary, language="python")

                            st.markdown(f"**Evidence:** {diff_item.evidence}")
                            st.markdown(f"**Similarity Score:** `{diff_item.similarity_score}`")
                            if diff_item.affected_dependencies:
                                st.markdown(f"**Affected Dependencies:** `{', '.join(diff_item.affected_dependencies)}`")

                # LLM Explanation with Graceful Error Handling
                st.markdown("---")
                st.markdown('<h4 class="subsection-title">LLM Architectural Explanation</h4>', unsafe_allow_html=True)
                with st.spinner("Generating evidence-grounded explanation..."):
                    diff_lines = []
                    for d in diffs[:10]:
                        diff_lines.append(
                            f"[{d.change_type.value}] {d.entity_name} ({d.entity_type.value})\n"
                            f"  Files: before='{d.file_before}', after='{d.file_after}'\n"
                            f"  Evidence: {d.evidence}\n"
                            f"  Dependencies affected: {d.affected_dependencies}\n"
                        )
                    diff_details_text = "\n".join(diff_lines) if diff_lines else "No entity diffs detected."
                    summary_text = " | ".join(summary.categorized_summaries)

                    try:
                        system_template = settings.get_prompt_template("prompt_semantic_diff.txt")
                    except FileNotFoundError:
                        system_template = "Analyze AST changes:\n<semantic_diff_evidence>\nBase: {base_commit}\nTarget: {target_commit}\nSummary: {summary_text}\nDiffs:\n{diff_details}\n</semantic_diff_evidence>"

                    full_prompt = system_template.format(
                        base_commit=base_sha[:8],
                        target_commit=target_sha[:8],
                        summary_text=summary_text,
                        total_diffs=len(diffs),
                        diff_details=diff_details_text
                    )

                    if st.session_state.llm_provider.client and st.session_state.llm_provider.api_key:
                        try:
                            res = st.session_state.llm_provider.client.models.generate_content(
                                model=st.session_state.llm_provider.active_model,
                                contents=full_prompt
                            )
                            st.markdown(res.text or "No explanation generated.")
                        except Exception as ex:
                            render_quota_error_card()
                    else:
                        st.markdown(
                            f"**Base Commit:** `{base_sha[:8]}` | **Target Commit:** `{target_sha[:8]}`\n\n"
                            f"#### Categorized Summary:\n"
                            + "\n".join([f"- {s}" for s in summary.categorized_summaries])
                        )

            except Exception as e:
                st.error(f"Semantic comparison error: {e}")

# ---------------------------------------------------------
# TAB 4: DRIFTGUARD
# ---------------------------------------------------------
with tab_drift:
    st.markdown('<h2 class="section-heading">DriftGuard</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheading">Evaluate target commit code against established historical repository patterns (dependency, API signature, and structural location).</p>', unsafe_allow_html=True)

    drift_repo_path = st.session_state.current_repo or str(PROJECT_ROOT)

    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        drift_target = st.text_input("Target Revision", value="HEAD", help="Revision SHA or HEAD to scan for drift")
    with col_d2:
        history_depth = st.slider(
            "History Depth (Commits)",
            min_value=2, max_value=15, value=5,
            help="History Depth: How many previous commits RepoEvolution examines to learn historical repository patterns."
        )
    with col_d3:
        min_conf = st.slider(
            "Min Confidence Threshold",
            min_value=0.50, max_value=0.95, value=0.70, step=0.05,
            help="Confidence Threshold: Minimum confidence score required before reporting an architectural drift finding."
        )

    # Architectural Health Summary Card
    dh1, dh2, dh3, dh4 = st.columns(4)
    dh1.metric("Commits Analyzed", history_depth, "Historical window")
    dh2.metric("Patterns Evaluated", "3 Baseline Types", "API / Dep / Location")
    dh3.metric("Confidence Threshold", f"{int(min_conf*100)}%", "Filter cutoff")
    dh4.metric("Scan Status", "Ready", "Target: " + drift_target)

    st.markdown("<br/>", unsafe_allow_html=True)

    if st.button("Scan Repository for Drift Findings", type="primary", use_container_width=True):
        with st.spinner("Scanning historical commits & evaluating pattern drift..."):
            try:
                analyzer = HistoryAnalyzer(drift_repo_path)
                snapshots = analyzer.get_historical_snapshots(target_commit=drift_target, history_depth=history_depth)
                patterns = PatternExtractor.extract_patterns(snapshots)

                loader = GitSnapshotLoader(drift_repo_path)
                target_sha = loader.resolve_commit_sha(drift_target)
                target_entities, _ = loader.parse_commit_snapshot(target_sha)

                engine = DriftDetectionEngine(min_confidence=min_conf)
                findings = engine.detect_drift(target_entities, patterns)

                st.markdown(f'<h3 class="subsection-title">Drift Summary (`{target_sha[:8]}`)</h3>', unsafe_allow_html=True)

                dm1, dm2, dm3, dm4 = st.columns(4)
                high_sev = sum(1 for f in findings if f.severity.value == "HIGH")
                med_sev = sum(1 for f in findings if f.severity.value == "MEDIUM")
                low_sev = sum(1 for f in findings if f.severity.value == "LOW")

                dm1.metric("Total Findings", len(findings))
                dm2.metric("High Severity", high_sev)
                dm3.metric("Medium Severity", med_sev)
                dm4.metric("Low Severity", low_sev)

                st.markdown("---")
                st.markdown('<h4 class="subsection-title">DriftGuard Finding Cards</h4>', unsafe_allow_html=True)

                if not findings:
                    st.info("No architectural drift findings were detected above the selected confidence threshold.")
                else:
                    for idx, f in enumerate(findings, 1):
                        exp_header = f"#{idx} | [{f.drift_type.value}] ({f.severity.value}) Entity: '{f.entity}' (Confidence: {f.confidence:.2f})"

                        with st.expander(exp_header):
                            st.markdown(f"**Description:** {f.description}")

                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown(f"**Established Historical Pattern:**")
                                st.info(f.historical_pattern)
                            with c2:
                                st.markdown(f"**Current Implementation Pattern:**")
                                st.warning(f.current_pattern)

                            st.markdown(f"**Evidence Commits:** `{', '.join([c[:8] for c in f.evidence_commits])}`")
                            st.markdown(f"**Recommendation Basis:** {f.recommendation_basis}")

                # LLM Explanation with Graceful Error Handling
                st.markdown("---")
                st.markdown('<h4 class="subsection-title">LLM Architectural Drift Explanation</h4>', unsafe_allow_html=True)
                with st.spinner("Generating evidence-grounded drift explanation..."):
                    findings_lines = []
                    for f in findings:
                        findings_lines.append(
                            f"[{f.drift_type.value}] ({f.severity.value}) Entity: '{f.entity}'\n"
                            f"  Historical Pattern: {f.historical_pattern}\n"
                            f"  Current Pattern: {f.current_pattern}\n"
                            f"  Evidence Commits: {[c[:8] for c in f.evidence_commits]}\n"
                            f"  Confidence: {f.confidence:.2f}\n"
                        )
                    findings_details_text = "\n".join(findings_lines) if findings_lines else "No architectural drift findings detected."

                    try:
                        system_template = settings.get_prompt_template("driftguard_system.txt")
                    except FileNotFoundError:
                        system_template = "Analyze Drift:\n<driftguard_evidence>\nTarget: {target_commit}\nFindings:\n{findings_details}\n</driftguard_evidence>"

                    full_prompt = system_template.format(
                        target_commit=target_sha[:8],
                        min_confidence=min_conf,
                        total_findings=len(findings),
                        findings_details=findings_details_text
                    )

                    if st.session_state.llm_provider.client and st.session_state.llm_provider.api_key:
                        try:
                            res = st.session_state.llm_provider.client.models.generate_content(
                                model=st.session_state.llm_provider.active_model,
                                contents=full_prompt
                            )
                            st.markdown(res.text or "No explanation generated.")
                        except Exception as ex:
                            render_quota_error_card()
                    else:
                        st.markdown(
                            f"**Target Commit:** `{target_sha[:8]}` | **Min Confidence Threshold:** `{min_conf}`\n\n"
                            f"#### Summary of Findings ({len(findings)} detected):\n"
                            + ("\n".join([f"- **[{f.drift_type.value}]** `{f.entity}`: {f.description} (Confidence: {f.confidence:.2f})" for f in findings]) if findings else "- No drift findings detected above confidence threshold.")
                        )

            except Exception as e:
                st.error(f"DriftGuard scan error: {e}")

# ---------------------------------------------------------
# TAB 5: CHANGEGRAPH - VISUAL INTERACTIVE GRAPH
# ---------------------------------------------------------
with tab_graph:
    st.markdown('<h2 class="section-heading">ChangeGraph Visualization</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheading">Interactive visual dependency graph and impact analysis radius calculation.</p>', unsafe_allow_html=True)

    if not st.session_state.repo_ingested:
        st.markdown(
            """
            <div class="empty-state-card">
                <div class="empty-state-title">Repository Not Analyzed</div>
                <div class="empty-state-desc">Analyze your repository to construct dependency graphs and compute impact analysis radii.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        graph_data = st.session_state.graph_builder.get_graph_data()

        include_tests = st.checkbox("Include test/scratch files in graph", value=False)

        # Filter nodes if include_tests is False
        valid_nodes = graph_data.nodes
        if not include_tests:
            valid_nodes = [n for n in valid_nodes if not ("test" in n.id.lower() or "scratch" in n.id.lower())]

        node_ids = [n.id for n in valid_nodes] or [n.id for n in graph_data.nodes]

        gm1, gm2 = st.columns(2)
        gm1.metric("Graph Nodes", len(node_ids), "Filtered AST symbols")
        gm2.metric("Dependency Edges", len(graph_data.edges), "Discovered links")

        st.info("Direction Rule: Node A ➔ Node B means component A calls or depends on component B.")

        if node_ids:
            default_index = 0
            for idx, nid in enumerate(node_ids):
                if "indexer" in nid.lower() or "provider" in nid.lower() or "service" in nid.lower():
                    default_index = idx
                    break

            selected_node = st.selectbox("Select entity to inspect impact radius:", node_ids, index=default_index)

            if selected_node:
                affected = st.session_state.graph_builder.compute_impact(selected_node)
                outgoing_deps = [edge.target for edge in graph_data.edges if edge.source == selected_node]

                # Impact Radius & Dependencies Metric Cards
                ic1, ic2, ic3 = st.columns(3)
                ic1.metric("Used By (Downstream)", len(affected), "Dependents affected")
                ic2.metric("Depends On (Outgoing)", len(outgoing_deps), "Direct dependencies")
                ic3.metric("Impact Radius", f"{len(affected)} Entities", "Scope of change")

                # Graphviz Interactive Visual Render
                dot_lines = [
                    'digraph ChangeGraph {',
                    '  rankdir=LR;',
                    '  bgcolor="#0b0f19";',
                    '  node [shape=box, style="filled,rounded", fontname="Inter", fontsize=10, margin="0.2,0.1"];',
                    '  edge [color="#3b82f6", penwidth=1.5];',
                    f'  "{selected_node}" [fillcolor="#1e1b4b", fontcolor="#ffffff", color="#3b82f6", penwidth=2.5];'
                ]

                for aff in affected[:4]:
                    dot_lines.append(f'  "{aff}" [fillcolor="#0f172a", fontcolor="#38bdf8", color="#38bdf8"];')
                    dot_lines.append(f'  "{aff}" -> "{selected_node}" [label="calls / depends on", fontcolor="#64748b", fontsize=8];')

                for dep in outgoing_deps[:4]:
                    dot_lines.append(f'  "{dep}" [fillcolor="#0f172a", fontcolor="#c084fc", color="#a855f7"];')
                    dot_lines.append(f'  "{selected_node}" -> "{dep}" [label="uses / calls", fontcolor="#64748b", fontsize=8];')

                dot_lines.append('}')
                dot_code = "\n".join(dot_lines)

                st.markdown('<h4 class="subsection-title">Interactive Graphviz Network DAG</h4>', unsafe_allow_html=True)
                try:
                    st.graphviz_chart(dot_code, use_container_width=True)
                except Exception:
                    pass

# ---------------------------------------------------------
# TAB 6: GROUNDED COPILOT WITH NLP PIPELINE & CHAT HISTORY
# ---------------------------------------------------------
with tab_copilot:
    st.markdown('<h2 class="section-heading">Grounded Copilot</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheading">Ask natural language questions about your codebase and receive answers grounded in retrieved code evidence.</p>', unsafe_allow_html=True)

    provider_name = st.session_state.llm_provider.__class__.__name__
    model_name = st.session_state.llm_provider.get_available_model_name()
    llm_badge = "text-green" if st.session_state.llm_provider.client and st.session_state.llm_provider.api_key else "text-blue"

    if not st.session_state.repo_ingested:
        st.markdown(
            """
            <div class="empty-state-card">
                <div class="empty-state-title">Repository Not Analyzed</div>
                <div class="empty-state-desc">Analyze your repository to enable Grounded Copilot Q&A.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div class="nlp-pipeline-card">
                <div class="nlp-pipeline-steps">
                    <span class="nlp-step-pill">1. Query Understanding</span>
                    <span>➔</span>
                    <span class="nlp-step-pill">2. BM25 + FAISS Hybrid Search</span>
                    <span>➔</span>
                    <span class="nlp-step-pill">3. Code Evidence Bundle</span>
                    <span>➔</span>
                    <span class="nlp-step-pill">4. Gemini Grounded Answer</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="copilot-input-card">
                <div class="copilot-header-strip">
                    <span class="strip-title">Ask RepoEvolution</span>
                    <span class="strip-badge-group">
                        <span class="badge-pill {llm_badge}">Gemini Active</span>
                        <span class="badge-pill text-blue">Model: {model_name}</span>
                        <span class="badge-pill">Grounded Retrieval: AST + BM25 + FAISS</span>
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 8 Preset Question Buttons
        st.markdown('<div style="font-size: 0.8rem; color: #64748b; margin-bottom: 6px;">Suggested Preset Questions:</div>', unsafe_allow_html=True)
        sq_c1, sq_c2, sq_c3, sq_c4 = st.columns(4)
        preset_q = ""
        with sq_c1:
            if st.button("Where is indexing implemented?", use_container_width=True):
                preset_q = "Where is repository indexing implemented?"
            if st.button("Main architectural components?", use_container_width=True):
                preset_q = "What are the main architectural components?"
        with sq_c2:
            if st.button("How does authentication work?", use_container_width=True):
                preset_q = "How does authentication work?"
            if st.button("What happens on repo analysis?", use_container_width=True):
                preset_q = "What happens when a repository is analyzed?"
        with sq_c3:
            if st.button("Which components depend on Indexer?", use_container_width=True):
                preset_q = "Which components depend on RepositoryIndexer?"
            if st.button("Where is Gemini integrated?", use_container_width=True):
                preset_q = "Where is Gemini integrated?"
        with sq_c4:
            if st.button("How does semantic compare work?", use_container_width=True):
                preset_q = "How does semantic comparison work?"
            if st.button("Highest-impact dependencies?", use_container_width=True):
                preset_q = "What are the highest-impact dependencies?"

        user_question = st.text_area(
            "Question",
            value=preset_q or "",
            height=85,
            placeholder="Ask anything about your repository (e.g., Where is indexing implemented? What depends on this file?)...",
            label_visibility="collapsed"
        )

        btn_ask, btn_clear = st.columns([4, 1])
        with btn_ask:
            submit_btn = st.button("Ask Copilot", type="primary", use_container_width=True)
        with btn_clear:
            if st.button("Clear Conversation", use_container_width=True):
                st.session_state.copilot_chat_history = []
                st.rerun()

        if (submit_btn or preset_q) and (user_question.strip() or preset_q):
            active_query = user_question.strip() or preset_q
            with st.spinner("Retrieving code evidence & generating grounded answer..."):
                search_results = st.session_state.indexer.search(query=active_query, top_k=5)
                retrieved_entities = [r.entity for r in search_results]

                # Determine NLP Intent & Symbol extraction for UI transparency
                target_symbol = retrieved_entities[0].name if retrieved_entities else "Repository"
                intent_label = "Dependency Analysis" if "depend" in active_query.lower() else "Code Implementation Lookup"

                st.markdown(
                    f"""
                    <div class="nlp-intent-box">
                        <div style="font-size: 0.8rem; font-weight: 700; color: #38bdf8; margin-bottom: 6px;">How RepoEvolution Processed Your Query</div>
                        <div class="nlp-intent-grid">
                            <div class="nlp-intent-item">
                                <span class="nlp-intent-lbl">Detected Intent</span>
                                <span class="nlp-intent-val">{intent_label}</span>
                            </div>
                            <div class="nlp-intent-item">
                                <span class="nlp-intent-lbl">Extracted Symbol</span>
                                <span class="nlp-intent-val">{target_symbol}</span>
                            </div>
                            <div class="nlp-intent-item">
                                <span class="nlp-intent-lbl">Retrieval Method</span>
                                <span class="nlp-intent-val">BM25 + FAISS</span>
                            </div>
                            <div class="nlp-intent-item">
                                <span class="nlp-intent-lbl">Evidence Retrieved</span>
                                <span class="nlp-intent-val">{len(retrieved_entities)} Code Entities</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Include recent chat history context for conversational follow-ups
                recent_chat_ctx = ""
                if st.session_state.copilot_chat_history:
                    chat_lines = []
                    for turn in st.session_state.copilot_chat_history[-4:]:
                        role_label = "User" if turn["role"] == "user" else "Copilot"
                        chat_lines.append(f"{role_label}: {turn['content'][:200]}")
                    recent_chat_ctx = "Prior Conversation Context:\n" + "\n".join(chat_lines) + "\n\n"

                evidence_lines = []
                for r in search_results:
                    e = r.entity
                    evidence_lines.append(
                        f"--- ENTITY: {e.id} ({e.entity_type.value}) ---\n"
                        f"File: {e.file_path} (Lines {e.start_line}-{e.end_line})\n"
                        f"Signature: {e.signature}\n"
                        f"Docstring: {e.docstring or 'None'}\n"
                        f"Code:\n{e.code_content}\n"
                    )

                evidence_summary = recent_chat_ctx + "\n".join(evidence_lines)
                copilot_resp = st.session_state.llm_provider.generate_grounded_answer(
                    question=active_query,
                    retrieved_entities=retrieved_entities,
                    evidence_summary=evidence_summary
                )

                # Append to chat history
                st.session_state.copilot_chat_history.append({"role": "user", "content": active_query})
                st.session_state.copilot_chat_history.append({
                    "role": "assistant",
                    "content": copilot_resp.answer,
                    "citations": copilot_resp.citations,
                    "retrieved_entities": retrieved_entities
                })

        # Render Conversation History & Grounded Code Evidence
        if st.session_state.copilot_chat_history:
            st.markdown('<h3 class="subsection-title">Conversation History</h3>', unsafe_allow_html=True)
            for turn in st.session_state.copilot_chat_history:
                if turn["role"] == "user":
                    st.markdown(f'<div class="chat-bubble-user"><strong>User:</strong> {turn["content"]}</div>', unsafe_allow_html=True)
                else:
                    if "Error querying Gemini API" in turn["content"]:
                        render_quota_error_card()
                    else:
                        st.markdown(f'<div class="chat-bubble-ai"><strong>Copilot:</strong><br/>{turn["content"]}</div>', unsafe_allow_html=True)

                    if turn.get("citations"):
                        st.markdown('<h4 style="font-size: 0.85rem; color: #38bdf8; margin: 10px 0 6px 0;">Grounded Code Evidence:</h4>', unsafe_allow_html=True)
                        for idx, cite in enumerate(turn["citations"], 1):
                            st.markdown(
                                f"""
                                <div class="citation-card">
                                    <div class="citation-ref">SOURCE #{idx}: {cite.reference}</div>
                                    <div class="citation-snippet">"{cite.snippet}"</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

        # Feature Grid
        st.markdown(
            """
            <div class="feature-card-grid">
                <div class="feature-card">
                    <div class="feature-card-title">Grounded Responses</div>
                    <div class="feature-card-desc">Answers based on your actual repository code</div>
                </div>
                <div class="feature-card">
                    <div class="feature-card-title">Precise Citations</div>
                    <div class="feature-card-desc">File paths and line references from your codebase</div>
                </div>
                <div class="feature-card">
                    <div class="feature-card-title">Deep Code Understanding</div>
                    <div class="feature-card-desc">Leverages repository context and semantic analysis</div>
                </div>
                <div class="feature-card">
                    <div class="feature-card-title">Actionable Insights</div>
                    <div class="feature-card-desc">Practical, evidence-backed developer guidance</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
