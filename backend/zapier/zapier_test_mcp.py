import json
import asyncio
from dotenv import load_dotenv
from pathlib import Path
import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from zapier.zapier_config import ZAPIER_APPS_CONFIG

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

async def main():
    print(ZAPIER_APPS_CONFIG["gmail"]["selected_api"])

# async def main():
    
#     client = MultiServerMCPClient(
#         {
#             "zapier": {
#                 "transport": "http",
#                 "url": os.getenv("ZAPIER_MCP_URL")
#             }
#         }
#     )

#     tools = await client.get_tools()

#     # STEP 1 : Display zaiper actions
#     # # # tool = next(
#     # # #     t for t in tools
#     # # #     if t.name == "discover_zapier_actions"
#     # # # )

#     # # # result = await tool.ainvoke({})
#     # # # print(result)



#     # STEP 2 : Enable zapier action (you need to enable all Added App once)
#     # # # tool = next(
#     # # #     t for t in tools
#     # # #     if t.name == "enable_zapier_action"
#     # # # )

#     # # # result = await tool.ainvoke(
#     # # # {
#     # # #     "selected_api":"GoogleDriveCLIAPI"
#     # # # })

#     # # # print(result)

#     # STEP 3 : List enabled actions
#     # # # tool = next(
#     # # #     t for t in tools
#     # # #     if t.name == "list_enabled_zapier_actions"
#     # # # )

#     # # # print(await tool.ainvoke({}))

#     # STEP 4 : Discover the exact actions and parameters for each app
#     # # # tool = next(
#     # # #     t for t in tools
#     # # #     if t.name == "list_enabled_zapier_actions"
#     # # # )

#     # # # print("GMAIL : ")
#     # # # print(await tool.ainvoke({"selected_api": "GoogleMailV2CLIAPI"}))

#     # # # print("GOOGLE SPREADSHEET : ")
#     # # # print(await tool.ainvoke({"selected_api": "GoogleSheetsV2CLIAPI"}))

#     # # # print("GOOGLE DOCS : ")
#     # # # print(await tool.ainvoke({"selected_api": "GoogleDocsV2CLIAPI"}))


#     # STEP 5 
#     # # # tool = next(
#     # # #     t for t in tools
#     # # #     if t.name == "list_enabled_zapier_actions"
#     # # # )

#     # # # result = await tool.ainvoke({
#     # # #     "selected_api": "GoogleMailV2CLIAPI",
#     # # #     "action": "message"
#     # # # })

#     # # # print(result)


#     tool = next(
#         t for t in tools
#         if t.name == "execute_zapier_write_action"
#     )

#     print("tool.args_schema : ")
#     print(type(tool.args_schema))
#     print("json.dumps(tool.args_schema, indent=4) : ")
#     print(json.dumps(tool.args_schema, indent=4))
#     print("tool : ")
#     print(tool)


asyncio.run(main())