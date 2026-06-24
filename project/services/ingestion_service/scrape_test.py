import json
from collections import Counter

with open("data/output.json", encoding="utf-8") as f:
    records = json.load(f)

print("Total:", len(records))
print("Sources:", Counter(r.get("source") for r in records))
print("Errors:", sum(1 for r in records if "error" in r))
print("Empty program_name:", sum(1 for r in records if not r.get("program_name")))
print("Empty sections:", sum(1 for r in records if not r.get("sections")))

with open("data/output.json", encoding="utf-8") as f:
    records = json.load(f)

for r in records:
    if "error" in r or not r.get("program_name") or not r.get("sections"):
        print("-" * 80)
        print("source:", r.get("source"))
        print("program_id:", r.get("program_id"))
        print("program_name:", r.get("program_name"))
        print("url:", r.get("url"))
        print("error:", r.get("error"))
        print("sections:", len(r.get("sections", [])))