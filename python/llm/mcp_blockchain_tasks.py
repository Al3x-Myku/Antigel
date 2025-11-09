#!/usr/bin/env python
import json
import os
from typing import Any, Dict, List, Optional

from web3 import Web3
from mcp.server.fastmcp import FastMCP

# ============================================================
#  CONFIG & DEPLOYMENT LOADING (NEW API)
# ============================================================

SEPOLIA_RPC_URL = os.getenv(
    "SEPOLIA_RPC_URL",
    "https://sepolia.infura.io/v3/713dcbe5e2254d718e5040c2ae716c3f",
)

# Resolve deployment.json:
# By default we assume repo layout:
#   /Antigel/deployment.json
#   /Antigel/python/llm/mcp_blockchain_tasks.py
# So from this file: ../../deployment.json
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DEPLOYMENT_PATH = os.path.abspath(
    os.path.join(THIS_DIR, "..", "deployment.json")
)

DEPLOYMENT_JSON_PATH = os.getenv("DEPLOYMENT_JSON", DEFAULT_DEPLOYMENT_PATH)

if not os.path.exists(DEPLOYMENT_JSON_PATH):
    raise RuntimeError(
        f"deployment.json not found at {DEPLOYMENT_JSON_PATH}. "
        f"Set DEPLOYMENT_JSON or place deployment.json at repo root."
    )

with open(DEPLOYMENT_JSON_PATH, "r") as f:
    deployment = json.load(f)

try:
    TASK_ADDRESS = Web3.to_checksum_address(
        deployment["taskContract"]["address"]
    )
    TASK_ABI = deployment["taskContract"]["abi"]
except KeyError as e:
    raise RuntimeError(
        f"deployment.json missing key {e}. "
        "Expected structure: taskContract.address + taskContract.abi"
    )

ZERO_ADDR = "0x0000000000000000000000000000000000000000"

# ============================================================
#  WEB3 / CONTRACT HELPERS
# ============================================================

_web3: Optional[Web3] = None
_contract = None


def get_web3() -> Web3:
    global _web3
    if _web3 is None:
        _web3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
    if not _web3.is_connected():
        raise RuntimeError(f"Cannot connect to Sepolia RPC at {SEPOLIA_RPC_URL}")
    return _web3


def get_contract():
    global _contract
    if _contract is None:
        w3 = get_web3()
        _contract = w3.eth.contract(address=TASK_ADDRESS, abi=TASK_ABI)
    return _contract


def get_task_count(contract) -> int:
    """
    New API: getTasksCount()
    Fallback: taskCounter() for compatibility.
    """
    # Prefer explicit getTasksCount()
    try:
        return int(contract.functions.getTasksCount().call())
    except Exception:
        pass

    # Fallback to taskCounter if present
    try:
        return int(contract.functions.taskCounter().call())
    except Exception as e:
        raise RuntimeError(
            f"Could not read getTasksCount() or taskCounter(): {e}"
        )


def _to_reward_display(value: Any):
    """
    Format reward into a human-friendly number.
    Assumes 'reward' behaves like a wei-style integer.
    """
    try:
        iv = int(value)
    except Exception:
        # Not an int: just return as-is
        return value

    # Web3 v6 style
    try:
        return float(Web3.from_wei(iv, "ether"))
    except Exception:
        pass

    # Web3 v5 style
    try:
        # type: ignore[attr-defined]
        return float(Web3.fromWei(iv, "ether"))
    except Exception:
        return iv


def task_tuple_to_dict(task: Any) -> Dict[str, Any]:
    """
    Normalize getTask(...) result to a stable JSON shape.

    Expected NEW layout:
        (id, title, description, reward, completed, worker, creator)

    Fallback OLD layout:
        (id, description, reward, completed, worker, creator)

    Returns:
        {
          "id": int,
          "title": str,
          "description": str,
          "rewardRaw": str,
          "rewardDisplay": float|str,
          "completed": bool,
          "worker": "0x...",
          "creator": "0x...",
          "status": "Available" | "InProgress" | "Completed"
        }
    """
    # Try the new full layout first
    try:
        task_id, title, description, reward, completed, worker, creator = task
    except ValueError:
        # Old shape fallback
        task_id = task[0] if len(task) > 0 else 0
        title = "(no title)"
        description = task[1] if len(task) > 1 else ""
        reward = task[2] if len(task) > 2 else 0
        completed = bool(task[3]) if len(task) > 3 else False
        worker = task[4] if len(task) > 4 else ZERO_ADDR
        creator = task[5] if len(task) > 5 else ZERO_ADDR

    task_id = int(task_id)
    completed = bool(completed)
    worker = str(worker)
    creator = str(creator)

    reward_raw = str(reward)
    reward_display = _to_reward_display(reward)

    has_worker = worker.lower() != ZERO_ADDR.lower()

    if completed:
        status = "Completed"
    elif has_worker:
        status = "InProgress"
    else:
        status = "Available"

    return {
        "id": task_id,
        "title": title,
        "description": description,
        "rewardRaw": reward_raw,
        "rewardDisplay": reward_display,
        "completed": completed,
        "worker": worker,
        "creator": creator,
        "status": status,
    }


