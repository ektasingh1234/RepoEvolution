# Prompt Engineering & Effectiveness Audit: REPOEVOLUTION

This document presents the prompt engineering design, audit criteria, evidence-grounding constraints, and output structure for all version-controlled prompt templates in **REPOEVOLUTION**.

---

## 1. Prompt Inventory & System Roles

| Prompt Template File | Target Component | System Role | Primary Output Objective |
| :--- | :--- | :--- | :--- |
| `prompts/system_copilot.txt` | Grounded Copilot | Repository Q&A Assistant | Evidence-grounded answers with exact file/line markdown citations |
| `prompts/prompt_semantic_diff.txt` | SemanticDiff Engine | Git Evolution Analyzer | Architectural rationale & change significance from AST diff evidence |
| `prompts/driftguard_system.txt` | DriftGuard Engine | Architectural Pattern Auditor | Explanation of historical pattern divergence & review recommendations |
| `prompts/prompt_rationale.txt` | Archaeologist / Commit Rationale | Evolutionary Historian | Extraction of developer intent vs AST code mutations |
| `prompts/prompt_drift.txt` | Doc & Test Drift Checker | Consistency Auditor | Discrepancy flagging between AST entities, docstrings, and tests |

---

## 2. Evidence Grounding & Uncertainty Audit

Each prompt template enforces five strict operational constraints:

1. **Strict Context Scoping**: The LLM is instructed to answer ONLY using the provided `<repository_evidence>` or `<semantic_diff_evidence>` XML payload.
2. **Anti-Hallucination Guardrails**: Explicit instruction: *"Do NOT invent functions, files, arguments, logic, or history that are not supported by evidence."*
3. **Explicit Uncertainty Handling**: When evidence is missing or insufficient, the model is required to emit a standard fallback phrase:
   * Copilot: `"Based on the available repository evidence, this detail cannot be verified."`
   * SemanticDiff: `"Based on available diff evidence, developer rationale cannot be verified."`
   * DriftGuard: `"Based on available repository history, historical pattern confidence is insufficient to declare definitive architectural drift."`
4. **Markdown Citation Formatting**: All code claims must cite exact line ranges: `[file_path:start_line-end_line]` or `[commit_sha]`.
5. **Deterministic Output Structure**: Headers for **What Changed**, **Historical Pattern**, **Current Implementation**, **Affected Components**, and **Review Recommendations**.

---

## 3. Detailed Audit Matrix

### A. Grounded Copilot (`prompts/system_copilot.txt`)
* **Purpose**: Conversational developer assistant answering codebase queries.
* **Input Context**: Hybrid retrieved AST code snippets, class signatures, docstrings, and call dependencies.
* **Grounding Rule**: Enforces direct file/line markdown links for all code symbols.
* **Audit Result**: Passed — Answers strictly reference retrieved AST entities without fabricating API methods.

### B. SemanticDiff Explanation (`prompts/prompt_semantic_diff.txt`)
* **Purpose**: Explain architectural impact between two Git commit SHAs.
* **Input Context**: AST change categories (`ADDED`, `REMOVED`, `MODIFIED`, `SIGNATURE_CHANGED`, `DEPENDENCY_CHANGED`, `RENAMED`), similarity scores, before/after signatures.
* **Grounding Rule**: Explains significance without guessing unevidenced business rationale.
* **Audit Result**: Passed — Grounded in diff evidence payloads.

### C. DriftGuard Explanation (`prompts/driftguard_system.txt`)
* **Purpose**: Explain architectural pattern drift across historical commits.
* **Input Context**: Deterministic drift findings (`DEPENDENCY_DRIFT`, `API_DRIFT`, `STRUCTURAL_DRIFT`), historical patterns, supporting commit SHAs, pattern confidence.
* **Grounding Rule**: Deterministic engine determines drift existence; prompt ONLY explains the evidence payload.
* **Audit Result**: Passed — Zero hallucinated historical patterns.

---

## 4. Example Prompt Payload & Response Audit

### Input Payload Example (`prompts/driftguard_system.txt`)
```xml
<driftguard_evidence>
Target Commit: e75a4f22
Min Confidence Threshold: 0.70
Total Drift Findings: 1

Structured Findings:
[DEPENDENCY_DRIFT] (HIGH) Entity: 'process_payment'
  Historical Pattern: Consistently called 'PaymentRepository' (3 commits)
  Current Pattern: Calls: ['DirectDatabaseClient', 'query']
  Evidence Commits: ['c1_sha', 'c2_sha', 'c3_sha']
  Confidence: 1.00
  Recommendation Basis: Review if replacing 'PaymentRepository' breaks established architectural contract in 'payment_service.py'.
</driftguard_evidence>
```

### Audited LLM Output
```markdown
### Architectural Drift Analysis

1. **What Changed**: Function `process_payment` in `payment_service.py` replaced its internal call to `PaymentRepository` with `DirectDatabaseClient`.
2. **Historical Pattern Detected**: Across 3 prior commits (`c1_sha`, `c2_sha`, `c3_sha`), `process_payment` consistently relied on `PaymentRepository` (Confidence: 1.00).
3. **Architectural Significance**: Swapping the repository abstraction for direct database client calls bypasses established data access patterns.
4. **Developer Review Recommendation**: Verify if bypassing `PaymentRepository` violates persistence architecture guidelines for `payment_service.py`.
```

---

## 5. Targeted Improvements Made

* Standardized uncertainty fallback instructions across all 5 prompt files.
* Enhanced markdown citation directives to mandate line range numbers (`#Lstart-Lend`).
* Confirmed that LLM prompts receive structured JSON/XML payloads rather than raw codebase dumps.
