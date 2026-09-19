
import sys
sys.path.insert(0, "d:/assistenteeee/odysseus")
from fastapi import FastAPI
from routes.stt_routes import setup_stt_routes

class FintoServizio:
    available = False
    def get_stats(self): return {}
    def transcribe(self, b): return None

app = FastAPI()
app.include_router(setup_stt_routes(FintoServizio()))
