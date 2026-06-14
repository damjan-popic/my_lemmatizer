import json
from pathlib import Path

INPUT  = Path("loris_rules_final.json")
OUTPUT = Path("loris_rules_final_clean.json")

def strip_strings(obj):
    """Recursively strip leading/trailing whitespace from all string values."""
    if isinstance(obj, dict):
        return {k: strip_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [strip_strings(x) for x in obj]
    elif isinstance(obj, str):
        return obj.strip()
    else:
        return obj

def main():
    with INPUT.open("r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned = strip_strings(data)

    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"Cleaned JSON written to {OUTPUT}")

if __name__ == "__main__":
    main()
