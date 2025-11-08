#!/usr/bin/env python
import json
import os
from typing import Any, Dict, List, Optional

from web3 import Web3
from mcp.server.fastmcp import FastMCP

# ========================
#  CONFIG
# ========================

# Sepolia RPC (override in env if you have your own node)
SEPOLIA_RPC_URL = os.getenv(
    "SEPOLIA_RPC_URL",
    "https://ethereum-sepolia.publicnode.com",
)

# Task contract address (Sepolia)
CONTRACT_ADDRESS = Web3.to_checksum_address(
    "0xa564E0967A252E813051Cb278BF84fE567617D2E"
)

# Correct ABI (uint26 fixed to uint256; includes mapping `tasks` too)
CONTRACT_ABI_STRING = r"""
[
  {
    "inputs":[
      {"internalType":"address","name":"_rewardContractAddress","type":"address"}
    ],
    "stateMutability":"nonpayable",
    "type":"constructor"
  },
  {
    "anonymous":false,
    "inputs":[
      {"indexed":true,"internalType":"uint256","name":"id","type":"uint256"},
      {"indexed":true,"internalType":"address","name":"completer","type":"address"}
    ],
    "name":"TaskClaimed",
    "type":"event"
  },
  {
    "anonymous":false,
    "inputs":[
      {"indexed":true,"internalType":"uint256","name":"id","type":"uint256"},
      {"indexed":true,"internalType":"address","name":"completer","type":"address"}
    ],
    "name":"TaskCompleted",
    "type":"event"
  },
  {
    "anonymous":false,
    "inputs":[
      {"indexed":true,"internalType":"uint256","name":"id","type":"uint256"},
      {"indexed":true,"internalType":"address","name":"creator","type":"address"},
      {"indexed":false,"internalType":"string","name":"metadataURI","type":"string"}
    ],
    "name":"TaskCreated",
    "type":"event"
  },
  {
    "anonymous":false,
    "inputs":[
      {"indexed":true,"internalType":"uint256","name":"id","type":"uint256"},
      {"indexed":true,"internalType":"address","name":"verifier","type":"address"}
    ],
    "name":"TaskVerified",
    "type":"event"
  },
  {
    "inputs":[{"internalType":"uint256","name":"_taskId","type":"uint256"}],
    "name":"claimTask",
    "outputs":[],
    "stateMutability":"nonpayable",
    "type":"function"
  },
  {
    "inputs":[{"internalType":"uint256","name":"_taskId","type":"uint256"}],
    "name":"completeTask",
    "outputs":[],
    "stateMutability":"nonpayable",
    "type":"function"
  },
  {
    "inputs":[
      {"internalType":"string","name":"_metadataURI","type":"string"},
      {"internalType":"uint256[]","name":"_rewardIds","type":"uint256[]"},
      {"internalType":"uint256[]","name":"_rewardAmounts","type":"uint256[]"}
    ],
    "name":"createTask",
    "outputs":[],
    "stateMutability":"nonpayable",
    "type":"function"
  },
  {
    "inputs":[{"internalType":"uint256","name":"_taskId","type":"uint256"}],
    "name":"getTask",
    "outputs":[
      {
        "components":[
          {"internalType":"uint256","name":"id","type":"uint256"},
          {"internalType":"address","name":"creator","type":"address"},
          {"internalType":"address","name":"completer","type":"address"},
          {"internalType":"string","name":"metadataURI","type":"string"},
          {"internalType":"enum TaskContract.TaskStatus","name":"status","type":"uint8"},
          {"internalType":"uint256[]","name":"rewardIds","type":"uint256[]"},
          {"internalType":"uint256[]","name":"rewardAmounts","type":"uint256[]"}
        ],
        "internalType":"struct TaskContract.Task",
        "name":"",
        "type":"tuple"
      }
    ],
    "stateMutability":"view",
    "type":"function"
  },
  {
    "inputs":[],
    "name":"rewardContract",
    "outputs":[
      {"internalType":"contract IRewardContract","name":"","type":"address"}
    ],
    "stateMutability":"view",
    "type":"function"
  },
  {
    "inputs":[],
    "name":"taskCounter",
    "outputs":[
      {"internalType":"uint256","name":"","type":"uint256"}
    ],
    "stateMutability":"view",
    "type":"function"
  },
  {
    "inputs":[{"internalType":"uint256","name":"","type":"uint256"}],
    "name":"tasks",
    "outputs":[
      {"internalType":"uint256","name":"id","type":"uint256"},
      {"internalType":"address","name":"creator","type":"address"},
      {"internalType":"address","name":"completer","type":"address"},
      {"internalType":"string","name":"metadataURI","type":"string"},
      {"internalType":"enum TaskContract.TaskStatus","name":"status","type":"uint8"}
    ],
    "stateMutability":"view",
    "type":"function"
  },
  {
    "inputs":[{"internalType":"uint256","name":"_taskId","type":"uint256"}],
    "name":"verifyTask",
    "outputs":[],
    "stateMutability":"nonpayable",
    "type":"function"
  }
]
"""

