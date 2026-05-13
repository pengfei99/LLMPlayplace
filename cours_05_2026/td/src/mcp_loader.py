from langchain_mcp_adapters.client import MultiServerMCPClient


async def load_open_meteo_mcp_tools_stdio():
    """
    Charge les tools MCP Open-Meteo via stdio en lançant le serveur avec npx.
    Nécessite Node.js + npm.
    """
    client = MultiServerMCPClient(
        {
            "weather": {
                "transport": "stdio",
                "command": "npx",
                "args": [
                    "-y",
                    "-p",
                    "open-meteo-mcp-server",
                    "open-meteo-mcp-server",
                ],
            }
        }
    )
    return await client.get_tools()


async def load_open_meteo_mcp_tools_http(base_url: str = "http://localhost:3000/mcp"):
    """
    Charge les tools MCP Open-Meteo via HTTP
    """
    client = MultiServerMCPClient(
        {
            "weather": {
                "transport": "streamable_http",
                "url": base_url,
            }
        }
    )
    return await client.get_tools()
