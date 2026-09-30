import os
import sys
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
from ui.styles import MAIN_CSS

# Page Configuration
st.set_page_config(
    page_title="REPOEVOLUTION | Developer Intelligence Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply CSS Styling
st.markdown(MAIN_CSS, unsafe_allow_html=True)

# Initialize Session State Singletons
if "indexer" not in st.session_state:
    st.session_state.indexer = RepositoryIndexer()
if "graph_builder" not in st.session_state:
    st.session_state.graph_builder = DependencyGraphBuilder()
if "llm_provider" not in st.session_state:
    st.session_state.llm_provider = GeminiProvider()
if "repo_ingested" not in st.session_state:
    st.session_state.repo_ingested = False
if "current_repo" not in st.session_state:
    st.session_state.current_repo = ""

# Top Header Banner
st.markdown(
    """
    <div class="hero-banner">
        <div class="hero-title">REPOEVOLUTION</div>
        <div class="hero-subtitle">Software Evolution Intelligence Engine & Grounded Developer Copilot</div>
    </div>
    """,
    unsafe_allow_html=True
)

# Sidebar Control Panel
with st.sidebar:
    st.subheader("⚙️ Control Panel")
    repo_input = st.text_input(
        "Repository Path",
        value=st.session_state.current_repo or str(PROJECT_ROOT),
        help="Absolute path to target Python repository"
    )

    if st.button("🚀 Ingest Repository", use_container_width=True, type="primary"):
        with st.spinner("Parsing AST entities & indexing codebase..."):
            try:
                files_count, entities_count = st.session_state.indexer.index_repository(repo_input)
                st.session_state.graph_builder.build_graph(st.session_state.indexer.entities)
                st.session_state.repo_ingested = True
                st.session_state.current_repo = repo_input
                st.success(f"Ingested {files_count} files ({entities_count} entities)")
            except Exception as e:
                st.error(f"Ingestion failed: {e}")

    st.markdown("---")
    st.markdown(f"**LLM Model:** `{st.session_state.llm_provider.get_available_model_name()}`")
    st.markdown(f"**Embedding Model:** `{settings.EMBEDDING_MODEL_NAME}`")
    st.markdown(f"**Phase 1 Status:** `Active Foundation`")

# Main Navigation Tabs
tab_overview, tab_search, tab_graph, tab_copilot = st.tabs([
    "📊 Repository Overview",
    "🔍 RepoSense Search",
    "🕸️ ChangeGraph",
    "💬 Grounded Copilot"
])

# ---------------------------------------------------------
# TAB 1: REPOSITORY OVERVIEW
# ---------------------------------------------------------
with tab_overview:
    st.subheader("Repository Overview & Parsed Statistics")
    if not st.session_state.repo_ingested:
        st.info("👈 Enter a repository path in the sidebar and click **Ingest Repository** to begin.")
    else:
        entities = st.session_state.indexer.entities
        total_entities = len(entities)
        class_cnt = sum(1 for e in entities if e.entity_type.value == "class")
        func_cnt = sum(1 for e in entities if e.entity_type.value in ("function", "method"))
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-val">{total_entities}</div><div class="stat-lbl">Total AST Entities</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-card"><div class="stat-val">{class_cnt}</div><div class="stat-lbl">Classes Extracted</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-card"><div class="stat-val">{func_cnt}</div><div class="stat-lbl">Functions & Methods</div></div>', unsafe_allow_html=True)

        st.markdown("### Extracted Entities Table")
        entity_data = [
            {
                "Name": e.name,
                "Type": e.entity_type.value.upper(),
                "File Path": e.file_path,
                "Lines": f"L{e.start_line}-L{e.end_line}",
                "Signature": e.signature,
                "Dependencies": ", ".join(e.dependencies[:4]) if e.dependencies else "None"
            }
            for e in entities
        ]
        st.dataframe(entity_data, use_container_width=True, height=350)

# ---------------------------------------------------------
# TAB 2: REPOSENSE SEARCH
# ---------------------------------------------------------
with tab_search:
    st.subheader("Hybrid Semantic & Keyword Search (BM25 + FAISS)")
    if not st.session_state.repo_ingested:
        st.info("Please ingest a repository first.")
    else:
        search_query = st.text_input("Enter natural language query or function/class symbol name:", value="extract function signature")
        top_k = st.slider("Results count (top_k)", min_value=1, max_value=10, value=5)
        
        if st.button("Search Codebase"):
            results = st.session_state.indexer.search(query=search_query, top_k=top_k)
            st.markdown(f"Found **{len(results)}** matching entities for query: *\"{search_query}\"*")
            
            for idx, res in enumerate(results, 1):
                e = res.entity
                badge_cls = "badge-class" if e.entity_type.value == "class" else ("badge-func" if e.entity_type.value == "function" else "badge-method")
                
                with st.expander(f"#{idx} | {e.name} ({e.entity_type.value}) - RRF Score: {res.score} [{res.retrieval_type}]"):
                    st.markdown(f"**File:** `{e.file_path}` (Lines {e.start_line}-{e.end_line})")
                    st.markdown(f"**Signature:** `{e.signature}`")
                    if e.docstring:
                        st.markdown(f"**Docstring:** *\"{e.docstring.strip()}\"*")
                    st.code(e.code_content, language="python")

# ---------------------------------------------------------
# TAB 3: CHANGEGRAPH
# ---------------------------------------------------------
with tab_graph:
    st.subheader("Dependency & Call Relationship Graph")
    if not st.session_state.repo_ingested:
        st.info("Please ingest a repository first.")
    else:
        graph_data = st.session_state.graph_builder.get_graph_data()
        st.write(f"Graph nodes: **{len(graph_data.nodes)}** | Dependency edges: **{len(graph_data.edges)}**")
        
        if graph_data.nodes:
            selected_node = st.selectbox("Select entity to inspect impact radius:", [n.id for n in graph_data.nodes])
            if selected_node:
                affected = st.session_state.graph_builder.compute_impact(selected_node)
                st.markdown(f"**Downstream affected nodes ({len(affected)}):**")
                if affected:
                    for aff in affected:
                        st.markdown(f"- `{aff}`")
                else:
                    st.write("No downstream dependents found for this entity.")

# ---------------------------------------------------------
# TAB 4: GROUNDED COPILOT
# ---------------------------------------------------------
with tab_copilot:
    st.subheader("Ask RepoEvolution Grounded Copilot")
    if not st.session_state.repo_ingested:
        st.info("Please ingest a repository first.")
    else:
        user_question = st.text_area(
            "Ask a question about the repository architecture or code entities:",
            value="What does this repository do and how is AST parsing handled?",
            height=80
        )
        
        if st.button("Submit Question to Copilot", type="primary"):
            with st.spinner("Retrieving evidence & generating grounded answer..."):
                search_results = st.session_state.indexer.search(query=user_question, top_k=5)
                retrieved_entities = [r.entity for r in search_results]

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

                evidence_summary = "\n".join(evidence_lines)
                copilot_resp = st.session_state.llm_provider.generate_grounded_answer(
                    question=user_question,
                    retrieved_entities=retrieved_entities,
                    evidence_summary=evidence_summary
                )

                st.markdown("### Copilot Answer")
                st.markdown(copilot_resp.answer)

                st.markdown("### Grounded Evidence Citations")
                for cite in copilot_resp.citations:
                    st.markdown(f"- 📄 `{cite.reference}` — *{cite.snippet}*")
