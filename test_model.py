from gliner2 import GLiNER2

def test_finetuned_model():
    print("Loading base model: fastino/gliner2-base-v1...")
    model = GLiNER2.from_pretrained("fastino/gliner2-base-v1")
    
    adapter_path = r"C:\Users\hp\Downloads\gliner2_geopolitical_ner_complete\best"
    print(f"Loading adapter from: {adapter_path}...")
    model.load_adapter(adapter_path)
    
    print("Adapter loaded successfully!")
    
    # Example text for geopolitical NER
    text = "The multifront campaign has put Iran under unprecedented pressure, forcing its fatigued population to endure still more strain. Iranian Supreme Leader Mojtaba Khamenei, meanwhile, remains conspicuously absent. Tuesday will mark his sixth month in hiding in an attempt to avoid the fate of his father and predecessor, Ayatollah Ali Khamenei, who was killed in an airstrike at the start of the US-Israeli war against Iran in late February."
    labels = ["GPE", "ORG", "EVENT", "PERSON","DATE"]
    
    print(f"\nRunning inference on text: '{text}'")
    print(f"Looking for labels: {labels}")
    
    results = model.extract_entities(text, labels)
    
    print("\n--- Extraction Results ---")
    if not results or "entities" not in results:
        print("No entities found.")
    else:
        print("Results:")
        # Format is {'entities': {'label': ['text1', 'text2']}}
        entities = results.get("entities", {})
        for label, text_matches in entities.items():
            for text in text_matches:
                print(f"Entity: '{text}' | Label: '{label}'")

if __name__ == "__main__":
    test_finetuned_model()
