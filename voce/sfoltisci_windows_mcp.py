import json, os, sys
sys.path.insert(0, r"d:\assistenteeee\odysseus"); os.chdir(r"d:\assistenteeee\odysseus")
from core.database import SessionLocal, McpServer

ESCLUSI = "Registry,Notification,MultiSelect,MultiEdit,Move,DisplayInventory,Process"
UV = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe"

db = SessionLocal()
s = db.query(McpServer).filter(McpServer.name == "windows-mcp").first()
if not s:
    print("windows-mcp non registrato"); raise SystemExit(1)

s.command = UV
s.args = json.dumps(["--directory", r"d:\assistenteeee\Windows-MCP", "run",
                     "windows-mcp", "serve", "--exclude-tools", ESCLUSI])
s.env = json.dumps({"UV_NO_SYNC": "1", "ANONYMIZED_TELEMETRY": "false",
                    "WINDOWS_MCP_MAX_TREE_ELEMENTS": "180"})
db.commit()
print("windows-mcp aggiornato:")
print("  esclusi:", ESCLUSI)
print("  limite albero: 180 elementi")
db.close()
