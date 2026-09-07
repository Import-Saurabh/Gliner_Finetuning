# GLiNER2 NER for Knowledge Graph Construction

[![Hugging Face Model](https://img.shields.io/badge/🤗%20Model-Saurabh18888/gliner--news--geo-yellow.svg)](https://huggingface.co/Saurabh18888/gliner-news-geo)

## Overview

This project fine-tunes **GLiNER2** to build the **Named Entity Recognition (NER) layer of a Knowledge Graph construction pipeline**.

The goal is not to create a generic NER model. The goal is to reliably identify the entities that will become **nodes in a Knowledge Graph**, which can later be connected through relation extraction and stored in a graph database.

The final NER model is designed for five core geopolitical entity types:

- `PERSON`
- `ORG`
- `GPE`
- `EVENT`
- `DATE`

These entities are particularly useful for extracting structured information from news, reports, articles, and other unstructured text before constructing the Knowledge Graph.

You can access the fine-tuned model here: **[Saurabh18888/gliner-news-geo](https://huggingface.co/Saurabh18888/gliner-news-geo)**

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
     └── DATE
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

The purpose of this fine-tuning stage is to produce **high-quality entity candidates for downstream Knowledge Graph construction**.

---

## Entity Ontology

| Entity | Description | Example |
|---|---|---|
| `PERSON` | Names of individual people including politicians, business leaders, and officials. | Donald Trump |
| `ORG` | Organizations, companies, governments, political parties, NGOs, and institutions. | NATO |
| `GPE` | Geopolitical entities such as countries, states, provinces, cities, and territories. | Iran, Washington |
| `EVENT` | Named or identifiable real-world events including geopolitical, military, and historical events. | 2024 Paris Olympics |
| `DATE` | Temporal expressions including dates, months, years, date ranges, and relative dates. | August 14, 2026 |

---

## Training Data Strategy

Because no single dataset provides high-quality coverage for all five target labels, this pipeline merges **three distinct datasets**:

### 1. [TNER OntoNotes 5](https://huggingface.co/datasets/tner/ontonotes5)
The foundational dataset. It provides excellent, high-volume coverage for `PERSON`, `ORG`, `GPE`, and `DATE`. It contains very few `EVENT`s.

### 2. [Few-NERD](https://huggingface.co/datasets/DFKI-SLT/few-nerd)
Used strictly to bolster the `EVENT` class. Few-NERD provides a massive pool of events, which we filter and randomly downsample to balance against the OntoNotes labels.

### 3. Custom JSONL (`combined_output.jsonl`)
A highly-trusted, domain-specific local dataset focused entirely on geopolitical `EVENT`s. We drop corrupted labels from this dataset (like broken PERSON/ORG extractions) and keep only the gold-standard EVENTs to inject strong domain knowledge into the model.

---

## Overcoming the Annotation Coverage Problem

A major problem when merging datasets is **differing annotation coverage**. 

For example, our Custom JSONL dataset drops `PERSON` and `ORG` labels because they were corrupted. If we feed a sentence containing a person's name to the model but don't label it as `PERSON`, the model learns a **False Negative** (i.e., it learns that the name is *not* a person).

Instead of using complex multi-stage pseudo-labeling, we solve this gracefully using **GLiNER's dynamic prompting format**. 

During dataset construction, we restrict the prompted `valid_labels` based on the source dataset:
* For **OntoNotes**, we prompt the model to learn all 5 labels.
* For **Custom JSONL**, we *only* prompt the model for `EVENT`. 

By not asking the model to predict `PERSON` or `ORG` on the Custom dataset, we completely bypass the False Negative penalty.

---

## Dataset Balancing & Unified Training

Because Few-NERD contains over 100,000 events, simply concatenating the datasets would cause the `EVENT` class to dominate the loss function, destroying the model's ability to recognize dates or organizations.

The pipeline implements a **controlled budgeting strategy**:
1. It calculates the fixed number of entities provided by OntoNotes and Custom datasets.
2. It sets a dynamic `TARGET_BUDGET` (e.g., 18,000 entities per class).
3. It samples just enough Few-NERD records to reach the budget.

---

## Final GLiNER2 Model

The final model uses **LoRA parameter-efficient fine-tuning** on top of the base GLiNER architecture:

```text
Base Model: fastino/gliner2-base-v1
Epochs: 8
Batch size: 18
Gradient accumulation: 2
Encoder learning rate: 1e-5
Task learning rate: 5e-4
LoRA Rank (r): 8 (Configurable to 16/32)
LoRA Alpha: 16.0 (Configurable to 32.0/64.0)
```

Early stopping (`patience=3`) and validation are evaluated at every epoch.

---

## Why These Entities Matter for the Knowledge Graph

The extracted entities will eventually become **Knowledge Graph nodes**.

For example, from:
> *President Donald Trump met NATO officials in Washington on August 14, 2026 during the Iran conflict.*

The NER system extracts:
```text
PERSON    → Donald Trump
ORG       → NATO
GPE       → Washington
DATE      → August 14, 2026
EVENT     → Iran conflict
```

These entities can then be passed to the downstream relation-extraction system to form the basis of the Knowledge Graph:

```text
[Donald Trump] ──(met)──▶ [NATO] ──(located in)──▶ [Washington]
                               │
                       (occurred during)
                               │
                               ▼
                       [Iran conflict]
```

---

## Training Workflow

The complete notebook workflow is:

```text
1. Load OntoNotes 5, Few-NERD, and Custom JSONL
        │
        ▼
2. Normalize all formats to Character-Level Spans
        │
        ▼
3. Validate and drop overlapping/whitespace spans
        │
        ▼
4. Global text deduplication (preventing data leakage)
        │
        ▼
5. Class Balancing (Downsample Few-NERD to Target Budget)
        │
        ▼
6. GroupShuffleSplit (Train / Val / Test)
        │
        ▼
7. Convert to GLiNER2 InputExample format
        │
        ▼
8. Fine-tune unified GLiNER2 with LoRA
        │
        ▼
9. Strict Span + Label Evaluation & Error Analysis
        │
        ▼
10. Save Model & Adapters
```

---

## Evaluation

The notebook includes an exact-match evaluation based on strict span boundaries:

```text
(entity start, entity end, entity label)
```

It outputs Micro/Macro statistics including Precision, Recall, and F1. 

A dedicated **Error Analysis** module is included to randomly sample and review:
* `Missed Entities` (False Negatives)
* `Spurious Entities` (False Positives)
* `Wrong Labels`

---

## Running the Notebook

The notebook is designed to run in **Google Colab**.

Install dependencies:
```bash
pip install -q "gliner2[local]" datasets scikit-learn matplotlib seaborn pandas tqdm huggingface_hub
```

Upload the domain-specific data:
```text
combined_output.jsonl
```

Run the notebook sequentially to preprocess the multi-source data, train the LoRA adapter, and save the merged `/best_model` locally or push it directly to the Hugging Face hub.
