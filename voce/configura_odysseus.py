"""Registra il ponte voce in Odysseus e imposta le chiavi TTS/STT.

Il pannello voce dell'interfaccia è disattivato in questa versione di Odysseus,
quindi la configurazione va scritta direttamente: l'endpoint nel database (usando
i modelli di Odysseus, così i campi restano coerenti) e le chiavi in settings.json
(che l'app rilegge da sola entro 2 secondi).

Uso:  d:\\assistenteeee\\odysseus\\venv\\Scripts\\python.exe configura_odysseus.py
"""

import json
import os
import sys
import uuid

ODYSSEUS = r"d:\assistenteeee\odysseus"
sys.path.insert(0, ODYSSEUS)
os.chdir(ODYSSEUS)

from core.database import ModelEndpoint, SessionLocal  # noqa: E402

BASE_URL = "http://127.0.0.1:8013/v1"
NAME = "voce-locale"


def ensure_endpoint() -> str:
    db = SessionLocal()
    try:
        row = db.query(ModelEndpoint).filter(ModelEndpoint.base_url == BASE_URL).first()
        if row:
            print(f"endpoint già presente: {row.id} ({row.name})")
            return row.id

        row = ModelEndpoint(
            id=uuid.uuid4().hex[:8],
            name=NAME,
            base_url=BASE_URL,
            api_key="",
            is_enabled=True,
            model_type="llm",       # "tts" non è tra i tipi accettati dalla UI
            endpoint_kind="local",
            model_refresh_mode="manual",
            cached_models=json.dumps(["pocket-tts", "parakeet"]),
            supports_tools=False,
        )
        db.add(row)
        db.commit()
        print(f"endpoint creato: {row.id}")
        return row.id
    finally:
        db.close()


def write_settings(endpoint_id: str) -> None:
    path = os.path.join(ODYSSEUS, "data", "settings.json")
    with open(path, encoding="utf-8") as f:
        settings = json.load(f)

    settings.update({
        "tts_enabled": True,
        "tts_provider": f"endpoint:{endpoint_id}",
        "tts_model": "pocket-tts",
        "tts_voice": "estelle",
        "tts_speed": "1",
        "stt_enabled": True,
        # "stream" = trascrizione in diretta via WebSocket (/api/stt/stream),
        # Nemotron-3.5 dentro il ponte. Il testo arriva mentre parli e il turno
        # si chiude da solo dopo ~800 ms di silenzio.
        # Per tornare al giro precedente (registra tutto, poi Parakeet) basta
        # rimettere f"endpoint:{endpoint_id}": resta installato e funzionante.
        "stt_provider": os.getenv("STT_PROVIDER", "stream"),
        "stt_model": "nemotron-3.5-streaming",
        "stt_language": "it",
    })

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    print("settings.json aggiornato (tts_provider, stt_provider, voce, lingua)")


if __name__ == "__main__":
    eid = ensure_endpoint()
    write_settings(eid)
    print("\nfatto. Ricarica Odysseus nel browser (Ctrl+F5).")
