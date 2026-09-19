"""Come misura_snapshot.py, ma con la configurazione sfoltita che vogliamo adottare:
strumenti esclusi + limite basso sugli elementi dell'albero.

Confronta il prima e il dopo per decidere se conviene.
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

ESCLUSI = "Registry,Notification,MultiSelect,MultiEdit,Move,DisplayInventory,Process"
MAX_ELEMENTI = "180"


def stima_token(testo: str) -> int:
    return round(len(testo) / 3.6)


async def misura():
    env = dict(
        os.environ,
        UV_NO_SYNC="1",
        ANONYMIZED_TELEMETRY="false",
        WINDOWS_MCP_MAX_TREE_ELEMENTS=MAX_ELEMENTI,
        WINDOWS_MCP_EXCLUDE_TOOLS=ESCLUSI,
    )

    params = StdioServerParameters(
        command=UV,
        args=["--directory", WINDOWS_MCP, "run", "windows-mcp", "serve",
              "--exclude-tools", ESCLUSI],
        env=env,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            schemi = json.dumps([t.model_dump() for t in tools.tools])
            print(f"strumenti registrati  : {len(tools.tools)}")
            print(f"  {', '.join(sorted(t.name for t in tools.tools))}")
            print(f"schemi degli strumenti: {stima_token(schemi):>7} token")
            print()

            res = await session.call_tool(
                "Snapshot", {"use_vision": False, "use_ui_tree": True})
            testo = "".join(c.text for c in res.content if getattr(c, "text", None))
            print(f"Snapshot (albero UI)  : {stima_token(testo):>7} token "
                  f"({len(testo)} caratteri)")

            fisso = stima_token(schemi)
            print()
            print(f"costo fisso per richiesta : {fisso} token "
                  f"({fisso / 49152 * 100:.1f}% del contesto da 48K)")
            print(f"costo di una osservazione : {stima_token(testo)} token")


if __name__ == "__main__":
    print(f"=== sfoltito: esclusi {ESCLUSI.count(',') + 1} strumenti, "
          f"limite albero {MAX_ELEMENTI} ===\n")
    asyncio.run(misura())
