# GLiNER Fine-Tuning & Iran War NER

This repository contains a fine-tuned GLiNER model workflow and an inference script for extracting named entities from the 2026 Iran War Wikipedia article.

## Files

- `ner_iran_war.py` — downloads the Wikipedia article, extracts its sections, chunks long text, runs GLiNER NER, deduplicates predictions, and writes JSON/JSONL output.
- `ner_iran_war.jsonl` — JSONL NER output.
- `ner_iran_war.json` — JSON NER output when generated.
- `requirements.txt` — Python dependencies.

## 1. Setup

Create and activate a virtual environment:

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

The script uses `requests`, `torch`, `beautifulsoup4`, and `gliner`.

## 2. Fine-tuning GLiNER

The fine-tuning process is performed using the GLiNER training workflow/Colab notebook.

Prepare your training data using the labels required for your NER task. The labels used during training must be preserved because the inference script requires the same label names.

After fine-tuning, keep the final inference model directory containing at least:

```text
pytorch_model.bin
gliner_config.json
```

The tokenizer/configuration files generated with the model should also be kept in the model directory.

Training checkpoints such as:

```text
checkpoint-9000/
checkpoint-10000/
```

are not required for inference and can be omitted when distributing the final model.

## 3. Run NER inference

The script requires a local fine-tuned GLiNER model directory:

```powershell
python ner_iran_war.py --model-dir "PATH_TO_FINETUNED_MODEL"
```

For example:

```powershell
python ner_iran_war.py --model-dir ".\gliner_finetuned"
```

The script automatically:

1. Selects CUDA when a CUDA-enabled PyTorch installation is available; otherwise it uses CPU.
2. Downloads the configured Wikipedia article.
3. Removes irrelevant HTML elements.
4. Extracts meaningful article sections.
5. Splits long sections into chunks.
6. Runs the fine-tuned GLiNER model.
7. Deduplicates entity predictions.
8. Writes JSON and JSONL results.

## 4. Specify entity labels

The default labels in the script are:

```text
PERSON
ORGANIZATION
LOCATION
EVENT
WEAPON
DATE
```

The labels should match the labels used during fine-tuning.

You can explicitly provide the labels:

```powershell
python ner_iran_war.py `
  --model-dir ".\gliner_finetuned" `
  --labels PERSON ORGANIZATION LOCATION EVENT WEAPON DATE
```

## 5. Adjust confidence threshold

The default GLiNER confidence threshold is `0.50`.

For example:

```powershell
python ner_iran_war.py `
  --model-dir ".\gliner_finetuned" `
  --threshold 0.60
```

Higher thresholds generally produce fewer, higher-confidence predictions.

## 6. Adjust chunk size

The default maximum chunk size is 180 words:

```powershell
python ner_iran_war.py `
  --model-dir ".\gliner_finetuned" `
  --max-words 180
```

You can change it, for example:

```powershell
python ner_iran_war.py `
  --model-dir ".\gliner_finetuned" `
  --max-words 150
```

## 7. Use another article URL

The default URL is the 2026 Iran War Wikipedia article. A different compatible URL can be supplied:

```powershell
python ner_iran_war.py `
  --model-dir ".\gliner_finetuned" `
  --url "https://en.wikipedia.org/wiki/2026_Iran_war"
```

## 8. Specify output files

Default outputs are:

```text
ner_iran_war.json
ner_iran_war.jsonl
```

You can change them:

```powershell
python ner_iran_war.py `
  --model-dir ".\gliner_finetuned" `
  --output "results.json" `
  --jsonl-output "results.jsonl"
```

## Complete example

```powershell
python ner_iran_war.py `
  --model-dir ".\gliner_finetuned" `
  --labels PERSON ORGANIZATION LOCATION EVENT WEAPON DATE `
  --threshold 0.50 `
  --max-words 180 `
  --output "ner_iran_war.json" `
  --jsonl-output "ner_iran_war.jsonl"
```

## Important notes

### Label compatibility

The script explicitly warns that the list of training labels cannot be reliably recovered from the GLiNER checkpoint. Therefore, `--labels` should contain the **exact labels used during fine-tuning**. The script currently provides domain-oriented defaults. 

### Model directory

`--model-dir` must point to the directory containing the final fine-tuned model. The script checks for `pytorch_model.bin` and then loads the model using:

```python
GLiNER.from_pretrained(model_path)
```

### GPU

The script automatically uses:

```text
cuda
```

when `torch.cuda.is_available()` is true. Otherwise it runs on:

```text
cpu
```

## CLI reference

```text
--model-dir       Required. Path to the fine-tuned GLiNER model.
--labels          Entity labels used during fine-tuning.
--threshold       Confidence threshold. Default: 0.50.
--max-words       Maximum words per NER chunk. Default: 180.
--url             Wikipedia article URL.
--output          JSON output path. Default: ner_iran_war.json.
--jsonl-output    JSONL output path. Default: ner_iran_war.jsonl.
```

## Output format

The JSONL output contains one record per extracted entity with fields such as:

```json
{
  "section": "Introduction",
  "section_index": 0,
  "chunk_index": 0,
  "entity": "Example Entity",
  "label": "ORGANIZATION",
  "score": 0.91,
  "start": 10,
  "end": 24
}
```

The JSON output additionally stores metadata including the source URL, model directory, device, threshold, entity types, article size, chunk count, and total entity count.

## Reproducibility

For reproducible inference:

- Use the same fine-tuned model files.
- Use the exact entity labels used during training.
- Keep the confidence threshold fixed.
- Keep the chunk size fixed.
- Record the GLiNER and PyTorch versions used for deployment.
