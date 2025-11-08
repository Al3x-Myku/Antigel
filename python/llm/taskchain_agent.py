import asyncio
import os

from agno.agent import Agent
from agno.models.azure import AzureOpenAI
from agno.tools.mcp import MCPTools


async def main() -> None:
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("GRAPHRAG_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", os.getenv("OPENAI_API_VERSION"))
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")

    if not api_key:
        raise RuntimeError("Missing AZURE_OPENAI_API_KEY / GRAPHRAG_API_KEY")
    if not azure_endpoint:
        raise RuntimeError("Missing AZURE_OPENAI_ENDPOINT")
    if not api_version:
        raise RuntimeError("Missing AZURE_OPENAI_API_VERSION / OPENAI_API_VERSION")

    taskchain_tools = MCPTools(
        command="python mcp_blockchain_tasks.py",
        env={**os.environ},
        timeout_seconds=60,
    )

    await taskchain_tools.connect()

    model = AzureOpenAI(
        id=deployment,
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        azure_deployment=deployment,
        api_version=api_version,
    )

    agent = Agent(
        name="Taskchain Agent",
        model=model,
        instructions=[
            "You are a task matchmaking assistant.",
            "Use the TaskChain MCP tools (list_tasks, list_active_tasks, get_task) "
            "to fetch on-chain tasks instead of guessing.",
        ],
        tools=[taskchain_tools],
        markdown=True,
    )

    try:
        await agent.aprint_response(
            "Use the TaskChain MCP tools to call list_active_tasks and summarize the open tasks.",
            stream=True,
        )
    finally:
        # This helps avoid the asyncgen/TaskGroup cleanup warning
        if hasattr(taskchain_tools, "close") and callable(taskchain_tools.close):
            await taskchain_tools.close()


if __name__ == "__main__":
    asyncio.run(main())