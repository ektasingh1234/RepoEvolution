import difflib
from typing import List, Dict, Tuple, Optional
import numpy as np

from src.core.models import (
    CodeEntity, SemanticEntityDiff, SemanticChangeType, EntityType
)

try:
    from sentence_transformers import SentenceTransformer
    from src.core.config import settings
    HAVE_EMBEDDINGS = True
except ImportError:
    HAVE_EMBEDDINGS = False


class SemanticEntityDiffEngine:
    """
    Compares Abstract Syntax Tree (AST) entities between two repository commits.
    Detects ADDED, REMOVED, MODIFIED, RENAMED, SIGNATURE_CHANGED, DEPENDENCY_CHANGED, DOCSTRING_CHANGED.
    """

    def __init__(self):
        self.embed_model = None
        if HAVE_EMBEDDINGS:
            try:
                self.embed_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            except Exception:
                self.embed_model = None

    def _compute_text_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity score using SentenceTransformers or SequenceMatcher fallback."""
        if not text1 or not text2:
            return 0.0
        if text1 == text2:
            return 1.0

        if self.embed_model:
            try:
                vecs = self.embed_model.encode([text1, text2], normalize_embeddings=True)
                sim = float(np.dot(vecs[0], vecs[1]))
                return max(0.0, min(1.0, round(sim, 4)))
            except Exception:
                pass

        # Fallback to SequenceMatcher
        return round(difflib.SequenceMatcher(None, text1, text2).ratio(), 4)

    def diff_entities(
        self, base_entities: List[CodeEntity], target_entities: List[CodeEntity]
    ) -> List[SemanticEntityDiff]:
        """
        Perform AST entity diff between base and target commit snapshots.
        """
        diffs: List[SemanticEntityDiff] = []

        base_map: Dict[str, CodeEntity] = {e.id: e for e in base_entities}
        target_map: Dict[str, CodeEntity] = {e.id: e for e in target_entities}

        matched_base_ids = set()
        matched_target_ids = set()

        # 1. Exact ID Matches (Same File & Entity Name)
        common_ids = set(base_map.keys()).intersection(set(target_map.keys()))
        for entity_id in common_ids:
            base_e = base_map[entity_id]
            target_e = target_map[entity_id]
            matched_base_ids.add(entity_id)
            matched_target_ids.add(entity_id)

            # Check for changes
            self._compare_matching_entities(base_e, target_e, diffs)

        # 2. Unmatched Entities - Check for RENAMED or Moved Entities
        unmatched_base = [e for eid, e in base_map.items() if eid not in matched_base_ids]
        unmatched_target = [e for eid, e in target_map.items() if eid not in matched_target_ids]

        for base_e in unmatched_base:
            best_match: Optional[CodeEntity] = None
            best_score = 0.0

            for target_e in unmatched_target:
                if target_e.id in matched_target_ids:
                    continue
                # Only match entities of the same type (class to class, func to func)
                if base_e.entity_type == target_e.entity_type:
                    sim = self._compute_text_similarity(base_e.code_content, target_e.code_content)
                    if sim > 0.70 and sim > best_score:
                        best_score = sim
                        best_match = target_e

            if best_match:
                matched_base_ids.add(base_e.id)
                matched_target_ids.add(best_match.id)

                diffs.append(
                    SemanticEntityDiff(
                        change_id=f"rename::{base_e.id}->{best_match.id}",
                        entity_type=base_e.entity_type,
                        entity_name=f"{base_e.name} -> {best_match.name}",
                        file_before=base_e.file_path,
                        file_after=best_match.file_path,
                        change_type=SemanticChangeType.RENAMED,
                        similarity_score=best_score,
                        before_summary=base_e.signature,
                        after_summary=best_match.signature,
                        affected_dependencies=best_match.dependencies,
                        evidence=f"Entity '{base_e.name}' in '{base_e.file_path}' was renamed/moved to '{best_match.name}' in '{best_match.file_path}' (similarity: {best_score:.2f})."
                    )
                )

        # 3. Process Remaining ADDED Entities
        for target_e in unmatched_target:
            if target_e.id not in matched_target_ids:
                diffs.append(
                    SemanticEntityDiff(
                        change_id=f"added::{target_e.id}",
                        entity_type=target_e.entity_type,
                        entity_name=target_e.name,
                        file_before=None,
                        file_after=target_e.file_path,
                        change_type=SemanticChangeType.ADDED,
                        similarity_score=1.0,
                        before_summary=None,
                        after_summary=target_e.signature,
                        affected_dependencies=target_e.dependencies,
                        evidence=f"New {target_e.entity_type.value} '{target_e.name}' added in '{target_e.file_path}' (Lines {target_e.start_line}-{target_e.end_line})."
                    )
                )

        # 4. Process Remaining REMOVED Entities
        for base_e in unmatched_base:
            if base_e.id not in matched_base_ids:
                diffs.append(
                    SemanticEntityDiff(
                        change_id=f"removed::{base_e.id}",
                        entity_type=base_e.entity_type,
                        entity_name=base_e.name,
                        file_before=base_e.file_path,
                        file_after=None,
                        change_type=SemanticChangeType.REMOVED,
                        similarity_score=0.0,
                        before_summary=base_e.signature,
                        after_summary=None,
                        affected_dependencies=base_e.dependencies,
                        evidence=f"{base_e.entity_type.value.capitalize()} '{base_e.name}' was removed from '{base_e.file_path}'."
                    )
                )

        return diffs

    def _compare_matching_entities(
        self, base_e: CodeEntity, target_e: CodeEntity, diffs: List[SemanticEntityDiff]
    ):
        """Analyze differences between base and target versions of the same entity."""
        # Check signature change
        if base_e.signature != target_e.signature:
            diffs.append(
                SemanticEntityDiff(
                    change_id=f"sig::{base_e.id}",
                    entity_type=base_e.entity_type,
                    entity_name=base_e.name,
                    file_before=base_e.file_path,
                    file_after=target_e.file_path,
                    change_type=SemanticChangeType.SIGNATURE_CHANGED,
                    similarity_score=self._compute_text_similarity(base_e.signature, target_e.signature),
                    before_summary=base_e.signature,
                    after_summary=target_e.signature,
                    affected_dependencies=target_e.dependencies,
                    evidence=f"Signature for '{base_e.name}' changed from '{base_e.signature}' to '{target_e.signature}'."
                )
            )

        # Check dependency change
        base_deps_set = set(base_e.dependencies)
        target_deps_set = set(target_e.dependencies)
        if base_deps_set != target_deps_set:
            added_deps = list(target_deps_set - base_deps_set)
            removed_deps = list(base_deps_set - target_deps_set)
            ev = f"Dependencies for '{base_e.name}' changed."
            if added_deps:
                ev += f" Added calls: {added_deps}."
            if removed_deps:
                ev += f" Removed calls: {removed_deps}."

            diffs.append(
                SemanticEntityDiff(
                    change_id=f"dep::{base_e.id}",
                    entity_type=base_e.entity_type,
                    entity_name=base_e.name,
                    file_before=base_e.file_path,
                    file_after=target_e.file_path,
                    change_type=SemanticChangeType.DEPENDENCY_CHANGED,
                    similarity_score=0.9,
                    before_summary=f"Calls: {base_e.dependencies}",
                    after_summary=f"Calls: {target_e.dependencies}",
                    affected_dependencies=list(target_deps_set.union(base_deps_set)),
                    evidence=ev
                )
            )

        # Check docstring change
        if base_e.docstring != target_e.docstring:
            diffs.append(
                SemanticEntityDiff(
                    change_id=f"doc::{base_e.id}",
                    entity_type=base_e.entity_type,
                    entity_name=base_e.name,
                    file_before=base_e.file_path,
                    file_after=target_e.file_path,
                    change_type=SemanticChangeType.DOCSTRING_CHANGED,
                    similarity_score=self._compute_text_similarity(base_e.docstring or "", target_e.docstring or ""),
                    before_summary=base_e.docstring,
                    after_summary=target_e.docstring,
                    affected_dependencies=target_e.dependencies,
                    evidence=f"Docstring updated for '{base_e.name}' in '{base_e.file_path}'."
                )
            )

        # Check logic mutation (body hash differs)
        if base_e.content_hash != target_e.content_hash:
            sim_score = self._compute_text_similarity(base_e.code_content, target_e.code_content)
            diffs.append(
                SemanticEntityDiff(
                    change_id=f"mod::{base_e.id}",
                    entity_type=base_e.entity_type,
                    entity_name=base_e.name,
                    file_before=base_e.file_path,
                    file_after=target_e.file_path,
                    change_type=SemanticChangeType.MODIFIED,
                    similarity_score=sim_score,
                    before_summary=base_e.signature,
                    after_summary=target_e.signature,
                    affected_dependencies=target_e.dependencies,
                    evidence=f"Internal code logic mutated in '{base_e.name}' (similarity: {sim_score:.2f})."
                )
            )
