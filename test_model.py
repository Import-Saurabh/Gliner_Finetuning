import json
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from gliner2 import GLiNER2


# ============================================================
# CONFIGURATION
# ============================================================

ADAPTER_REPO = "Saurabh18888/gliner-news-geo"
ADAPTER_DIR = Path("./gliner-news-geo")

LABELS = [
    "person",
    "event",
    "org",
    "gpe",
    "date",
    "time",
]


# ============================================================
# DOWNLOAD ADAPTER
# ============================================================

def download_adapter():
    """
    Download the LoRA adapter from Hugging Face into a local
    directory because GLiNER2.load_adapter() expects a local path.
    """

    config_file = ADAPTER_DIR / "adapter_config.json"
    weights_file = ADAPTER_DIR / "adapter_model.safetensors"

    if config_file.exists() and weights_file.exists():

        print("\nAdapter already exists locally.")
        print(f"Path: {ADAPTER_DIR.resolve()}")

        return

    print("\n" + "=" * 70)
    print("DOWNLOADING LORA ADAPTER")
    print("=" * 70)

    snapshot_download(
        repo_id=ADAPTER_REPO,
        local_dir=str(ADAPTER_DIR),
    )

    print("\nAdapter downloaded successfully.")
    print(f"Path: {ADAPTER_DIR.resolve()}")


# ============================================================
# READ ADAPTER CONFIG
# ============================================================

def get_base_model():

    config_path = ADAPTER_DIR / "adapter_config.json"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Missing adapter config: {config_path}"
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    base_model = config.get("base_model_name_or_path")

    if not base_model:
        raise RuntimeError(
            "base_model_name_or_path is missing from "
            "adapter_config.json"
        )

    return base_model


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    print("\n" + "=" * 70)
    print("LOADING GLINER2 MODEL")
    print("=" * 70)

    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"Device: {device}")

    # --------------------------------------------------------
    # Download adapter if required
    # --------------------------------------------------------

    download_adapter()

    # --------------------------------------------------------
    # Get exact base model
    # --------------------------------------------------------

    base_model = get_base_model()

    print(f"Base model: {base_model}")

    # --------------------------------------------------------
    # Load base GLiNER2
    # --------------------------------------------------------

    print("\nLoading base model...")

    model = GLiNER2.from_pretrained(
        base_model,
        map_location=device,
    )

    print("\nBase model loaded successfully.")

    # --------------------------------------------------------
    # Load native GLiNER2 LoRA adapter
    # --------------------------------------------------------

    print("\nLoading LoRA adapter...")

    model.load_adapter(
        str(ADAPTER_DIR.resolve())
    )

    print("LoRA adapter loaded successfully.")

    # --------------------------------------------------------
    # Evaluation mode
    # --------------------------------------------------------

    model.eval()

    print("\nModel ready for inference.")

    return model


# ============================================================
# TEST DATA
# ============================================================

TEST_CASES = [

    (
        "Geopolitical News",
        "Indian Prime Minister Narendra Modi met US President "
        "Donald Trump in Washington on January 15, 2026 to discuss "
        "the Russia-Ukraine war."
    ),

    (
        "Organizations and Locations",
        "The United Nations announced that NATO and the European "
        "Union will hold a meeting in Brussels on March 10, 2026."
    ),

    (
        "Major Event",
        "The G20 Summit will take place in New Delhi next year, "
        "with leaders from India, China, Russia and the United "
        "States attending."
    ),

    (
        "Date and Time",
        "The ceasefire agreement was signed on February 24, 2026 "
        "at 10:30 AM in Geneva."
    ),

    (
        "Russia Ukraine",
        "Russian President Vladimir Putin announced a new military "
        "operation in Ukraine after negotiations failed in Moscow "
        "on June 5, 2026."
    ),

    (
        "India",
        "Prime Minister Narendra Modi addressed the Parliament of "
        "India in New Delhi on August 15, 2026 at 10:00 AM."
    ),

    (
        "United States",
        "Donald Trump met officials from the United States "
        "Department of Defense on July 20, 2026 in Washington."
    ),

    (
        "Middle East",
        "Israel and Iran agreed to participate in peace negotiations "
        "in Geneva on September 12, 2026."
    ),

]


# ============================================================
# EXTRACT ENTITIES
# ============================================================

def extract(model, text):

    return model.extract_entities(
        text,
        LABELS,
        include_confidence=True,
        include_spans=True,
    )


# ============================================================
# DISPLAY RESULT
# ============================================================

def display_result(result):

    entities = result.get("entities", {})

    found = False

    for label in LABELS:

        values = entities.get(label, [])

        if not values:
            continue

        found = True

        print(f"\n[{label.upper()}]")

        for entity in values:

            print(f"  {entity}")

    if not found:

        print("\nNo entities detected.")


# ============================================================
# RUN TESTS
# ============================================================

def run_tests(model):

    print("\n" + "=" * 70)
    print("ENTITY EXTRACTION TEST")
    print("=" * 70)

    print("\nTarget labels:")

    for label in LABELS:
        print(f"  - {label}")

    for index, (name, text) in enumerate(TEST_CASES, 1):

        print("\n")
        print("=" * 70)
        print(f"TEST {index}: {name}")
        print("=" * 70)

        print("\nTEXT:")
        print(text)

        try:

            result = extract(model, text)

            print("\nENTITIES:")
            print("-" * 70)

            display_result(result)

        except Exception as exc:

            print("\nTEST FAILED")
            print(f"{type(exc).__name__}: {exc}")


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 70)
    print("Saurabh18888/gliner-news-geo")
    print("GLiNER2 LoRA MODEL TEST")
    print("=" * 70)

    try:

        model = load_model()

        run_tests(model)

        print("\n")
        print("=" * 70)
        print("TESTING COMPLETED")
        print("=" * 70)

    except Exception as exc:

        print("\n")
        print("=" * 70)
        print("FATAL ERROR")
        print("=" * 70)

        print(f"\n{type(exc).__name__}: {exc}")

        raise


if __name__ == "__main__":
    main()