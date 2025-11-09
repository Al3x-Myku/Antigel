import os

from fastapi import FastAPI

from agno.agent import Agent
from agno.models.azure import AzureOpenAI
from agno.tools.mcp import MCPTools
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI

# ========= ENV / AZURE CONFIG =========

API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("GRAPHRAG_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
API_VERSION = (
    os.getenv("AZURE_OPENAI_API_VERSION")
    or os.getenv("OPENAI_API_VERSION")
    or "2024-12-01-preview"
)
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-nano")

if not API_KEY:
    raise RuntimeError("Missing AZURE_OPENAI_API_KEY / GRAPHRAG_API_KEY")
if not AZURE_ENDPOINT:
    raise RuntimeError("Missing AZURE_OPENAI_ENDPOINT")

# ========= MCP: TASKCHAIN TOOLS =========

# Important: do NOT call asyncio.run() here.
# We connect/disconnect in FastAPI startup/shutdown events.
taskchain_tools = MCPTools(
    command="python mcp_blockchain_tasks.py",
    env={**os.environ},
    timeout_seconds=60,
)

# ========= MODEL =========

model = AzureOpenAI(
    id=DEPLOYMENT,
    api_key=API_KEY,
    azure_endpoint=AZURE_ENDPOINT,
    azure_deployment=DEPLOYMENT,
    api_version=API_VERSION,
)

# ========= AGENT =========

taskchain_agent = Agent(
    name="Taskchain Agent",
    model=model,
    instructions=[
            """
You are SideQuests AI. Here's the ultra-compact version:
	1.	Who you help

	•	Campus, company, event/community users.
	•	Many are new to Web3 → be clear, simple, direct.

	2.	What SideQuests is

	•	Real-world micro-tasks + rewards.
	•	People post tasks; others complete them.
	•	Rewards = tokenized points:
	•	On-chain for transparency.
	•	Redeemable for perks (varies by deployment).
	•	Always show RAW (e.g. 1e-16 = raw 100).

	3.	How you think & talk

	•	First: answer the question.
	•	Then: offer a concrete next step (find quests, draft quest, check rewards).
	•	No jargon unless asked. No hype. No cringe.

If the user asks for tasks and you don't receive anything, don't hallucinate, fabricate, or lie to the user.
Reward should be shown in raw format only, for example: for 1e-16, you need to show 100.
"""
        ],
    tools=[taskchain_tools],
    markdown=True,
)

# ========= AG-UI / AGENTOS =========

agent_os = AgentOS(
    agents=[taskchain_agent],
    interfaces=[AGUI(agent=taskchain_agent)],
)

app: FastAPI = agent_os.get_app()


# ========= LIFECYCLE: CONNECT MCP TOOLS =========

@app.on_event("startup")
async def startup_event():
    # Connect MCPTools once the FastAPI app starts
    await taskchain_tools.connect()


@app.on_event("shutdown")
async def shutdown_event():
    # Cleanly close MCP connection on shutdown (if supported)
    close = getattr(taskchain_tools, "close", None)
    if callable(close):
        await close()


# ========= ENTRYPOINT =========

if __name__ == "__main__":
    # Use AgentOS.serve (wraps uvicorn)
    agent_os.serve(app="taskchain_server:app", host="0.0.0.0", port=7777, reload=False)