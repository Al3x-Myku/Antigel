#!/usr/bin/env python3
"""
Test script for SideQuests Task Contract
Lists all tasks from the blockchain
"""

import json
from web3 import Web3

# Load deployment configuration
with open('deployment.json', 'r') as f:
    deployment = json.load(f)

# Contract addresses and ABIs from deployment
TASK_ADDRESS = deployment['taskContract']['address']
TASK_ABI = deployment['taskContract']['abi']

# Connect to Sepolia
SEPOLIA_RPC_URL = "https://sepolia.infura.io/v3/713dcbe5e2254d718e5040c2ae716c3f"
web3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))

if not web3.is_connected():
    print("❌ Error: Could not connect to Sepolia.")
    exit()

print(f"✅ Connected to Sepolia (Block: {web3.eth.block_number})")
print(f"📝 Task Contract: {TASK_ADDRESS}\n")

def format_task(task):
    """Format task data for display.

    Expected task tuple from getTask: (id, title, description, reward, completed, worker, creator)
    """
    try:
        task_id, title, description, reward, completed, worker, creator = task
    except ValueError:
        # Fallback to old ordering if ABI mismatch
        # old: (id, description, reward, completed, worker, creator)
        task_id = task[0]
        title = "(no title)"
        description = task[1] if len(task) > 1 else ""
        reward = task[2] if len(task) > 2 else 0
        completed = task[3] if len(task) > 3 else False
        worker = task[4] if len(task) > 4 else "0x0000000000000000000000000000000000000000"
        creator = task[5] if len(task) > 5 else "0x0000000000000000000000000000000000000000"

    # Format reward (reward is in wei-like smallest unit of token; show as human-friendly value)
    try:
        reward_display = Web3.fromWei(int(reward), 'ether')
    except Exception:
        # If reward is already numeric or convertible
        try:
            reward_display = float(reward)
        except Exception:
            reward_display = reward

    # Status
    if completed:
        status = "✅ Completed"
        status_color = "🟢"
    elif worker and worker != "0x0000000000000000000000000000000000000000":
        status = "🔨 In Progress"
        status_color = "🟡"
    else:
        status = "📝 Available"
        status_color = "🔵"

    # Format addresses
    creator_short = f"{creator[:6]}...{creator[-4:]}"
    worker_short = f"{worker[:6]}...{worker[-4:]}" if worker and worker != "0x0000000000000000000000000000000000000000" else "Not assigned"

    return f"""
{'='*70}
{status_color} TASK #{task_id}: {status}
Title: {title}
{'='*70}
Description: {description}
Reward:      {reward_display} HLP tokens
Creator:     {creator_short}
Worker:      {worker_short}
{'='*70}
"""

def get_all_tasks():
    """Fetch and display all tasks from the contract"""
    try:
        contract = web3.eth.contract(address=TASK_ADDRESS, abi=TASK_ABI)
        
        # Get total number of tasks
        task_count = contract.functions.getTasksCount().call()
        
        if task_count == 0:
            print("📭 No tasks found in the contract.")
            print("\n💡 To create a task:")
            print("   1. Connect wallet to the app")
            print("   2. Fill in task description and reward amount")
            print("   3. Click 'Create Task'")
            return
        
        print(f"📦 Total tasks: {task_count}\n")
        
        # Fetch and display each task
        for i in range(1, task_count + 1):
            print(f"Fetching task #{i}...")
            task = contract.functions.getTask(i).call()
            print(format_task(task))
        
        print(f"\n✅ Successfully retrieved {task_count} task(s)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if "execution reverted" in str(e):
            print("💡 Tip: Make sure the contract address and ABI are correct")

# Run the script
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                   SideQuests Task List Viewer                        ║
║                                                                      ║
║  This script fetches and displays all tasks from the Task Contract  ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    get_all_tasks()
