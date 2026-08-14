# GLiNER2 NER for Knowledge Graph Construction

## Overview

This project fine-tunes **GLiNER2** to build the **Named Entity Recognition (NER) layer of a Knowledge Graph construction pipeline**.

The goal is not to create a generic NER model. The goal is to reliably identify the entities that will become **nodes in a Knowledge Graph**, which can later be connected through relation extraction and stored in a graph database.

The final NER model is designed for seven entity types:

- `PERSON`
- `ORG`
- `GPE`
- `EVENT`
- `DATE`
- `TIME`
- `QUANTITY`

These entities are particularly useful for extracting structured information from news, reports, articles, and other unstructured text before constructing the Knowledge Graph.

---

## Knowledge Graph Pipeline

The NER model represents the first major information-extraction stage of the Knowledge Graph pipeline.

```text
Raw Documents
     │
     ▼
Text Extraction / Preprocessing
     │
     ▼
GLiNER2 NER
     │
     ├── PERSON
     ├── ORG
     ├── GPE
     ├── EVENT
     ├── DATE
     ├── TIME
     └── QUANTITY
     │
     ▼
Entity Normalization / Deduplication
     │
     ▼
Relation Extraction
     │
     ▼
Knowledge Graph
     │
     ├── Entity Nodes
     └── Relationship Edges
```

The purpose of this fine-tuning stage is therefore to produce **high-quality entity candidates for downstream Knowledge Graph construction**.

---

## Entity Ontology

| Entity | Description | Example |
|---|---|---|
| `PERSON` | Individual people | Donald Trump |
| `ORG` | Organizations, companies, institutions, agencies, groups | NATO |
| `GPE` | Geopolitical entities | Iran, India, Washington |
| `EVENT` | Named events, conflicts, operations, disasters, incidents | Iran War |
| `DATE` | Calendar dates and date expressions | August 14, 2026 |
| `TIME` | Clock times and time-of-day expressions | 5 PM |
| `QUANTITY` | Measured quantities, amounts, counts, or numeric quantities with units | 500 soldiers |

---

# Training Data Strategy

Two datasets are being combined because neither source provides all the entity types required for the Knowledge Graph.

### Dataset 1 — TNER OntoNotes5

The TNER OntoNotes5 dataset is used as the trusted source for:

```text
PERSON
ORG
DATE
TIME
QUANTITY
```

The notebook loads the dataset from Hugging Face and reads its `ClassLabel` metadata rather than assuming numeric tag IDs.

The original BIO/BIOES-style annotations are converted into entity spans and only the required OntoNotes labels are retained.

### Dataset 2 — `combined_output.jsonl`

The second dataset is used as the trusted source for:

```text
GPE
EVENT
```

Only these two labels are taken from Dataset 2.

---

# Why We Do Not Simply Merge the Labels

A major problem is that the two datasets have **different annotation coverage**.

For example, Dataset 2 may contain:

```text
PERSON + ORG + GPE + EVENT
```

but we only trust its `GPE` and `EVENT` annotations.

If we simply remove the `PERSON` and `ORG` annotations and train the unified model, the model could incorrectly learn that those entities are **not entities** in Dataset 2.

That would introduce false-negative supervision.

Therefore, the project deliberately keeps the complete sentence while treating the missing labels as **unknown**, rather than explicitly treating them as negative examples.

---

# Two-Stage Specialist Training

To reduce the annotation-coverage problem, the training process first creates two specialist GLiNER2 models.

### Specialist 1 — OntoNotes Adapter

Learns:

```text
PERSON
ORG
DATE
TIME
QUANTITY
```

### Specialist 2 — Dataset 2 Adapter

Learns:

```text
GPE
EVENT
```

Both specialists use **LoRA parameter-efficient fine-tuning**.

---

# Pseudo-Labeling

After training the specialist models, they can be used as teachers to recover entities that are missing from the other dataset.

```text
Dataset 1
   │
   └── OntoNotes trusted labels
       PERSON
       ORG
       DATE
       TIME
       QUANTITY
   │
   └── Dataset 2 specialist predicts
       GPE
       EVENT


Dataset 2
   │
   └── Dataset 2 trusted labels
       GPE
       EVENT
   │
   └── OntoNotes specialist predicts
       PERSON
       ORG
       DATE
       TIME
       QUANTITY
```

Only predictions above the configured confidence threshold are accepted.

The current notebook uses:

```python
PSEUDO_THRESHOLD = 0.85
```

Pseudo-labeling is optional because these annotations are weak supervision and must be inspected before being used for final training.

---

# Final Unified Dataset

The enriched datasets are combined into a single seven-label dataset.

Before training:

1. Source-specific annotations are normalized.
2. Mixed sentences are preserved.
3. Pseudo-labels can be added.
4. Duplicate texts are merged.
5. Duplicate entity annotations are removed.
6. The final dataset is split into train, validation, and test sets.

The split occurs **after deduplication** so that the same text does not unintentionally appear across different splits.

---

# Final GLiNER2 Model

