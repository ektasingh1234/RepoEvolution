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
from src.semantic_diff.git_loader import GitSnapshotLoader
from src.semantic_diff.entity_diff import SemanticEntityDiffEngine
from src.semantic_diff.summary_builder import SemanticSummaryBuilder
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
if "diff_engine" not in st.session_state:
    st.session_state.diff_engine = SemanticEntityDiffEngine()
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
    st.markdown(f"**Phase 2 Status:** `SemanticDiff Active`")

# Main Navigation Tabs
tab_overview, tab_search, tab_diff, tab_graph, tab_copilot = st.tabs([
    "📊 Repository Overview",
    "🔍 RepoSense Search",
    "🔀 Semantic Compare",
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
                with st.expander(f"#{idx} | {e.name} ({e.entity_type.value}) - RRF Score: {res.score} [{res.retrieval_type}]"):
                    st.markdown(f"**File:** `{e.file_path}` (Lines {e.start_line}-{e.end_line})")
                    st.markdown(f"**Signature:** `{e.signature}`")
                    if e.docstring:
                        st.markdown(f"**Docstring:** *\"{e.docstring.strip()}\"*")
                    st.code(e.code_content, language="python")

# ---------------------------------------------------------
# TAB 3: SEMANTIC COMPARE (PHASE 2)
# ---------------------------------------------------------
with tab_diff:
    st.subheader("🔀 Semantic Git Commit Comparison (AST Entity Diff)")
    st.caption("Compares AST node additions, deletions, signature modifications, and dependency changes between two Git commits without checking out code.")

    target_repo_path = st.session_state.current_repo or str(PROJECT_ROOT)
    
    col_a, col_b = st.columns(2)
    with col_a:
        base_commit = st.text_input("Base Commit / Revision", value="HEAD~1", help="e.g., HEAD~1, main, or commit SHA")
    with col_b:
        target_commit = st.text_input("Target Commit / Revision", value="HEAD", help="e.g., HEAD, feature-branch, or commit SHA")

    if st.button("🔀 Compare Commits Semantically", type="primary", use_container_width=True):
        with st.spinner(f"Loading AST snapshots for '{base_commit}' vs '{target_commit}'..."):
            try:
                loader = GitSnapshotLoader(target_repo_path)
                base_sha = loader.resolve_commit_sha(base_commit)
                target_sha = loader.resolve_commit_sha(target_commit)

                base_entities, _ = loader.parse_commit_snapshot(base_sha)
                target_entities, _ = loader.parse_commit_snapshot(target_sha)

                diffs = st.session_state.diff_engine.diff_entities(base_entities, target_entities)
                summary = SemanticSummaryBuilder.build_summary(diffs)

                st.markdown(f"### Comparison: `{base_sha[:8]}` ➔ `{target_sha[:8]}`")
                
                # Summary Metric Cards
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Added", summary.total_added)
                m2.metric("Removed", summary.total_removed)
                m3.metric("Modified", summary.total_modified)
                m4.metric("Signature Changed", summary.total_signature_changed)
                m5.metric("Renamed / Moved", summary.total_renamed)

                st.markdown("#### High-Level Categorized Summaries")
                for summary_stmt in summary.categorized_summaries:
                    st.markdown(f"- 📌 {summary_stmt}")

                st.markdown("---")
                st.markdown("#### Structured Entity Diff Details")

                if not diffs:
                    st.success("No AST semantic changes detected between these commits.")
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

                # Generate LLM Explanation
                st.markdown("---")
                st.markdown("#### LLM SemanticDiff Architectural Explanation")
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
                            st.warning(f"LLM Warning: {ex}")
                    else:
                        st.markdown(
                            f"### [Offline SemanticDiff Evidence Explanation]\n\n"
                            f"**Base Commit:** `{base_sha[:8]}` | **Target Commit:** `{target_sha[:8]}`\n\n"
                            f"#### Categorized Summary:\n"
                            + "\n".join([f"- {s}" for s in summary.categorized_summaries])
                            + "\n\n*(Note: GEMINI_API_KEY is unconfigured/offline. AST diff evidence computed directly.)*"
                        )

            except Exception as e:
                st.error(f"Semantic comparison error: {e}")

# ---------------------------------------------------------
# TAB 4: CHANGEGRAPH
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
# TAB 5: GROUNDED COPILOT
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
