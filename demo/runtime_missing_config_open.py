import json

with open("config/settings.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(data)
