import json
from web3 import Web3
import os

# Load deployment info
with open('deployment.json', 'r') as f:
    deployment = json.load(f)

# Connect to Web3
INFURA_URL = "https://sepolia.infura.io/v3/713dcbe5e2254d718e5040c2ae716c3f"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

# Get private key
private_key = os.getenv('PRIVATE_KEY')
if not private_key:
    private_key = input("Enter your private key: ")
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key

account = w3.eth.account.from_key(private_key)

# Create contract instances
reward_contract = w3.eth.contract(
    address=deployment['rewardContract']['address'],
    abi=deployment['rewardContract']['abi']
)

task_contract = w3.eth.contract(
    address=deployment['taskContract']['address'],
    abi=deployment['taskContract']['abi']
)

print("\n" + "="*60)
print("🧪 TESTING DEPLOYED CONTRACTS")
print("="*60 + "\n")

print(f"Account: {account.address}")
print(f"Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH\n")

# Test 1: Check if TaskContract has MINTER_ROLE
print("Test 1: Checking MINTER_ROLE...")
minter_role = w3.keccak(text="MINTER_ROLE")
has_role = reward_contract.functions.hasRole(minter_role, deployment['taskContract']['address']).call()
print(f"   TaskContract has MINTER_ROLE: {'✅ Yes' if has_role else '❌ No'}\n")

# Test 2: Create a task
print("Test 2: Creating a test task...")
try:
    create_tx = task_contract.functions.createTask(
        "ipfs://QmTest123",  # metadata URI
        [0],  # reward IDs (0 = COMMUNITY_TOKE)
        [100 * 10**18]  # reward amounts (100 tokens)
    ).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price
    })
    
    signed_tx = w3.eth.account.sign_transaction(create_tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"   TX: {tx_hash.hex()}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"   ✅ Task created! Gas used: {receipt.gasUsed}\n")
    
    # Get task counter
    task_count = task_contract.functions.taskCounter().call()
    print(f"   Total tasks created: {task_count}")
    
    # Get the task details
    task = task_contract.functions.getTask(task_count).call()
    print(f"   Task ID: {task[0]}")
    print(f"   Creator: {task[1]}")
    print(f"   Status: {['Created', 'InProgress', 'Completed', 'Verified'][task[4]]}")
    print(f"   Metadata: {task[3]}")
    print(f"   Reward IDs: {task[5]}")
    print(f"   Reward Amounts: {task[6]}\n")
    
except Exception as e:
    print(f"   ❌ Error: {e}\n")

# Test 3: Check contract paused status
print("Test 3: Checking contract status...")
is_paused = reward_contract.functions.paused().call()
print(f"   RewardContract paused: {'⏸️  Yes' if is_paused else '✅ No'}\n")

# Test 4: Check roles
print("Test 4: Checking roles...")
admin_role = reward_contract.functions.DEFAULT_ADMIN_ROLE().call()
pauser_role = w3.keccak(text="PAUSER_ROLE")

has_admin = reward_contract.functions.hasRole(admin_role, account.address).call()
has_pauser = reward_contract.functions.hasRole(pauser_role, account.address).call()

print(f"   Your address has ADMIN_ROLE: {'✅ Yes' if has_admin else '❌ No'}")
print(f"   Your address has PAUSER_ROLE: {'✅ Yes' if has_pauser else '❌ No'}\n")

print("="*60)
print("🎉 TESTING COMPLETE")
print("="*60)
print("\n📝 Contract Addresses:")
print(f"   RewardContract: {deployment['rewardContract']['address']}")
print(f"   TaskContract:   {deployment['taskContract']['address']}")
print(f"\n🔗 View on Etherscan:")
print(f"   https://sepolia.etherscan.io/address/{deployment['rewardContract']['address']}")
print(f"   https://sepolia.etherscan.io/address/{deployment['taskContract']['address']}")
print()
