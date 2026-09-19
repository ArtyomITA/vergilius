import json, os, sys
sys.path.insert(0, r"d:\assistenteeee\odysseus"); os.chdir(r"d:\assistenteeee\odysseus")
from core.database import SessionLocal, ModelEndpoint
db = SessionLocal()
ep = db.query(ModelEndpoint).filter(ModelEndpoint.base_url == "http://127.0.0.1:8013/v1").first()
if not ep:
    print("endpoint voce non trovato"); raise SystemExit(1)
ep.hidden_models = json.dumps(["pocket-tts", "parakeet"])
db.commit()
print("nascosti dal menu:", ep.hidden_models)
print("endpoint:", ep.id, ep.name, "| enabled:", ep.is_enabled)
db.close()
