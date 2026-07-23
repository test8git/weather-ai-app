import asyncio
from zapier.zapier_tools import send_email

async def main():
    result = await send_email(
        "test8cs@gmail.com",
        "Hello",
        "Testing Zapier MCP"
    )

    print(result)


asyncio.run(main())