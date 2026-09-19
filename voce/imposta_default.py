import json, os
path = r"d:\assistenteeee\odysseus\data\settings.json"
with open(path, encoding="utf-8") as f: s = json.load(f)
s["default_model"] = "qwenpaw"
s["vision_model"] = "qwenpaw-vista"
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f: json.dump(s, f, indent=2, ensure_ascii=False)
os.replace(tmp, path)
print("default_model =", s["default_model"], "| vision_model =", s["vision_model"], "| utility =", s["utility_model"])
