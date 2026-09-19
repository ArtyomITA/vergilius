import os, sys, asyncio
sys.path.insert(0, r"d:\assistenteeee\odysseus"); os.chdir(r"d:\assistenteeee\odysseus")
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    p = StdioServerParameters(
        command="npx.cmd",
        args=["-y", "@playwright/mcp@latest", "--headless", "--isolated",
              "--snapshot-mode", "none", "--output-mode", "file",
              "--image-responses", "omit"],
        env=dict(os.environ),
    )
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            t = await s.list_tools()
            nomi = sorted(x.name for x in t.tools)
            print(f"strumenti: {len(nomi)}")
            for n in nomi: print(" ", n)

asyncio.run(main())
