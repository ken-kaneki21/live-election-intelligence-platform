import json
import sys
from collections import Counter


def inspect_geojson(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if "features" not in data:
        print("Invalid GeoJSON: no 'features' key found.")
        return

    features = data["features"]

    print("=" * 80)
    print("GEOJSON INSPECTION REPORT")
    print("=" * 80)

    print(f"\nTotal features: {len(features)}")

    if not features:
        print("No features found.")
        return

    print("\nTop-level keys:")
    print(list(data.keys()))

    print("\nFirst feature keys:")
    print(list(features[0].keys()))

    properties = features[0].get("properties", {})

    print("\nProperty keys in first feature:")
    for key in properties.keys():
        print(f"- {key}")

    print("\nFirst feature properties:")
    for key, value in properties.items():
        print(f"{key}: {value}")

    print("\nSample property values from first 20 features:")
    all_property_keys = set()

    for feature in features:
        all_property_keys.update(feature.get("properties", {}).keys())

    for key in sorted(all_property_keys):
        print("\n" + "-" * 60)
        print(f"Property: {key}")

        values = []
        for feature in features[:20]:
            value = feature.get("properties", {}).get(key)
            values.append(value)

        for value in values:
            print(value)

    print("\nPossible constituency name fields:")
    possible_name_fields = []

    for key in sorted(all_property_keys):
        key_lower = key.lower()
        if (
            "name" in key_lower
            or "const" in key_lower
            or "ac" in key_lower
            or "assembly" in key_lower
            or "district" in key_lower
            or "pc" in key_lower
        ):
            possible_name_fields.append(key)

    if possible_name_fields:
        for key in possible_name_fields:
            print(f"- {key}")
    else:
        print("No obvious constituency-name field found.")

    print("\nProperty value uniqueness:")
    for key in sorted(all_property_keys):
        values = [
            feature.get("properties", {}).get(key)
            for feature in features
            if feature.get("properties", {}).get(key) is not None
        ]
        counter = Counter(values)
        print(f"{key}: {len(counter)} unique values")

    print("\nDone.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage:")
        print("python inspect_geojson_properties.py data/geojson/tamil_nadu_ac.geojson")
        sys.exit(1)

    inspect_geojson(sys.argv[1])