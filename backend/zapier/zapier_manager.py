import asyncio
import os
import json

from dotenv import load_dotenv
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class ZapierManager:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):

        if cls._instance is None:
            cls._instance = super().__new__(cls)

            cls._instance._initialized = False
            cls._instance.client = None
            cls._instance.tools = {}

        return cls._instance

    async def connect(self):

        if self._initialized:
            return

        async with self._lock:

            if self._initialized:
                return

            print("Connecting to Zapier MCP...")

            self.client = MultiServerMCPClient(

                {
                    "zapier": {
                        "transport": "http",
                        "url": os.getenv("ZAPIER_MCP_URL")
                    }
                }
            )

            tools = await self.client.get_tools()

            self.tools = {
                tool.name: tool
                for tool in tools
            }

            self._initialized = True

            print(f"Zapier MCP Connected ({len(self.tools)} tools)")


    # Reset Connection
    def reset(self):
        self.client = None
        self.tools = {}
        self._initialized = False

    def get_tool(self, name):

        if name not in self.tools:

            raise ValueError(
                f"Zapier tool '{name}' not found.\n"
                f"Available tools:\n"
                + "\n".join(sorted(self.tools.keys()))
            )

        return self.tools[name]

    async def _execute(self, selected_api, action, tool_name, params, instructions, output):
        #
        # New MCP servers expose the actual tool directly
        #

        tool = self.get_tool(tool_name)

        # payload = {
        #     "selected_api": selected_api,
        #     "action": action,
        #     "tool_name": tool_name,
        #     "instructions": instructions,
        #     "params": params,
        #     "output": output,
        # }

        payload = {
            "selected_api": selected_api,
            "action": action,
            "tool_name": tool_name,
            "instructions": instructions,
            "output": output,
        }

        if tool_name == "gmail_find_email":
            payload["query"] = params
        else:
            payload["params"] = params



        # print("PAYLOAD")
        # print(json.dumps(payload, indent=2))

        return await tool.ainvoke(payload)

        # # # tool = self.get_tool("gmail_find_email")

        # # # result = await tool.ainvoke(
        # # # {
        # # #     "instructions":"Find newest email.",
        # # #     "query":"from:zapier in:inbox"
        # # # })

        # print("TYPE")
        # print(type(result))
        # print("REPR")
        # print(repr(result))
        # print("RESPONSE")
        # print(result)


    async def execute(self, selected_api, action, tool_name, params, instructions="", output="Return success or failure."):

        await self.connect()

        try:

            return await self._execute(
                selected_api,
                action,
                tool_name,
                params,
                instructions,
                output
            )

        except Exception as e:

            msg = str(e).lower()
            print(f"Zapier MCP Error: {e}")

            if any(x in msg for x in ("connection", "transport", "closed", "broken pipe", "reset by peer", "session", "timeout", "refused")):

                # Reconnect once
                print("Attempting MCP reconnect...")

                self.reset()
                await self.connect()

                try:

                    return await self._execute(
                        selected_api,
                        action,
                        tool_name,
                        params,
                        instructions,
                        output
                    )

                except Exception:
                    raise
            else:
                print("ERROR IN ZAIPER MANAGER : ")
                print(str(e))
                raise


_manager = ZapierManager()

def get_zapier_manager():

    return _manager