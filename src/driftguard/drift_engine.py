from typing import List, Dict
from src.core.models import CodeEntity, DriftFinding, DriftType, DriftSeverity
from src.driftguard.pattern_extractor import HistoricalPattern


class DriftDetectionEngine:
    """
    Compares current repository AST entities against learned historical patterns.
    Reports DEPENDENCY_DRIFT, API_DRIFT, STRUCTURAL_DRIFT only when confidence >= min_confidence.
    """

    def __init__(self, min_confidence: float = 0.70, min_frequency: int = 2):
        self.min_confidence = min_confidence
        self.min_frequency = min_frequency

    def _determine_severity(self, confidence: float) -> DriftSeverity:
        if confidence >= 0.85:
            return DriftSeverity.HIGH
        elif confidence >= 0.70:
            return DriftSeverity.MEDIUM
        return DriftSeverity.LOW

    def detect_drift(
        self, target_entities: List[CodeEntity], patterns: Dict[str, HistoricalPattern]
    ) -> List[DriftFinding]:
        findings: List[DriftFinding] = []
        if not target_entities or not patterns:
            return findings

        entity_map: Dict[str, CodeEntity] = {e.name: e for e in target_entities}

        for pattern_key, pattern in patterns.items():
            # Skip patterns with insufficient historical confidence or frequency count (< min_frequency)
            if pattern.confidence < self.min_confidence or pattern.frequency < self.min_frequency:
                continue

            entity_name = pattern.entity_name
            current_entity = entity_map.get(entity_name)

            # If current entity no longer exists, skip (handled by SemanticDiff REMOVED)
            if not current_entity:
                continue

            # 1. DEPENDENCY DRIFT DETECTION
            if pattern.pattern_type == "DEPENDENCY":
                expected_dep = pattern.expected_value
                current_deps = current_entity.dependencies

                if expected_dep not in current_deps:
                    # Current entity dropped expected historical dependency or switched to another client
                    current_pattern_str = f"Calls: {current_deps if current_deps else 'None'}"
                    hist_pattern_str = f"Consistently called '{expected_dep}' ({pattern.frequency} commits)"

                    findings.append(
                        DriftFinding(
                            drift_id=f"dep_drift::{entity_name}->{expected_dep}",
                            drift_type=DriftType.DEPENDENCY_DRIFT,
                            severity=self._determine_severity(pattern.confidence),
                            entity=entity_name,
                            description=f"Entity '{entity_name}' diverged from historical dependency '{expected_dep}'.",
                            historical_pattern=hist_pattern_str,
                            current_pattern=current_pattern_str,
                            evidence_commits=pattern.source_commits,
                            evidence_entities=[f"{current_entity.file_path}::{entity_name}"],
                            confidence=pattern.confidence,
                            recommendation_basis=f"Review if replacing '{expected_dep}' breaks established architectural contract in '{current_entity.file_path}'."
                        )
                    )

            # 2. API DRIFT DETECTION
            elif pattern.pattern_type == "API":
                expected_sig = pattern.expected_value
                current_sig = current_entity.signature

                if current_sig != expected_sig:
                    findings.append(
                        DriftFinding(
                            drift_id=f"api_drift::{entity_name}",
                            drift_type=DriftType.API_DRIFT,
                            severity=self._determine_severity(pattern.confidence),
                            entity=entity_name,
                            description=f"API signature for '{entity_name}' diverged from established historical signature.",
                            historical_pattern=f"Signature: '{expected_sig}' ({pattern.frequency} commits)",
                            current_pattern=f"Signature: '{current_sig}'",
                            evidence_commits=pattern.source_commits,
                            evidence_entities=[f"{current_entity.file_path}::{entity_name}"],
                            confidence=pattern.confidence,
                            recommendation_basis=f"Verify if consumers of '{entity_name}' are impacted by this signature change in '{current_entity.file_path}'."
                        )
                    )

            # 3. STRUCTURAL DRIFT DETECTION
            elif pattern.pattern_type == "STRUCTURAL":
                expected_file = pattern.expected_value
                current_file = current_entity.file_path

                if current_file != expected_file:
                    findings.append(
                        DriftFinding(
                            drift_id=f"struct_drift::{entity_name}",
                            drift_type=DriftType.STRUCTURAL_DRIFT,
                            severity=self._determine_severity(pattern.confidence),
                            entity=entity_name,
                            description=f"File location for '{entity_name}' moved from established historical module path.",
                            historical_pattern=f"Resided in '{expected_file}' ({pattern.frequency} commits)",
                            current_pattern=f"Resided in '{current_file}'",
                            evidence_commits=pattern.source_commits,
                            evidence_entities=[f"{current_file}::{entity_name}"],
                            confidence=pattern.confidence,
                            recommendation_basis=f"Check if moving '{entity_name}' to '{current_file}' violates module architecture guidelines."
                        )
                    )

        return findings
