# Multimodal & Vision Subsystem

Owner: Developer 4 (Multimodal Engineer)
Status: slice 1 complete — resource → OCR → traceable evidence
Tests: 60 in `tests/unit/multimodal/`

## What this subsystem does
Resolves a `ResourceReference`, renders its pages, extracts evidence, and
returns `MultimodalResult`. It does not retrieve, plan, orchestrate, or
interpret what the evidence means.

## Entry points
| Class | Use |
|---|---|
| `DefaultMultimodalProcessor.process(request)` | **Preferred.** Full result: evidence + artifacts + errors + metadata |
| `TesseractOCREngine.extract_text(resource)` | Evidence only. No `Artifact` records — those need a `task_id` from `RequestContext` |
| `OcrDocumentParser.parse_document(resource)` | Convenience wrapper; context supplied at construction |
| `VisionEngine.analyze_image(...)` | Not implemented — slice 2, blocked on hardware |

```python
processor = DefaultMultimodalProcessor(
    backend=TesseractOcrBackend(),
    resolver=PathResourceResolver(allowed_roots=["/data/inbox"]),
    artifact_store=LocalArtifactStore("outputs/multimodal_artifacts"),
    dpi=300,
)
result = processor.process(request)
```

Everything concrete is injected. Swapping Tesseract for PaddleOCR means adding
one adapter behind `OcrBackend` and changing one line of wiring.

## Internal layout
| path | role |
|---|---|
| `schemas.py` | our contract (`MultimodalRequest` / `MultimodalResult`) |
| `processor.py`, `ocr.py`, `vision.py`, `document.py` | public interfaces + implementations |
| `ports/` | interfaces for what we use but don't own |
| `adapters/` | swappable implementations |
| `pipeline/` | internal logic and strongly-typed internal model |
| `mapping.py` | the only module that converts internal → core contract types |

Rule: `pipeline/` imports `ports/`, never `adapters/`.

## Traceability
```
ResourceReference → document_hash → page image Artifact (art_<hash>)
                                  → Evidence (region on that artifact)
```
IDs are content-derived, so a re-run reproduces them exactly.
`python scripts/multimodal_demo.py <file> --audit` walks the chain.

Region data is in `Evidence.provenance["region"]` as structured numbers, with
a readable summary in `Evidence.location`. A UI highlighting a region needs
the numbers, not a string to re-parse.

## Status semantics
- `SUCCESS` — evidence produced, no errors
- `PARTIAL` — evidence produced, some pages or steps failed (see `errors`)
- `FAILED` — no usable evidence

Useful evidence is never discarded because something else failed. Per-document
failures return a `FAILED` result, never a raised exception.

## Confidence
Per-evidence only, always with `confidence_source`. **No aggregate is ever
computed.** `OCR_ENGINE` values are measured by the decoder; `VISION_MODEL`
values (slice 2) are self-reported by a model and are not calibrated
probabilities. Averaging them yields a number that looks meaningful and is not.

## Security
1. `uri_or_path` is a request to read, never authorisation. `PathResourceResolver`
   normalises the path, requires containment in a configured allowed root,
   checks `resource_type`, and refuses every URI scheme (zero-egress). Deny by
   default: no roots configured means nothing resolves.
   See `tests/unit/multimodal/test_resolver_security.py` — do not weaken these.
2. `Evidence.content` is UNTRUSTED text from a user document and may contain
   adversarial instructions. Consumers must embed it as quoted data with its
   source, never in instruction position. System-wide concern.

## Dependencies needed in pyproject.toml
`pymupdf`, `pytesseract`, `pillow` — plus the Tesseract binary on PATH.
`pyproject.toml` is outside this subsystem; requested from Developer 1.

## Open with the System Architect
- Should `Evidence.location` stay free-text, or gain a structured region field?
- Should derived page images register in a system-wide artifact registry so
  other subsystems can fetch them, rather than our local store?
- Do we emit audit events ourselves, or does the orchestrator wrap our result?
- Hardware for a local open-weight vision model — blocking slice 2.