def _iter_all_tasks() -> List[Dict[str, Any]]:
    """
    Fetch and normalize all tasks.
    Skips IDs that revert on getTask.
    """
    contract = get_contract()
    total = get_task_count(contract)
    if total == 0:
        return []

    tasks: List[Dict[str, Any]] = []
    for task_id in range(1, total + 1):
        try:
            raw = contract.functions.getTask(task_id).call()
        except Exception:
            # Skip missing/invalid task IDs
            continue
        tasks.append(task_tuple_to_dict(raw))
    return tasks


# ============================================================
#  MCP SERVER & TOOLS
# ============================================================

mcp = FastMCP("TaskChain")


@mcp.tool(
    name="list_tasks",
    description=(
        "List tasks from the SideQuests TaskContract on Sepolia. "
        "Uses getTasksCount() and getTask(id). "
        "Optionally limit how many tasks are returned."
    ),
)
def list_tasks(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get a basic overview of on-chain tasks.
    """
    all_tasks = _iter_all_tasks()
    if limit is not None:
        limit = max(0, int(limit))
        all_tasks = all_tasks[:limit]
    return all_tasks


@mcp.tool(
    name="get_task",
    description=(
        "Fetch a single task by its ID. "
        "Returns id, title, description, reward, status, worker, and creator."
    ),
)
def get_task(task_id: int) -> Dict[str, Any]:
    """
    Inspect one specific task by on-chain ID (1-based).
    """
    contract = get_contract()
    raw = contract.functions.getTask(int(task_id)).call()
    return task_tuple_to_dict(raw)


@mcp.tool(
    name="list_active_tasks",
    description=(
        "List tasks that are open for contributors: "
        "status 'Available' (no worker) or 'InProgress' (has worker, not completed)."
    ),
)
def list_active_tasks() -> List[Dict[str, Any]]:
    tasks = _iter_all_tasks()
    return [t for t in tasks if t["status"] in ("Available", "InProgress")]


@mcp.tool(
    name="list_completed_tasks",
    description=(
        "List tasks that have been completed on-chain "
        "(status 'Completed' according to getTask tuple)."
    ),
)
def list_completed_tasks() -> List[Dict[str, Any]]:
    tasks = _iter_all_tasks()
    return [t for t in tasks if t["status"] == "Completed"]


@mcp.tool(
    name="list_tasks_by_creator",
    description=(
        "List tasks created by a specific address. "
        "Useful for showing all quests posted by a given user/project."
    ),
)
def list_tasks_by_creator(creator_address: str) -> List[Dict[str, Any]]:
    addr = creator_address.lower()
    return [
        t for t in _iter_all_tasks()
        if t["creator"].lower() == addr
    ]


@mcp.tool(
    name="list_tasks_by_worker",
    description=(
        "List tasks where the given address is set as worker (assigned or completed). "
        "Use for contributor dashboards / profiles."
    ),
)
def list_tasks_by_worker(worker_address: str) -> List[Dict[str, Any]]:
    addr = worker_address.lower()
    return [
        t for t in _iter_all_tasks()
        if t["worker"].lower() == addr
    ]


@mcp.tool(
    name="search_tasks",
    description=(
        "Search tasks by keyword in title or description. "
        "Simple case-insensitive substring search."
    ),
)
def search_tasks(query: str, limit: int = 25) -> List[Dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return []

    results: List[Dict[str, Any]] = []
    for t in _iter_all_tasks():
        hay = f"{t.get('title','')} {t.get('description','')}".lower()
        if q in hay:
            results.append(t)
            if len(results) >= int(limit):
                break
    return results


@mcp.tool(
    name="get_task_stats",
    description=(
        "Get high-level stats for tasks on the current contract: "
        "total, available, in-progress, completed."
    ),
)
def get_task_stats() -> Dict[str, Any]:
    tasks = _iter_all_tasks()
    stats = {
        "total": len(tasks),
        "available": 0,
        "inProgress": 0,
        "completed": 0,
    }

    for t in tasks:
        if t["status"] == "Available":
            stats["available"] += 1
        elif t["status"] == "InProgress":
            stats["inProgress"] += 1
        elif t["status"] == "Completed":
            stats["completed"] += 1

    return stats


@mcp.tool(
    name="get_open_task_summaries",
    description=(
        "Return short natural-language summaries of open tasks "
        "(id, title, reward) for direct use in chat UIs / prompts."
    ),
)
def get_open_task_summaries(limit: int = 20) -> List[str]:
    summaries: List[str] = []
    for t in _iter_all_tasks():
        if t["status"] not in ("Available", "InProgress"):
            continue

        summaries.append(
            f"Task #{t['id']} [{t['status']}]: {t['title']} "
            f"- Reward: {t['rewardDisplay']} (raw {t['rewardRaw']})"
        )

        if len(summaries) >= int(limit):
            break

    return summaries


# ============================================================
#  ENTRYPOINT (STDIO MCP)
# ============================================================

def main():
    # This is launched by taskchain_server / AgentOS as an MCP toolkit over stdio.
    mcp.run()


if __name__ == "__main__":
    main()