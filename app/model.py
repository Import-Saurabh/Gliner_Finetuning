"""Thread-safe GLiNER2 model manager.

Base model : fastino/gliner2-base-v1
Adapter    : LoRA/adapter finetuned on the GEOPOLITICAL WIKI NEWS DATASET
             (Wikipedia current-conflict / wiki-news style articles).
Labels     : PERSON, GPE, ORG, EVENT, DATE
"""
from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("geoner.model")

DATASET_NAME = "Geopolitical Wiki News Dataset (Wikipedia current-conflict articles)"

# Default adapter location: <this file's dir>/adapter/best (i.e. app/adapter/best),
# resolved relative to model.py itself so it works no matter which directory
# `uvicorn` was launched from. ADAPTER_PATH env var still overrides this
# (either with a different local path, or a Hugging Face Hub repo id).
_DEFAULT_ADAPTER_DIR = str(Path(__file__).resolve().parent / "adapter" / "best")


@dataclass
class Settings:
    base_model: str = os.getenv("GLINER_BASE_MODEL", "fastino/gliner2-base-v1")
    adapter_path: str = os.getenv("ADAPTER_PATH", _DEFAULT_ADAPTER_DIR)
    labels: List[str] = field(
        default_factory=lambda: [
            l.strip()
            for l in os.getenv("NER_LABELS", "PERSON,GPE,ORG,EVENT,DATE").split(",")
            if l.strip()
        ]
    )
    threshold: float = float(os.getenv("NER_THRESHOLD", "0.3"))
    max_text_len: int = int(os.getenv("MAX_TEXT_LEN", "4000"))


settings = Settings()


class ModelManager:
    """Loads the GLiNER2 base model + finetuned adapter exactly once.

    - Background warm-up at startup (Render health-check stays green).
    - Self-healing: a failed load is retried on the next request.
    - Adapter can be a local dir (repo/adapter/best) or a HF Hub repo id.
    """

    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self._model = None
        self._lock = threading.Lock()
        self._loading = False
        self._error: Optional[str] = None

    # ------------------------------------------------------------------ load
    def load(self) -> bool:
        with self._lock:
            if self._model is not None:
                return True
            if self._loading:
                return False          # warm-up already in progress -> 503
            self._loading = True
            self._error = None
        try:
            from gliner2 import GLiNER2

            log.info("Loading base model: %s", self.cfg.base_model)
            model = GLiNER2.from_pretrained(self.cfg.base_model)

            adapter = self._resolve_adapter(self.cfg.adapter_path)
            log.info("Loading adapter from: %s", adapter)
            model.load_adapter(adapter)

            with self._lock:
                self._model = model
                self._loading = False
            log.info("Adapter loaded successfully!")
            return True
        except Exception as exc:  # pragma: no cover
            log.exception("Model load failed")
            with self._lock:
                self._error = str(exc)
                self._loading = False
            return False

    @staticmethod
    def _resolve_adapter(path: str) -> str:
        p = Path(path)
        if p.is_dir():
            return str(p)
        # Treat as Hugging Face repo id (e.g. "username/gliner2-geopolitical")
        from huggingface_hub import snapshot_download
        return snapshot_download(path)

    # ----------------------------------------------------------------- state
    @property
    def loaded(self) -> bool:
        return self._model is not None

    @property
    def error(self) -> Optional[str]:
        return self._error

    # -------------------------------------------------------------- inference
    def extract(self, text: str, labels: List[str], threshold: float) -> List[Dict[str, Any]]:
        """Return non-overlapping entity spans sorted by position."""
        model = self._model
        spans: List[Dict[str, Any]] = []

        # Preferred: span-level API
        try:
            raw = model.predict_entities(text, labels, threshold=threshold)
        except Exception:
            raw = None

        if raw is not None:
            for e in raw:
                try:
                    s, en = int(e["start"]), int(e["end"])
                    spans.append({
                        "text": e.get("span") or e.get("text") or text[s:en],
                        "label": e["label"],
                        "start": s,
                        "end": en,
                        "score": round(float(e.get("score", 1.0)), 4),
                    })
                except Exception:
                    continue
        else:
            # Fallback: grouped API ({'entities': {label: [texts]}}) + localisation
            res = model.extract_entities(text, labels)
            entities = res.get("entities", {}) if isinstance(res, dict) else {}
            used = set()
            for label, items in entities.items():
                for item in items:
                    for m in re.finditer(re.escape(item), text):
                        if (m.start(), m.end()) not in used:
                            used.add((m.start(), m.end()))
                            spans.append({
                                "text": item, "label": label,
                                "start": m.start(), "end": m.end(), "score": 1.0,
                            })
                            break

        spans.sort(key=lambda d: (d["start"], d["end"]))
        clean, last_end = [], -1
        for s in spans:                       # drop overlaps
            if s["start"] >= last_end:
                clean.append(s)
                last_end = s["end"]
        return clean