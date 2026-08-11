
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

import requests
import torch
from bs4 import BeautifulSoup
from gliner import GLiNER


WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/2026_Iran_war"

# IMPORTANT:
# GLiNER fine-tuning does not store the list of training labels in the
# checkpoint in a way that can reliably be recovered by this script.
# Replace these defaults with the EXACT labels used in your training data.
DEFAULT_ENTITY_TYPES = [
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "EVENT",
    "WEAPON",
    "DATE",
]


def fetch_wikipedia_article(url: str = WIKIPEDIA_URL) -> List[Dict[str, str]]:
    """Fetch the article and return meaningful text sections."""

    headers = {
        "User-Agent": (
            "GLiNER-NER-research-script/1.0 "
            "(educational use; contact: local-user)"
        )
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove content that should not be sent to the NER model.
    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "table",
            "sup",
            "figure",
            "nav",
            "form",
        ]
    ):
        tag.decompose()

    content = soup.select_one("#mw-content-text")
    if content is None:
        content = soup

    sections: List[Dict[str, str]] = []
    current_heading = "Introduction"
    buffer: List[str] = []

    def flush() -> None:
        nonlocal buffer
        text = clean_text(" ".join(buffer))
        if text:
            sections.append(
                {
                    "section": current_heading,
                    "text": text,
                }
            )
        buffer = []

    for element in content.find_all(["h2", "h3", "p"]):
        if element.name in {"h2", "h3"}:
            flush()
            heading = clean_text(element.get_text(" ", strip=True))
            heading = re.sub(r"\[edit\]$", "", heading).strip()
            if heading:
                current_heading = heading
        elif element.name == "p":
            paragraph = clean_text(element.get_text(" ", strip=True))
            if paragraph:
                buffer.append(paragraph)

    flush()

    # Ignore very short navigation-like fragments.
    sections = [
        s for s in sections
        if len(s["text"].split()) >= 5
    ]

    if not sections:
        raise RuntimeError("No article text could be extracted from Wikipedia.")

    return sections


