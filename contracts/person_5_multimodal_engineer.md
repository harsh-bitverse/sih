# PERSON 5 — MULTIMODAL ENGINEER

## Final-system ownership

Own:

- OCR
- scanned PDF processing
- image processing
- visual reasoning
- document modality handling
- multimodal evidence extraction
- visual provenance
- P&ID/engineering drawing understanding

## MVP subsystem

Build:

```text
PDF
Image
Scanned document
Table
      ↓
Multimodal pipeline
      ↓
Model Registry
      ↓
Structured evidence
```

Demo requirement:

```text
scanned inspection report
+
equipment photograph
        ↓
multimodal analysis
        ↓
structured findings
```

No need for a huge generalized multimodal platform.

## 5. Multimodal subsystem

This one is slightly different because its input can contain different modalities.

### Input: `MultimodalRequest`

```text
MultimodalRequest
├── request_context
├── objective
├── context
├── resources[]
├── input_modalities[]
├── required_output
├── output_schema?
└── constraints[]
```

For example:

```text
objective:
    "Identify safety findings in these inspection photographs."

resources:
    [
        equipment_photo.png,
        inspection_report.pdf
    ]

required_output:
    "Structured safety findings with visual evidence."
```

## 6. Output: `MultimodalResult`

```text
MultimodalResult
├── request_context
├── status
├── structured_output
├── evidence[]
├── artifacts[]
├── provenance[]
├── confidence?
└── errors[]
```

The crucial thing is that the output is **request-relative structured evidence**.

For example:

```text
structured_output:

{
    "findings": [
        {
            "finding": "Visible corrosion around flange",
            "location": {
                "image": "equipment_photo.png",
                "region": [x1, y1, x2, y2]
            },
            "confidence": 0.91
        }
    ]
}
```

Or for a scanned PDF:

```text
{
    "measurements": [
        {
            "value": 4.2,
            "unit": "mm",
            "page": 7,
            "source_region": ...
        }
    ]
}
```

## 7. What Multimodal internally does

This is important for Person 5.

```text
MultimodalRequest
        |
        ▼
Identify resource types
        |
        ├── PDF
        ├── image
        ├── scanned document
        ├── table
        └── engineering drawing
        |
        ▼
Prepare/process resources
        |
        ▼
Break multimodal work into necessary internal operations
        |
        ▼
Request suitable model capability
        |
        ▼
Model Registry
        |
        ▼
Local multimodal model(s)
        |
        ▼
Interpret results relative to original request
        |
        ▼
Structured evidence
        |
        ▼
MultimodalResult
```

And this is where your earlier insight matters:

Multimodal Engineer does not hard-code:

```text
PDF → Model A
Table → Model B
Image → Model C
```

It asks Model Registry for the capability it needs.

```text
resources[] = RetrievedResource | Artifact | ResourceReference
```

or, even simpler for MVP:

> `MultimodalRequest.resources[]` accepts the `RetrievedResource` objects returned by Retrieval, as well as user-provided/previously generated `Artifact` references.
