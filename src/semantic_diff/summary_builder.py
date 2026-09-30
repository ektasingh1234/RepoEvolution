from typing import List, Dict
from src.core.models import SemanticEntityDiff, SemanticDiffSummary, SemanticChangeType


class SemanticSummaryBuilder:
    """
    Aggregates low-level AST entity diffs into structured summary statistics
    and evidence-grounded high-level change categories.
    """

    @staticmethod
    def build_summary(diffs: List[SemanticEntityDiff]) -> SemanticDiffSummary:
        added = sum(1 for d in diffs if d.change_type == SemanticChangeType.ADDED)
        removed = sum(1 for d in diffs if d.change_type == SemanticChangeType.REMOVED)
        modified = sum(1 for d in diffs if d.change_type == SemanticChangeType.MODIFIED)
        sig_changed = sum(1 for d in diffs if d.change_type == SemanticChangeType.SIGNATURE_CHANGED)
        renamed = sum(1 for d in diffs if d.change_type == SemanticChangeType.RENAMED)
        dep_changed = sum(1 for d in diffs if d.change_type == SemanticChangeType.DEPENDENCY_CHANGED)

        # Group by file/module to form evidence-grounded high-level summary statements
        file_diff_map: Dict[str, List[SemanticEntityDiff]] = {}
        for d in diffs:
            file_key = d.file_after or d.file_before or "unknown_file"
            file_diff_map.setdefault(file_key, []).append(d)

        categorized_statements: List[str] = []
        for file_path, file_diffs in file_diff_map.items():
            types_summary = []
            file_added = sum(1 for d in file_diffs if d.change_type == SemanticChangeType.ADDED)
            file_mod = sum(1 for d in file_diffs if d.change_type == SemanticChangeType.MODIFIED)
            file_sig = sum(1 for d in file_diffs if d.change_type == SemanticChangeType.SIGNATURE_CHANGED)
            file_rem = sum(1 for d in file_diffs if d.change_type == SemanticChangeType.REMOVED)
            file_ren = sum(1 for d in file_diffs if d.change_type == SemanticChangeType.RENAMED)

            if file_added:
                types_summary.append(f"{file_added} added")
            if file_mod:
                types_summary.append(f"{file_mod} mutated")
            if file_sig:
                types_summary.append(f"{file_sig} signature updated")
            if file_rem:
                types_summary.append(f"{file_rem} removed")
            if file_ren:
                types_summary.append(f"{file_ren} renamed/moved")

            summary_line = f"Module '{file_path}': {', '.join(types_summary)}."
            categorized_statements.append(summary_line)

        if not categorized_statements:
            categorized_statements.append("No semantic AST changes detected between commits.")

        return SemanticDiffSummary(
            total_added=added,
            total_removed=removed,
            total_modified=modified,
            total_signature_changed=sig_changed,
            total_renamed=renamed,
            total_dependency_changed=dep_changed,
            categorized_summaries=categorized_statements
        )