CONTRACT_ABI = json.loads(CONTRACT_ABI_STRING)

# Enum labels must match TaskStatus in your Solidity
STATUS_LABELS = ["Created", "InProgress", "Completed", "Verified"]

# ========================
#  WEB3 HELPERS
# ========================

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
        _contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    return _contract


def task_tuple_to_dict(task_tuple: Any) -> Dict[str, Any]:
    """
    Convert getTask(...) tuple into a JSON-serializable dict.

    Layout:
      (id, creator, completer, metadataURI, status, rewardIds, rewardAmounts)
    """
    (
        task_id,
        creator,
        completer,
        metadata_uri,
        status_raw,
        reward_ids,
        reward_amounts,
    ) = task_tuple

    # Map status enum → label
    if 0 <= status_raw < len(STATUS_LABELS):
        status_label = STATUS_LABELS[status_raw]
    else:
        status_label = f"Unknown({status_raw})"

    rewards: List[Dict[str, Any]] = []
    for rid, amt in zip(reward_ids, reward_amounts):
        # NOTE: If these are ERC20 amounts, Ether-style from_wei is just display sugar.
        # Adjust decimals client-side if needed.
        amt_int = int(amt)
        rewards.append(
            {
                "rewardId": int(rid),
                "amountWei": str(amt_int),
                "amountEther": str(Web3.from_wei(amt_int, "ether")),
            }
        )

    return {
        "id": int(task_id),
        "creator": creator,
        "completer": completer,
        "metadataURI": metadata_uri,
        "status": status_label,
        "statusId": int(status_raw),
        "rewards": rewards,
    }


# ========================
#  MCP SERVER
# ========================

mcp = FastMCP("TaskChain")


@mcp.tool()
def list_tasks(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    List tasks from the on-chain TaskContract.

    Args:
        limit: Optional max number of tasks to return (from id=1 upwards).
               If omitted, returns all tasks.

    Returns:
        Array of task objects:
        {
          "id": int,
          "creator": "0x...",
          "completer": "0x...",
          "metadataURI": "ipfs://... or https://...",
          "status": "Created|InProgress|Completed|Verified",
          "statusId": int,
          "rewards": [
            {"rewardId": int, "amountWei": "str", "amountEther": "str"}
          ]
        }
    """
    contract = get_contract()
    total = contract.functions.taskCounter().call()

    if total == 0:
        return []

    max_id = total
    if limit is not None:
        max_id = max(1, min(total, limit))

    tasks: List[Dict[str, Any]] = []

    for task_id in range(1, max_id + 1):
        try:
            raw = contract.functions.getTask(task_id).call()
        except Exception:
            # If some IDs are invalid/unused, just skip.
            continue
        task = task_tuple_to_dict(raw)
        tasks.append(task)

    return tasks


@mcp.tool()
def get_task(task_id: int) -> Dict[str, Any]:
    """
    Get a single task by ID.
    """
    contract = get_contract()
    raw = contract.functions.getTask(task_id).call()
    return task_tuple_to_dict(raw)


@mcp.tool()
def list_active_tasks() -> List[Dict[str, Any]]:
    """
    List tasks that are in an "open" state.

    Currently:
      - Includes status Created, InProgress.
      - Excludes Completed, Verified.

    Adjust this filter to match your business logic.
    """
    contract = get_contract()
    total = contract.functions.taskCounter().call()

    if total == 0:
        return []

    active: List[Dict[str, Any]] = []

    for task_id in range(1, total + 1):
        try:
            raw = contract.functions.getTask(task_id).call()
        except Exception:
            continue

        task = task_tuple_to_dict(raw)
        if task["status"] in ("Created", "InProgress"):
            active.append(task)

    return active


# ========= FUTURE: EMBEDDINGS / VECTOR SEARCH HOOKS =========
#
# Once you:
#   - store text-embedding-3-small outputs on-chain, OR
#   - store them in IPFS / vector DB keyed by taskId,
# you can add tools like:
#
# @mcp.tool()
# def get_task_embedding(task_id: int) -> Dict[str, Any]:
#     """Return embedding vector for a given task (if available)."""
#     ...
#
# @mcp.tool()
# def semantic_search_tasks(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
#     """
#     Embed the query with Azure OpenAI, run similarity search over task embeddings,
#     and return best-matching tasks.
#     """
#     ...
#
# The MCP client (ChatGPT / Claude / your agent) can then call those directly
# for RAG-style matching.

# ========================
#  ENTRYPOINT
# ========================

def main():
    # Default: stdio transport (for MCP-compatible clients)
    mcp.run()


if __name__ == "__main__":
    main()