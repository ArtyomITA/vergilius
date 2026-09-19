"""Misura quanto costa in token una fotografia dell'interfaccia (Windows-MCP).

Serve a tarare WINDOWS_MCP_MAX_TREE_ELEMENTS: la ricerca dice che sopra i ~3.500
token per osservazione un modello da 9B peggiora invece di migliorare.

Uso:
    d:\\assistenteeee\\odysseus\\venv\\Scripts\\python.exe misura_snapshot.py [limite]

Il limite (numero massimo di elementi dell'albero) si passa come argomento; senza
argomento usa il predefinito di Windows-MCP (500).
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, r"d:\assistenteeee\odysseus")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

UV = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe"
WINDOWS_MCP = r"d:\assistenteeee\Windows-MCP"


def stima_token(testo: str) -> int:
    """~3.6 caratteri per token: media osservata su testo strutturato inglese."""
    return round(len(testo) / 3.6)


async def misura(max_elementi: str | None):
    env = dict(os.environ, UV_NO_SYNC="1", ANONYMIZED_TELEMETRY="false")
    if max_elementi:
        env["WINDOWS_MCP_MAX_TREE_ELEMENTS"] = max_elementi

    params = StdioServerParameters(
        command=UV,
        args=["--directory", WINDOWS_MCP, "run", "windows-mcp", "serve"],
        env=env,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            schemi = json.dumps([t.model_dump() for t in tools.tools])
            print(f"strumenti registrati : {len(tools.tools)}")
            print(f"schemi degli strumenti: {stima_token(schemi):>7} token "
                  f"({len(schemi)} caratteri)")
            print()

            for nome, args in [
                ("Snapshot (albero UI)", {"use_vision": False, "use_ui_tree": True}),
                ("Snapshot (senza albero)", {"use_vision": False, "use_ui_tree": False}),
            ]:
                try:
                    res = await session.call_tool("Snapshot", args)
                    testo = "".join(
                        c.text for c in res.content if getattr(c, "text", None)
                    )
                    print(f"{nome:<26} {stima_token(testo):>7} token "
                          f"({len(testo)} caratteri)")
                except Exception as e:
                    print(f"{nome:<26} errore: {e}")


if __name__ == "__main__":
    limite = sys.argv[1] if len(sys.argv) > 1 else None
    etichetta = limite or "predefinito (500)"
    print(f"=== limite elementi albero: {etichetta} ===\n")
    asyncio.run(misura(limite))
