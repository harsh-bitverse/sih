# Sovereign On-Premise Agentic AI Workbench

Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs for Confidential Industrial Work (SIH 2026).

---

## Subsystem Ownership Matrix

| Developer | Role | Owned Subsystem Path(s) |
| :--- | :--- | :--- |
| **Developer 1** | System Architect | `src/workbench/core/`, `src/workbench/workbench/`, `src/workbench/planner/`, `src/workbench/workflow/`, `src/workbench/synthesis/`, `src/workbench/ui/`, `tests/integration/`, `docs/contracts/` |
| **Developer 2** | Model Engineer | `src/workbench/models/` |
| **Developer 3** | Retrieval Engineer | `src/workbench/retrieval/` |
| **Developer 4** | Multimodal Engineer | `src/workbench/multimodal/` |
| **Developer 5** | Tool/Sandbox Engineer | `src/workbench/tools/` |
| **Developer 6** | Security/Audit Engineer | `src/workbench/security/` |

---

## Developer Workflow & Git Rules

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd sih
   ```
2. **Create Personal Feature Branch**:
   - Create and switch to your feature branch before starting work (e.g., `git checkout -b dev-2-models`).
   - Do NOT work directly on the main branch.
3. **Work Inside Your Owned Subsystem**:
   - Limit code modifications strictly to your assigned directory/module as outlined in the Ownership Matrix above.
   - Do NOT introduce developer-specific folders. Folders represent system architecture; branches represent developer ownership.
4. **Respect Architectural & Dependency Rules**:
   - Do NOT import internal implementation modules of another subsystem directly.
   - Communicate strictly across defined interfaces and shared contracts (`src/workbench/core/` and subsystem schemas).
   - Maintain zero-egress and security audit constraints.
5. **Coordinate Contract Changes**:
   - All shared contracts in `docs/contracts/` and `src/workbench/core/` are architecturally controlled.
   - If your subsystem implementation requires updates to cross-subsystem contracts, coordinate changes with Developer 1 (System Architect).
6. **Add Unit & Subsystem Tests**:
   - Place unit tests inside `tests/unit/` mirroring your subsystem structure.
   - Integration tests in `tests/integration/` are managed by the System Architect, though contributions of subsystem contract verification tests are encouraged.
7. **No Direct Inter-Branch Merges**:
   - Do NOT merge your branch directly into another developer's branch.
   - All integrations occur through Pull Requests / Merges into `main`, coordinated by the System Architect.

---

## Running Smoke & Integration Tests

```bash
python -m pytest tests/integration/test_smoke.py
```