The final model is based on:

```text
fastino/gliner2-base-v1
```

and is fine-tuned with the unified seven-label ontology:

```text
PERSON
ORG
GPE
EVENT
DATE
TIME
QUANTITY
```

The current notebook starts with:

```text
Epochs: 3
Batch size: 8
Gradient accumulation: 2
Encoder learning rate: 1e-5
Task learning rate: 5e-4
LoRA: enabled
```

Early stopping and validation are enabled for the final training stage.

---

# Why These Entities Matter for the Knowledge Graph

The extracted entities will eventually become **Knowledge Graph nodes**.

For example, from:

```text
President Donald Trump met NATO officials in Washington
on August 14, 2026 during the Iran conflict.
```

the NER system can identify:

```text
PERSON    → Donald Trump
ORG       → NATO
GPE       → Washington
DATE      → August 14, 2026
EVENT     → Iran conflict
```

These entities can then be passed to the downstream relation-extraction system.

Conceptually:

```text
Donald Trump
      │
      │ met
      ▼
    NATO
      │
      │ located/operating in
      ▼
 Washington

Iran conflict
      │
      │ occurred during
      ▼
August 14, 2026
```

NER therefore provides the **entity layer**, while the subsequent relation-extraction stage provides the **relationship layer**.

Together they form the basis of the Knowledge Graph.

---

# Data Format

The cleaned data is converted into the GLiNER2 training format:

```json
{
  "input": "Donald Trump met NATO officials in Washington.",
  "output": {
    "entities": {
      "PERSON": ["Donald Trump"],
      "ORG": ["NATO"],
      "GPE": ["Washington"]
    }
  }
}
```

The notebook generates:

```text
gliner2_ner/
├── ontonotes_trusted.jsonl
├── dataset2_trusted.jsonl
├── train.jsonl
├── validation.jsonl
├── test.jsonl
├── adapters/
│   ├── ontonotes/
│   └── dataset2/
└── final_model/
```

---

# Training Workflow

The complete workflow is:

```text
1. Load OntoNotes5
        │
        ▼
2. Extract trusted PERSON/ORG/DATE/TIME/QUANTITY
        │
        ▼
3. Load combined_output.jsonl
        │
        ▼
4. Extract trusted GPE/EVENT
        │
        ▼
5. Preserve mixed sentences
        │
        ▼
6. Train OntoNotes specialist
        │
        ▼
7. Train Dataset 2 specialist
        │
        ▼
8. Optional high-confidence pseudo-labeling
        │
        ▼
9. Inspect pseudo-labels
        │
        ▼
10. Merge + deduplicate
        │
        ▼
11. Train/validation/test split
        │
        ▼
12. Validate training data
        │
        ▼
13. Fine-tune final GLiNER2
        │
        ▼
14. Evaluate NER
        │
        ▼
15. Use extracted entities for Knowledge Graph construction
```

---

# Evaluation

The notebook includes an exact-match evaluation based on:

```text
(entity text, entity label)
```

and calculates:

```text
Precision
Recall
F1
TP
FP
FN
```

The test set should ultimately be **manually verified** because the two source datasets have different annotation policies.

Evaluation should also be performed **per entity type**, not only using aggregate F1.

In particular:

```text
TIME
EVENT
QUANTITY
```

should be evaluated independently because weak performance on minority entity types can be hidden by the aggregate score. 
---

# Running the Notebook

The notebook is designed to run in **Google Colab**.

Install dependencies:

```bash
pip install -U "gliner2[local]" datasets scikit-learn pandas matplotlib tqdm
```

Upload:

```text
combined_output.jsonl
```

and configure:

```python
DATASET2_PATH = Path("/content/combined_output.jsonl")
```

Then execute the notebook from preprocessing through final training.

---

# Important Training Principle

This project prioritizes **annotation correctness over simply maximizing dataset size**.

We do not assume:

```text
"entity not annotated"
=
"not an entity"
```

Instead, we distinguish between:

```text
Trusted positive annotation
        vs.
Missing annotation
```

This distinction is important when combining datasets with different annotation policies and is particularly important for Knowledge Graph construction, where incorrect entities can propagate into later node creation and relationship extraction.

---

# End Goal

The ultimate objective is to use the fine-tuned GLiNER2 model as the **entity extraction component of a Knowledge Graph pipeline**.

The final architecture is intended to evolve into:

```text
                 Documents / News / Reports
                           │
                           ▼
                    Text Processing
                           │
                           ▼
                    ┌─────────────┐
                    │   GLiNER2   │
                    │     NER     │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        Entity Nodes              Entity Metadata
              │
              ▼
       Entity Resolution
              │
              ▼
      Relation Extraction
              │
              ▼
        Graph Construction
              │
              ▼
        ┌───────────────┐
        │ Knowledge     │
        │    Graph      │
        └───────────────┘
```

The trained GLiNER2 model is therefore **not the final product**. It is the NER foundation used to identify the entities that will populate the Knowledge Graph and support downstream relation extraction, entity resolution, and graph construction.
