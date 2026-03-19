import json

with open("raw_data/articles_en-us.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total articles: {len(data)}")
print(f"With title: {sum(1 for a in data if a.get('title'))}")
print(f"With content: {sum(1 for a in data if a.get('content'))}")
print()

# Check what fields the titleless articles have
a20 = data[20]
print("Fields in article 20 (no title):")
for k, v in a20.items():
    val = str(v)[:80] if v else "EMPTY"
    print(f"  {k}: {val}")
print()

# Check if titleless articles have content or description
for i, a in enumerate(data[20:25], 20):
    desc = a.get("description", "")[:80]
    has_c = bool(a.get("content"))
    art_id = a.get("articlepublicnumber", "N/A")
    print(f"{i}: id={art_id} content={has_c} desc={desc}")
