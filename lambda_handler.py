"""AWS Lambda handler for GeoNER API.

This module provides the entry point for AWS Lambda to invoke the GeoNER model.
It wraps the FastAPI application logic into a Lambda-compatible format.

Built by Saurabh Hadole (AVI) — ML/AI Engineer
Portfolio: https://saurabhhadole.vercel.app/
GitHub:    https://github.com/Import-Saurabh
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from collections import defaultdict
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("geoner.lambda")

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))  # requests per window
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
ENABLE_RATE_LIMIT = os.getenv("ENABLE_RATE_LIMIT", "true").lower() == "true"

# Global rate limit tracking (in-memory for Lambda)
_rate_limit_data = defaultdict(list)
_rate_limit_lock = threading.Lock()

# Global model instance (cached across Lambda invocations)
_model_instance = None
_model_loading = False
_model_error: Optional[str] = None


def _check_rate_limit(client_id: str) -> bool:
    """Check if client has exceeded rate limit.
    
    Args:
        client_id: Unique identifier for the client (IP or API key)
    
    Returns:
        True if request is allowed, False if rate limited
    """
    if not ENABLE_RATE_LIMIT:
        return True
    
    current_time = time.time()
    window_start = current_time - RATE_LIMIT_WINDOW
    
    with _rate_limit_lock:
        # Clean old entries
        _rate_limit_data[client_id] = [
            t for t in _rate_limit_data[client_id] if t > window_start
        ]
        
        # Check if limit exceeded
        if len(_rate_limit_data[client_id]) >= RATE_LIMIT_REQUESTS:
            return False
        
        # Record this request
        _rate_limit_data[client_id].append(current_time)
        return True


def _get_client_id(event: Dict[str, Any]) -> str:
    """Extract client identifier from event for rate limiting."""
    # Try to get IP from Lambda Function URL context
    request_context = event.get("requestContext", {})
    http_context = request_context.get("http", {})
    source_ip = http_context.get("sourceIp", "unknown")
    
    # Could also use API key if implemented
    headers = event.get("headers", {})
    api_key = headers.get("x-api-key", "")
    
    if api_key:
        return f"key:{api_key}"
    return f"ip:{source_ip}"


def _get_settings() -> Dict[str, Any]:
    """Get model settings from environment variables."""
    return {
        "base_model": os.getenv("GLINER_BASE_MODEL", "fastino/gliner2-base-v1"),
        "adapter_path": "/opt/adapter/best",  # Lambda layer path
        "labels": [
            l.strip()
            for l in os.getenv("NER_LABELS", "PERSON,GPE,ORG,EVENT,DATE").split(",")
            if l.strip()
        ],
        "threshold": float(os.getenv("NER_THRESHOLD", "0.3")),
        "max_text_len": int(os.getenv("MAX_TEXT_LEN", "4000")),
    }


def _load_model() -> bool:
    """Load the GLiNER2 model and adapter.
    
    Returns True if successful, False otherwise.
    Model is cached in global variable for reuse across invocations.
    """
    global _model_instance, _model_loading, _model_error
    
    if _model_instance is not None:
        return True
    
    if _model_loading:
        return False  # Already loading
    
    _model_loading = True
    _model_error = None
    
    try:
        from gliner2 import GLiNER2
        
        settings = _get_settings()
        log.info("Loading base model: %s", settings["base_model"])
        
        # Load base model
        model = GLiNER2.from_pretrained(settings["base_model"])
        
        # Load adapter from Lambda layer
        adapter_path = settings["adapter_path"]
        log.info("Loading adapter from: %s", adapter_path)
        
        if not os.path.exists(adapter_path):
            raise FileNotFoundError(f"Adapter not found at {adapter_path}")
        
        model.load_adapter(adapter_path)
        
        _model_instance = model
        _model_loading = False
        log.info("Model loaded successfully!")
        return True
        
    except Exception as exc:
        log.exception("Model load failed")
        _model_error = str(exc)
        _model_loading = False
        return False


def _extract_entities(text: str, labels: List[str], threshold: float) -> List[Dict[str, Any]]:
    """Extract entities from text using the loaded model."""
    import re
    
    if _model_instance is None:
        raise RuntimeError("Model not loaded")
    
    spans: List[Dict[str, Any]] = []
    
    # Try span-level API first
    try:
        raw = _model_instance.predict_entities(text, labels, threshold=threshold)
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
        # Fallback: grouped API
        res = _model_instance.extract_entities(text, labels)
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
    
    # Sort and remove overlaps
    spans.sort(key=lambda d: (d["start"], d["end"]))
    clean, last_end = [], -1
    for s in spans:
        if s["start"] >= last_end:
            clean.append(s)
            last_end = s["end"]
    
    return clean


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry point.
    
    Args:
        event: Lambda event containing request data
        context: Lambda context object
    
    Returns:
        Lambda response with CORS headers
    """
    # Handle Lambda Function URL format
    if "requestContext" in event and "http" in event["requestContext"]:
        # Lambda Function URL format
        http_method = event["requestContext"]["http"]["method"]
        path = event["requestContext"]["http"]["path"]
        body = event.get("body", "{}")
        
        # Parse body if it's a string (Lambda URL sends as string)
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = {}
    else:
        # Direct invocation format (for testing)
        http_method = "POST"
        path = "/api/ner"
        body = event
    
    # Default CORS headers
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Amz-Date, Authorization, X-Api-Key",
    }
    
    # Handle OPTIONS (CORS preflight)
    if http_method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": "",
        }
    
    # Handle health check
    if path == "/health" or (event.get("resource", "") == "/health" and http_method == "GET"):
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "status": "ok",
                "model_loaded": _model_instance is not None,
                "model_error": _model_error,
            }),
        }
    
    # Handle NER inference
    if path == "/api/ner" or http_method == "POST":
        # Rate limiting check
        client_id = _get_client_id(event)
        if not _check_rate_limit(client_id):
            return {
                "statusCode": 429,
                "headers": headers,
                "body": json.dumps({
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds",
                    "retry_after": RATE_LIMIT_WINDOW,
                }),
            }
        
        # Ensure model is loaded
        if _model_instance is None:
            log.info("Loading model on first request...")
            start_time = time.perf_counter()
            if not _load_model():
                return {
                    "statusCode": 500,
                    "headers": headers,
                    "body": json.dumps({
                        "error": "Model failed to load",
                        "details": _model_error,
                    }),
                }
            load_time = round((time.perf_counter() - start_time) * 1000, 2)
            log.info("Model loaded in %d ms", load_time)
        
        # Extract request parameters
        text = body.get("text", "")
        labels = body.get("labels", _get_settings()["labels"])
        threshold = body.get("threshold", _get_settings()["threshold"])
        
        # Validate input with abuse prevention
        if not text:
            return {
                "statusCode": 422,
                "headers": headers,
                "body": json.dumps({"error": "Text is required"}),
            }
        
        # Prevent abuse: limit text length
        max_len = _get_settings()["max_text_len"]
        if len(text) > max_len:
            return {
                "statusCode": 413,
                "headers": headers,
                "body": json.dumps({
                    "error": "Text too long",
                    "message": f"Maximum length is {max_len} characters",
                    "current_length": len(text),
                }),
            }
        
        labels = [l.strip().upper() for l in labels if l.strip()]
        if not labels:
            return {
                "statusCode": 422,
                "headers": headers,
                "body": json.dumps({"error": "At least one label is required"}),
            }
        
        # Perform inference
        try:
            start_time = time.perf_counter()
            spans = _extract_entities(text, labels, threshold)
            inference_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            # Group entities by label
            grouped: Dict[str, List[str]] = {}
            for s in spans:
                grouped.setdefault(s["label"], [])
                if s["text"] not in grouped[s["label"]]:
                    grouped[s["label"]].append(s["text"])
            
            response = {
                "entities": spans,
                "grouped": grouped,
                "counts": {k: len(v) for k, v in grouped.items()},
                "total": len(spans),
                "inference_ms": inference_ms,
                "model": {
                    "framework": "GLiNER2",
                    "base": _get_settings()["base_model"],
                    "adapter": "/opt/adapter/best",
                    "dataset": "Geopolitical Wiki News Dataset",
                },
            }
            
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps(response),
            }
            
        except Exception as exc:
            log.exception("Inference failed")
            return {
                "statusCode": 500,
                "headers": headers,
                "body": json.dumps({
                    "error": "Inference failed",
                    "details": str(exc),
                }),
            }
    
    # Handle info endpoint
    if path == "/api/info" or (event.get("resource", "") == "/api/info" and http_method == "GET"):
        settings = _get_settings()
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "name": "GeoNER API",
                "framework": "GLiNER2",
                "base_model": settings["base_model"],
                "adapter": settings["adapter_path"],
                "finetuned_on": "Geopolitical Wiki News Dataset",
                "labels": settings["labels"],
                "threshold": settings["threshold"],
                "max_text_len": settings["max_text_len"],
                "author": "Saurabh Hadole (AVI)",
            }),
        }
    
    # Unknown path
    return {
        "statusCode": 404,
        "headers": headers,
        "body": json.dumps({"error": "Not found"}),
    }
