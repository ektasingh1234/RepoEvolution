from typing import List, Dict, Set, Optional
from src.driftguard.history_analyzer import HistoricalCommitSnapshot
from src.core.models import CodeEntity, EntityType


class HistoricalPattern:
    """Represents a learned deterministic historical repository pattern."""
    def __init__(
        self,
        pattern_key: str,
        pattern_type: str,  # "DEPENDENCY", "API", "STRUCTURAL"
        entity_name: str,
        expected_value: str,
        source_commits: List[str],
        frequency: int,
        confidence: float,
        evidence: str
    ):
        self.pattern_key = pattern_key
        self.pattern_type = pattern_type
        self.entity_name = entity_name
        self.expected_value = expected_value
        self.source_commits = source_commits
        self.frequency = frequency
        self.confidence = confidence
        self.evidence = evidence


class PatternExtractor:
    """
    Extracts deterministic historical patterns (Dependency, API, Structural)
    from historical commit snapshots.
    """

    @staticmethod
    def extract_patterns(snapshots: List[HistoricalCommitSnapshot]) -> Dict[str, HistoricalPattern]:
        """
        Build pattern lookup map from historical commit sequence.
        """
        patterns: Dict[str, HistoricalPattern] = {}
        total_snapshots = len(snapshots)
        if total_snapshots == 0:
            return patterns

        # Track occurrences across snapshots
        # 1. Dependency Patterns: {caller_entity_name: {target_dep_name: [commit_shas]}}
        dep_history: Dict[str, Dict[str, List[str]]] = {}
        # 2. API Signature Patterns: {entity_name: {signature_str: [commit_shas]}}
        api_history: Dict[str, Dict[str, List[str]]] = {}
        # 3. Structural File Patterns: {entity_name: {file_path: [commit_shas]}}
        struct_history: Dict[str, Dict[str, List[str]]] = {}

        # Entity snapshot counts (how many commits contained entity X)
        entity_commit_counts: Dict[str, Set[str]] = {}

        for snap in snapshots:
            sha = snap.commit_sha
            for entity in snap.entities:
                name = entity.name
                entity_commit_counts.setdefault(name, set()).add(sha)

                # Track Dependencies
                for dep in entity.dependencies:
                    dep_history.setdefault(name, {}).setdefault(dep, []).append(sha)

                # Track API Signature
                api_history.setdefault(name, {}).setdefault(entity.signature, []).append(sha)

                # Track Structural File Path
                struct_history.setdefault(name, {}).setdefault(entity.file_path, []).append(sha)

        # 1. Build Dependency Patterns
        for caller, targets in dep_history.items():
            total_caller_commits = len(entity_commit_counts.get(caller, set()))
            for target_dep, shas in targets.items():
                unique_shas = list(set(shas))
                freq = len(unique_shas)
                confidence = round(freq / total_caller_commits, 2) if total_caller_commits > 0 else 0.0

                key = f"dep::{caller}->{target_dep}"
                patterns[key] = HistoricalPattern(
                    pattern_key=key,
                    pattern_type="DEPENDENCY",
                    entity_name=caller,
                    expected_value=target_dep,
                    source_commits=unique_shas,
                    frequency=freq,
                    confidence=confidence,
                    evidence=f"Historical entity '{caller}' called '{target_dep}' in {freq}/{total_caller_commits} historical commits (confidence: {confidence:.2f})."
                )

        # 2. Build API Signature Patterns
        for entity_name, sigs in api_history.items():
            total_entity_commits = len(entity_commit_counts.get(entity_name, set()))
            for sig, shas in sigs.items():
                unique_shas = list(set(shas))
                freq = len(unique_shas)
                confidence = round(freq / total_entity_commits, 2) if total_entity_commits > 0 else 0.0

                key = f"api::{entity_name}"
                # If multiple signatures exist in history, pick highest frequency as primary pattern
                if key not in patterns or confidence > patterns[key].confidence:
                    patterns[key] = HistoricalPattern(
                        pattern_key=key,
                        pattern_type="API",
                        entity_name=entity_name,
                        expected_value=sig,
                        source_commits=unique_shas,
                        frequency=freq,
                        confidence=confidence,
                        evidence=f"Historical entity '{entity_name}' maintained signature '{sig}' in {freq}/{total_entity_commits} commits (confidence: {confidence:.2f})."
                    )

        # 3. Build Structural Patterns
        for entity_name, files in struct_history.items():
            total_entity_commits = len(entity_commit_counts.get(entity_name, set()))
            for file_path, shas in files.items():
                unique_shas = list(set(shas))
                freq = len(unique_shas)
                confidence = round(freq / total_entity_commits, 2) if total_entity_commits > 0 else 0.0

                key = f"struct::{entity_name}"
                if key not in patterns or confidence > patterns[key].confidence:
                    patterns[key] = HistoricalPattern(
                        pattern_key=key,
                        pattern_type="STRUCTURAL",
                        entity_name=entity_name,
                        expected_value=file_path,
                        source_commits=unique_shas,
                        frequency=freq,
                        confidence=confidence,
                        evidence=f"Historical entity '{entity_name}' resided in '{file_path}' in {freq}/{total_entity_commits} commits (confidence: {confidence:.2f})."
                    )

        return patterns
