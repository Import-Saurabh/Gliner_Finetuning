"""GeoNER API — production-ready FastAPI service for geopolitical NER.

GLiNER2 (fastino/gliner2-base-v1) + adapter finetuned on the
GEOPOLITICAL WIKI NEWS DATASET. Labels: PERSON, GPE, ORG, EVENT, DATE.

Built by Saurabh Hadole (AVI) — ML/AI Engineer
Portfolio: https://saurabhhadole.vercel.app/
GitHub:    https://github.com/Import-Saurabh
"""
from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from mangum import Mangum  # <-- ADDED: Required for AWS Lambda

from .model import DATASET_NAME, ModelManager, settings
from .samples import SAMPLES
from .schemas import AboutOut, NERRequest, NERResponse, SampleOut
from .wiki import router as wiki_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("geoner.api")

STATIC = Path(__file__).resolve().parent / "static"
manager = ModelManager(settings)

AUTHOR = "Saurabh Hadole (AVI)"
AUTHOR_ROLE = "ML/AI Engineer"
AUTHOR_PORTFOLIO = "https://saurabhhadole.vercel.app/"
AUTHOR_GITHUB = "https://github.com/Import-Saurabh"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # For AWS Lambda, we shouldn't use background threads for initialization 
    # because the runtime freezes them. We will load synchronously on cold start instead.
    # manager.load() # optionally load synchronously here, or let the first request do it.
    log.info("GeoNER API startup (model will load on first request)")
    yield
    log.info("GeoNER API shutting down")


app = FastAPI(
    title="GeoNER API",
    version="1.0.0",
    description=(
        "Geopolitical Named-Entity Recognition with **GLiNER2** "
        "(`fastino/gliner2-base-v1`) + an adapter **finetuned on the Geopolitical "
        "Wiki News Dataset** (Wikipedia current-conflict articles).\n\n"
        "Labels: `PERSON`, `GPE`, `ORG`, `EVENT`, `DATE`.\n\n"
        f"Built by **{AUTHOR}** — {AUTHOR_ROLE}  \n"
        f"[Portfolio]({AUTHOR_PORTFOLIO}) &bull; [GitHub]({AUTHOR_GITHUB})"
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to your frontend domain in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wiki_router)


# --------------------------------------------------------------------- UI
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html", media_type="text/html")


# ----------------------------------------------------------------- health
@app.get("/health", tags=["ops"])
def health():
    return {
        "status": "ok",
        "model_loaded": manager.loaded,
        "model_error": manager.error,
    }


# ------------------------------------------------------------------- info
@app.get("/api/info", tags=["meta"])
def info():
    return {
        "name": "GeoNER API",
        "framework": "GLiNER2",
        "base_model": settings.base_model,
        "adapter": settings.adapter_path,
        "finetuned_on": DATASET_NAME,
        "labels": settings.labels,
        "threshold": settings.threshold,
        "max_text_len": settings.max_text_len,
        "author": AUTHOR,
    }


@app.get("/api/about", response_model=AboutOut, tags=["meta"])
def about():
    return AboutOut(
        project="GeoNER — Geopolitical NER Demo",
        description=(
            "GLiNER2 fine-tuned on the Geopolitical Wiki News Dataset to extract "
            "PERSON, GPE, ORG, EVENT, and DATE entities from conflict-related text."
        ),
        author=AUTHOR,
        role=AUTHOR_ROLE,
        portfolio=AUTHOR_PORTFOLIO,
        github=AUTHOR_GITHUB,
    )


@app.get("/api/labels", response_model=List[str], tags=["meta"])
def labels():
    return settings.labels


@app.get("/api/samples", response_model=Dict[str, List[SampleOut]], tags=["meta"])
def samples():
    return {"samples": SAMPLES}


# -------------------------------------------------------------------- NER
@app.post("/api/ner", response_model=NERResponse, tags=["ner"])
def ner(req: NERRequest):
    labels = [l.strip().upper() for l in (req.labels or settings.labels) if l.strip()]
    if not labels:
        raise HTTPException(422, "At least one label is required")

    if not manager.loaded:
        manager.load()                      # synchronous retry if warm-up died
    if manager.error:
        raise HTTPException(500, f"Model failed to load: {manager.error}")
    if not manager.loaded:
        raise HTTPException(
            503,
            "Model is still loading (first request after deploy). Retry shortly.",
            headers={"Retry-After": "5"},
        )

    threshold = req.threshold if req.threshold is not None else settings.threshold
    t0 = time.perf_counter()
    try:
        spans = manager.extract(req.text, labels, threshold)
    except Exception as exc:
        log.exception("Inference failed")
        raise HTTPException(500, f"Inference failed: {exc}")
    inference_ms = round((time.perf_counter() - t0) * 1000, 2)

    grouped: Dict[str, List[str]] = {}
    for s in spans:
        grouped.setdefault(s["label"], [])
        if s["text"] not in grouped[s["label"]]:
            grouped[s["label"]].append(s["text"])

    return NERResponse(
        entities=spans,
        grouped=grouped,
        counts={k: len(v) for k, v in grouped.items()},
        total=len(spans),
        inference_ms=inference_ms,
        model={
            "framework": "GLiNER2",
            "base": settings.base_model,
            "adapter": settings.adapter_path,
            "dataset": DATASET_NAME,
        },
    )

# -------------------------------------------------------------------- LAMBDA HANDLER
# This wraps the FastAPI app so AWS Lambda can invoke it
handler = Mangum(app)