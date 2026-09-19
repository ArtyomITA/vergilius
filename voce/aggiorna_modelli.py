import json, os, sys
sys.path.insert(0, r"d:\assistenteeee\odysseus"); os.chdir(r"d:\assistenteeee\odysseus")
from core.database import SessionLocal, ModelEndpoint

MODELLI = ["qwenpaw", "qwenpaw-vista", "heretic", "heretic-vista"]

db = SessionLocal()
ep = db.query(ModelEndpoint).filter(ModelEndpoint.base_url == "http://127.0.0.1:8012/v1").first()
if not ep:
    print("endpoint llama non trovato"); raise SystemExit(1)
ep.cached_models = json.dumps(MODELLI)
ep.hidden_models = json.dumps([])
ep.model_refresh_mode = "auto"
db.commit()
print("modelli disponibili:", ep.cached_models)
eid = ep.id
db.close()

path = os.path.join(r"d:\assistenteeee\odysseus", "data", "settings.json")
with open(path, encoding="utf-8") as f:
    s = json.load(f)
s["default_endpoint_id"] = eid
s["default_model"] = "heretic"
s["utility_endpoint_id"] = eid
s["utility_model"] = "qwenpaw"
s["vision_model"] = "heretic-vista"
s["vision_enabled"] = True
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(s, f, indent=2, ensure_ascii=False)
os.replace(tmp, path)
print("default_model=heretic, vision_model=heretic-vista, utility=qwenpaw")
