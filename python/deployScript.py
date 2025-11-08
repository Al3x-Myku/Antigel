import json
import os
from web3 import Web3
from solcx import compile_standard, install_solc
from pathlib import Path

# Configuration
INFURA_URL = "https://sepolia.infura.io/v3/713dcbe5e2254d718e5040c2ae716c3f"
SOLC_VERSION = "0.8.20"

# Get the base directory
BASE_DIR = Path(__file__).parent.resolve()
CONTRACTS_DIR = BASE_DIR / "contracts"
NODE_MODULES_DIR = BASE_DIR / "node_modules"

def check_dependencies():
    """Check if OpenZeppelin contracts are installed"""
    oz_path = NODE_MODULES_DIR / "@openzeppelin" / "contracts"
    if not oz_path.exists():
        print("Error: OpenZeppelin contracts not found!")
        print(f"Expected path: {oz_path}")
        print("Please run: npm install @openzeppelin/contracts")
        return False
    print("Dependencies found.")
    return True

def read_contract_file(filename):
    """Read a contract source file"""
    filepath = CONTRACTS_DIR / filename
    with open(filepath, 'r') as f:
        return f.read()

def compile_contracts():
    """Compile the smart contracts with proper import resolution"""
    print(f"Installing Solc {SOLC_VERSION}...")
    install_solc(SOLC_VERSION)
    
    print("Reading contract source files...")
    reward_contract_source = read_contract_file("RewardContract.sol")
    task_contract_source = read_contract_file("TaskContract.sol")
    
    print("Compiling contracts...")
    
    # Prepare the compilation input with proper settings
    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {
                "RewardContract.sol": {"content": reward_contract_source},
                "TaskContract.sol": {"content": task_contract_source}
            },
            "settings": {
                # This is the key part - remapping @openzeppelin to the actual path
                "remappings": [
                    f"@openzeppelin/={NODE_MODULES_DIR}/@openzeppelin/"
                ],
                "optimizer": {
                    "enabled": True,
                    "runs": 200
                },
                "outputSelection": {
                    "*": {
                        "*": [
                            "abi",
                            "metadata",
                            "evm.bytecode",
                            "evm.bytecode.sourceMap",
                            "evm.deployedBytecode",
                            "evm.deployedBytecode.sourceMap"
                        ]
                    }
                }
            }
        },
        solc_version=SOLC_VERSION,
        allow_paths=str(BASE_DIR)
    )
    
    return compiled_sol

def deploy_contracts(w3, private_key, compiled_sol):
    """Deploy the contracts to the network"""
    account = w3.eth.account.from_key(private_key)
    
    print(f"\nDeploying from account: {account.address}")
    print(f"Account balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")
    
    # Extract contract data
    reward_contract = compiled_sol['contracts']['RewardContract.sol']['RewardContract']
    task_contract = compiled_sol['contracts']['TaskContract.sol']['TaskContract']
    
    reward_bytecode = reward_contract['evm']['bytecode']['object']
    reward_abi = reward_contract['abi']
    
    task_bytecode = task_contract['evm']['bytecode']['object']
    task_abi = task_contract['abi']
    
    # Deploy RewardContract
    print("\n=== Deploying RewardContract ===")
    RewardContract = w3.eth.contract(abi=reward_abi, bytecode=reward_bytecode)
    
    # Build transaction for RewardContract (admin = deployer address)
    reward_tx = RewardContract.constructor(account.address).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 3000000,
        'gasPrice': w3.eth.gas_price
    })
    
    # Sign and send
    signed_reward_tx = w3.eth.account.sign_transaction(reward_tx, private_key)
    reward_tx_hash = w3.eth.send_raw_transaction(signed_reward_tx.raw_transaction)
    print(f"RewardContract deployment tx: {reward_tx_hash.hex()}")
    
    # Wait for confirmation
    reward_tx_receipt = w3.eth.wait_for_transaction_receipt(reward_tx_hash)
    reward_contract_address = reward_tx_receipt.contractAddress
    print(f"RewardContract deployed at: {reward_contract_address}")
    
    # Deploy TaskContract
    print("\n=== Deploying TaskContract ===")
    TaskContract = w3.eth.contract(abi=task_abi, bytecode=task_bytecode)
    
    # Build transaction for TaskContract (pass RewardContract address)
    task_tx = TaskContract.constructor(reward_contract_address).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price
    })
    
    # Sign and send
    signed_task_tx = w3.eth.account.sign_transaction(task_tx, private_key)
    task_tx_hash = w3.eth.send_raw_transaction(signed_task_tx.raw_transaction)
    print(f"TaskContract deployment tx: {task_tx_hash.hex()}")
    
    # Wait for confirmation
    task_tx_receipt = w3.eth.wait_for_transaction_receipt(task_tx_hash)
    task_contract_address = task_tx_receipt.contractAddress
    print(f"TaskContract deployed at: {task_contract_address}")
    
    # Grant MINTER_ROLE to TaskContract
    print("\n=== Granting MINTER_ROLE to TaskContract ===")
    reward_contract_instance = w3.eth.contract(
        address=reward_contract_address,
        abi=reward_abi
    )
    
    # Calculate MINTER_ROLE hash
    minter_role = w3.keccak(text="MINTER_ROLE")
    
    grant_role_tx = reward_contract_instance.functions.grantRole(
        minter_role,
        task_contract_address
    ).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 100000,
        'gasPrice': w3.eth.gas_price
    })
    
    signed_grant_tx = w3.eth.account.sign_transaction(grant_role_tx, private_key)
    grant_tx_hash = w3.eth.send_raw_transaction(signed_grant_tx.raw_transaction)
    print(f"GrantRole tx: {grant_tx_hash.hex()}")
    
    grant_tx_receipt = w3.eth.wait_for_transaction_receipt(grant_tx_hash)
    print("MINTER_ROLE granted successfully!")
    
    # Save deployment info
    deployment_info = {
        "network": "sepolia",
        "rewardContract": {
            "address": reward_contract_address,
            "abi": reward_abi
        },
        "taskContract": {
            "address": task_contract_address,
            "abi": task_abi
        }
    }
    
    with open('deployment.json', 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print("\n=== Deployment Summary ===")
    print(f"RewardContract: {reward_contract_address}")
    print(f"TaskContract: {task_contract_address}")
    print("Deployment info saved to deployment.json")
    
    return deployment_info

def main():
    print("Checking for OpenZeppelin dependencies...")
    if not check_dependencies():
        return
    
    print(f"Successfully connected to {INFURA_URL}")
    
    try:
        # Compile contracts
        compiled_sol = compile_contracts()
        print("Compilation successful!")
        
        # Connect to Web3
        w3 = Web3(Web3.HTTPProvider(INFURA_URL))
        
        if not w3.is_connected():
            print("Error: Could not connect to Ethereum network")
            return
        
        # Get private key from environment or prompt
        private_key = os.getenv('PRIVATE_KEY')
        if not private_key:
            private_key = input("Enter your private key (without 0x prefix): ")
            if not private_key.startswith('0x'):
                private_key = '0x' + private_key
        
        # Deploy contracts
        deploy_contracts(w3, private_key, compiled_sol)
        
    except Exception as e:
        print(f"Compilation Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
