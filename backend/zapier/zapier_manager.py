import asyncio
import time

from langchain_mcp_adapters.client import MultiServerMCPClient


class ZapierManager:

    def __init__(self):

        self.connections = {}

        self.lock = asyncio.Lock()

    ##########################################################
    # Connect one user
    ##########################################################

    async def connect(self, user_id, mcp_url):

        #
        # Already connected?
        #

        if user_id in self.connections:

            return

        async with self.lock:

            if user_id in self.connections:

                return

            print(f"Connecting MCP for {user_id}")

            client = MultiServerMCPClient(

                {
                    "zapier": {
                        "transport": "http",
                        "url": mcp_url
                    }
                }

            )

            tools = await client.get_tools()

            # # # for tool in tools:

            # # #     if tool.name == 'gmail_send_email':

            # # #         print("\n==============================")
            # # #         print("TOOL:", tool.name)
            # # #         # print("DESCRIPTION:", tool.description)
            # # #         print("ARGS:", tool.args)
            # # #         # print("SCHEMA:", tool.args_schema)

            self.connections[user_id] = {

                "client": client,
                "tools": {
                    tool.name: tool
                    for tool in tools
                },
                "connected_at": time.time()
            }

            print(
                f"{user_id} connected ({len(tools)} tools)"
            )

            # # # for tool_name in sorted(self.connections[user_id]["tools"].keys()):
            # # #     print("MCP TOOL:", tool_name)

    ##########################################################
    # Disconnect
    ##########################################################

    def disconnect(self, user_id):

        if user_id in self.connections:

            del self.connections[user_id]

    ##########################################################
    # Get Tool
    ##########################################################

    def get_tool(self, user_id, tool_name):

        if user_id not in self.connections:

            raise Exception(
                "User not connected."
            )

        tools = self.connections[user_id]["tools"]

        if tool_name not in tools:

            raise Exception(

                f"{tool_name} not found.\n"

                + "\n".join(
                    sorted(tools.keys())
                )

            )

        return tools[tool_name]

    async def execute_tool(self, user_id, mcp_url, tool_name, params):
        await self.connect(user_id, mcp_url)

        try:

            tool = self.get_tool(user_id, tool_name)

            return await tool.ainvoke(params)

        except Exception as ex:

            print("Zapier tool execute error:", ex)

            self.disconnect(user_id)

            await self.connect(user_id, mcp_url)

            tool = self.get_tool(user_id, tool_name)

            return await tool.ainvoke(params)

    ##########################################################
    # Execute
    ##########################################################

    async def execute(
        self,
        user_id,
        mcp_url,
        selected_api,
        action,
        tool_name,
        params,
        instructions="",
        output=""
    ):

        await self.connect(
            user_id,
            mcp_url
        )

        payload = params.copy()

        try:

            tool = self.get_tool(user_id, tool_name)

            # payload = {
            #     "selected_api": selected_api,
            #     "action": action,
            #     "tool_name": tool_name,
            #     "instructions": instructions,
            #     "output": output
            # }

            # if tool_name == "gmail_find_email":
            #     payload["query"] = params
            # else:
            #     payload["params"] = params

            

            if tool_name == "gmail_find_email":
                payload = {
                    "query": params
                }

            return await tool.ainvoke(payload)

        except Exception as ex:

            print(ex)

            print("Zapier execute error:", ex)

            # IMPORTANT:
            # Do not automatically retry Gmail write operations.
            # The first request may already have succeeded.

            if tool_name in [
                "gmail_send_email",
                "gmail_create_draft",
                "gmail_reply_to_email",
            ]:
                raise

            # Retry read/non-destructive operations only
            self.disconnect(user_id)

            await self.connect(user_id, mcp_url)

            tool = self.get_tool(user_id, tool_name)

            return await tool.ainvoke(payload)


_manager = ZapierManager()


def get_zapier_manager():

    return _manager