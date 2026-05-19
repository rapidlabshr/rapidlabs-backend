import json

with open("comment_note.json", "r", encoding="utf-8") as f:
    data = json.load(f)

new_data = []

for entry in data:
    name = entry["category"].strip()

    new_data.append({
        "service_code": entry["service_code"].strip(),
        "category": name,
        "parameter": name,

        "low_comment": f"{name} is reduced.\nThis may indicate decreased physiological levels or underlying pathology.\nClinical correlation and further evaluation are advised.",

        "high_comment": f"{name} is elevated.\nThis may suggest an active pathological or reactive process.\nCorrelation with clinical findings is recommended.",

        "normal_comment": f"{name} is within reference range.\nNo significant abnormality is noted.\nContinue routine clinical correlation."
    })

with open("comment_note_new.json", "w", encoding="utf-8") as f:
    json.dump(new_data, f, indent=2, ensure_ascii=False)

print("Done. Created comment_note_new.json")