def clean_text(text: str) -> str:
    """Normalize Wikipedia HTML text for NER."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\[\s*\d+\s*\]", "", text)  # citation markers
    return text.strip()


def chunk_text(text: str, max_words: int = 180) -> List[str]:
    """
    Split long sections into word-based chunks.

    A conservative chunk size is used so that the fine-tuned GLiNER model
    is not overwhelmed by a very long Wikipedia section.
    """
    words = text.split()
    return [
        " ".join(words[i : i + max_words])
        for i in range(0, len(words), max_words)
    ]


def load_model(model_dir: str, device: str) -> GLiNER:
    """Load the local fine-tuned GLiNER checkpoint."""
    model_path = Path(model_dir)

    if not model_path.exists():
        raise FileNotFoundError(f"Model directory does not exist: {model_path}")

    required = model_path / "pytorch_model.bin"
    if not required.exists():
        raise FileNotFoundError(
            f"pytorch_model.bin was not found in {model_path}. "
            "Point --model-dir to the directory containing "
            "pytorch_model.bin and gliner_config.json."
        )

    model = GLiNER.from_pretrained(str(model_path))
    model = model.to(device)
    model.eval()
    return model


def normalize_entity(entity: Dict) -> Dict:
    """Keep only stable, JSON-serializable prediction fields."""
    result = {
        "text": entity.get("text", ""),
        "label": entity.get("label", ""),
    }

    # GLiNER normally returns start/end character offsets.
    if entity.get("start") is not None:
        result["start"] = int(entity["start"])
    if entity.get("end") is not None:
        result["end"] = int(entity["end"])

    if entity.get("score") is not None:
        result["score"] = round(float(entity["score"]), 6)

    return result


def deduplicate_entities(entities: List[Dict]) -> List[Dict]:
    """
    Remove exact duplicates and prefer the higher-confidence prediction
    when the same span/label occurs more than once.
    """
    best = {}

    for entity in entities:
        key = (
            entity.get("text", "").strip(),
            entity.get("label", ""),
            entity.get("start"),
            entity.get("end"),
        )

        score = float(entity.get("score", 0.0))
        if key not in best or score > float(best[key].get("score", 0.0)):
            best[key] = entity

    return sorted(
        best.values(),
        key=lambda x: (
            x.get("start", 10**12),
            x.get("end", 10**12),
            x.get("label", ""),
        ),
    )


def extract_ner(
    model: GLiNER,
    sections: List[Dict[str, str]],
    entity_types: List[str],
    threshold: float,
    max_words: int,
) -> List[Dict]:
    """Run NER over all article sections."""
    output = []

    for section_index, section in enumerate(sections):
        chunks = chunk_text(section["text"], max_words=max_words)

        for chunk_index, text in enumerate(chunks):
            predictions = model.predict_entities(
                text,
                entity_types,
                threshold=threshold,
            )

            entities = [
                normalize_entity(p)
                for p in predictions
                if p.get("text") and p.get("label")
            ]

            entities = deduplicate_entities(entities)

            output.append(
                {
                    "section": section["section"],
                    "section_index": section_index,
                    "chunk_index": chunk_index,
                    "text": text,
                    "entities": entities,
                }
            )

    return output


def flatten_results(results: List[Dict]) -> List[Dict]:
    """Create one JSONL record per extracted entity."""
    rows = []

    for block in results:
        for entity in block["entities"]:
            rows.append(
                {
                    "section": block["section"],
                    "section_index": block["section_index"],
                    "chunk_index": block["chunk_index"],
                    "entity": entity["text"],
                    "label": entity["label"],
                    "score": entity.get("score"),
                    "start": entity.get("start"),
                    "end": entity.get("end"),
                }
            )

    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract NER entities from the 2026 Iran war Wikipedia article."
    )

    parser.add_argument(
        "--model-dir",
        required=True,
        help="Path to the fine-tuned GLiNER model directory.",
    )

    parser.add_argument(
        "--labels",
        nargs="+",
        default=DEFAULT_ENTITY_TYPES,
        help=(
            "Exact entity labels used during GLiNER fine-tuning. "
            "If omitted, domain-oriented defaults are used."
        ),
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.50,
        help="GLiNER confidence threshold. Default: 0.50",
    )

    parser.add_argument(
        "--max-words",
        type=int,
        default=180,
        help="Maximum words per NER chunk. Default: 180",
    )

    parser.add_argument(
        "--url",
        default=WIKIPEDIA_URL,
        help="Wikipedia article URL.",
    )

    parser.add_argument(
        "--output",
        default="ner_iran_war.json",
        help="JSON output file.",
    )

    parser.add_argument(
        "--jsonl-output",
        default="ner_iran_war.jsonl",
        help="JSONL output file.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not 0.0 <= args.threshold <= 1.0:
        raise ValueError("--threshold must be between 0 and 1.")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    print("=" * 72)
    print("GLiNER NER — 2026 Iran War Wikipedia Article")
    print("=" * 72)
    print(f"Model   : {args.model_dir}")
    print(f"Device  : {device}")
    print(f"Labels  : {', '.join(args.labels)}")
    print(f"Threshold: {args.threshold}")
    print()

    print("Loading fine-tuned model...")
    model = load_model(args.model_dir, device)
    print("Model loaded.")

    print("\nDownloading article...")
    sections = fetch_wikipedia_article(args.url)
    print(f"Extracted sections: {len(sections)}")

    total_words = sum(len(s["text"].split()) for s in sections)
    print(f"Article words      : {total_words:,}")

    print("\nRunning NER...")
    results = extract_ner(
        model=model,
        sections=sections,
        entity_types=args.labels,
        threshold=args.threshold,
        max_words=args.max_words,
    )

    flat_entities = flatten_results(results)
    unique_entities = deduplicate_entities(
        [
            {
                "text": row["entity"],
                "label": row["label"],
                "score": row.get("score"),
                "start": row.get("start"),
                "end": row.get("end"),
            }
            for row in flat_entities
        ]
    )

    payload = {
        "source_url": args.url,
        "model_dir": str(Path(args.model_dir).resolve()),
        "device": device,
        "threshold": args.threshold,
        "entity_types": args.labels,
        "article_sections": len(sections),
        "article_words": total_words,
        "chunks": len(results),
        "entity_count": len(flat_entities),
        "entities": flat_entities,
    }

    Path(args.output).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with open(args.jsonl_output, "w", encoding="utf-8") as f:
        for row in flat_entities:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("\n" + "=" * 72)
    print(f"Entities extracted: {len(flat_entities):,}")
    print(f"JSON output       : {args.output}")
    print(f"JSONL output      : {args.jsonl_output}")
    print("=" * 72)

    print("\nTop extracted entities:")
    for entity in unique_entities[:50]:
        score = entity.get("score")
        score_text = f"{score:.3f}" if score is not None else "n/a"
        print(
            f"  {entity['label']:24s} "
            f"{entity['text'][:60]:60s} "
            f"{score_text}"
        )


if __name__ == "__main__":
    main()