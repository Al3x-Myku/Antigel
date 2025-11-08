import solcx
import json
import os
import time
from solcx import compile_standard, install_solc
from web3 import Web3
from dotenv import load_dotenv

def compile_contracts():
    """
    Installs solc 0.8.20 and compiles both contracts,
    handling OpenZeppelin imports.
    """
    
    # 1. Install and set the correct Solidity compiler version
    print("Installing Solc 0.8.20...")
    try:
        install_solc('0.8.20')
        solcx.set_solc_version('0.8.20')
    except Exception as e:
        print(f"Error installing or setting solc: {e}")
        return None, None, None, None

    # 2. Define the compiler input structure
    print("Reading contract source files...")
    try:
        with open("contracts/RewardContract.sol", "r") as f:
            reward_source = f.read()
        with open("contracts/TaskContract.sol", "r") as f:
            task_source = f.read()
    except FileNotFoundError as e:
        print(f"Error: {e}. Make sure contracts are in a 'contracts/' directory.")
        return None, None, None, None

    input_json = {
        "language": "Solidity",
        "sources": {
            "RewardContract.sol": {"content": reward_source},
            "TaskContract.sol": {"content": task_source},
        },
        "settings": {
            # Define import remappings for OpenZeppelin
            "remappings": [
                "@openzeppelin/=" + os.path.abspath("node_modules/@openzeppelin/")
            ],
            # Define output selection
            "outputSelection": {
                "*": {
                    "*": ["abi", "evm.bytecode.object"]
                }
            },
        },
    }

    # 3. Compile the contracts
    print("Compiling contracts...")
    try:
        compiled_sol = compile_standard(
            input_json,
            allow_paths=[
                "contracts/",
                "node_modules/"
            ]
        )
    except Exception as e:
        print(f"Compilation Failed: {e}")
        return None, None, None, None
    
    # 4. Extract ABI and Bytecode for each contract
    try:
        rc_data = compiled_sol["contracts"]["RewardContract.sol"]["RewardContract"]
        rc_abi = rc_data["abi"]
        rc_bytecode = rc_data["evm"]["bytecode"]["object"]
        
        tc_data = compiled_sol["contracts"]["TaskContract.sol"]["TaskContract"]
        tc_abi = tc_data["abi"]
        tc_bytecode = tc_data["evm"]["bytecode"]["object"]
    except KeyError as e:
        print(f"Error extracting ABI/Bytecode. Compilation output may be incomplete: {e}")
        return None, None, None, None
    
    print("Compilation successful.")
    return rc_abi, rc_bytecode, tc_abi, tc_bytecode

def send_tx(w3, tx, deployer_acct, description):
    """
    Signs and sends a transaction, waits for the receipt,
    and handles errors.
    """
    try:
        # Estimate gas
        tx['gas'] = w3.eth.estimate_gas(tx)
        
        # Sign the transaction
        signed_txn = w3.eth.account.sign_transaction(tx, private_key=deployer_acct.key)
        
        # Send the transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print(f"  Sending {description} (Tx: {tx_hash.hex()})...")
        
        # Wait for the transaction receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        if receipt.status == 0:
            print(f"  !! {description} FAILED. Transaction reverted. !!")
            return None
            
        print(f"  ... {description} successful.")
        return receipt
        
    except Exception as e:
        print(f"  !! Error during {description}: {e} !!")
        return None

def deploy_contracts(w3, deployer_acct, rc_abi, rc_bytecode, tc_abi, tc_bytecode):
    """
    Deploys both contracts in a two-stage process.
    """
    
    print(f"\nDeploying from account: {deployer_acct.address}")
    
    # --- STAGE 1: Deploy RewardContract ---
    print("Deploying RewardContract...")
    RewardContract = w3.eth.contract(abi=rc_abi, bytecode=rc_bytecode)
    
    construct_txn = RewardContract.constructor(deployer_acct.address).build_transaction({
        "from": deployer_acct.address,
        "nonce": w3.eth.get_transaction_count(deployer_acct.address),
        "gasPrice": w3.eth.gas_price
    })
    
    rc_receipt = send_tx(w3, construct_txn, deployer_acct, "RewardContract Deployment")
    if rc_receipt is None:
        return None, None
        
    reward_address = rc_receipt.contractAddress
    print(f"  RewardContract deployed at: {reward_address}")

    # --- STAGE 2: Deploy TaskContract ---
    # Wait a moment for the nonce to be correct
    time.sleep(5) 
    
    print("\nDeploying TaskContract...")
    TaskContract = w3.eth.contract(abi=tc_abi, bytecode=tc_bytecode)
    
    construct_txn = TaskContract.constructor(reward_address).build_transaction({
        "from": deployer_acct.address,
        "nonce": w3.eth.get_transaction_count(deployer_acct.address),
        "gasPrice": w3.eth.gas_price
    })
    
    tc_receipt = send_tx(w3, construct_txn, deployer_acct, "TaskContract Deployment")
    if tc_receipt is None:
        return reward_address, None

    task_address = tc_receipt.contractAddress
    print(f"  TaskContract deployed at: {task_address}")
    
    return reward_address, task_address

def configure_permissions(w3, deployer_acct, rc_abi, reward_address, task_address):
    """
    Grants the MINTER_ROLE from RewardContract to TaskContract.
    """
    
    print("\nConfiguring contract permissions...")
    
    # 1. Get an instance of the deployed RewardContract
    rc_instance = w3.eth.contract(address=reward_address, abi=rc_abi)

    # 2. Get the MINTER_ROLE identifier (a bytes32 value)
    try:
        MINTER_ROLE = rc_instance.functions.MINTER_ROLE().call()
        print(f"  MINTER_ROLE hash: {MINTER_ROLE.hex()}")
    except Exception as e:
        print(f"  Error calling MINTER_ROLE(): {e}")
        return False

    # 3. Grant the MINTER_ROLE to the TaskContract's address
    try:
        # Wait a moment for the nonce to be correct
        time.sleep(5) 

        grant_txn = rc_instance.functions.grantRole(MINTER_ROLE, task_address).build_transaction({
            "from": deployer_acct.address,
            "nonce": w3.eth.get_transaction_count(deployer_acct.address),
            "gasPrice": w3.eth.gas_price
        })
        
        receipt = send_tx(w3, grant_txn, deployer_acct, "Grant MINTER_ROLE")
        if receipt is None:
            return False
            
    except Exception as e:
        print(f"  Error building grantRole transaction: {e}")
        return False

    print("  Permissions configured successfully.")
    return True

def generate_artifacts_file(rc_abi, reward_address, tc_abi, task_address):
    """
    Generates the JSON artifact file - the formal "hand-off"
    to the Go backend.
    """
    
    print("\nGenerating deployment_artifacts.json...")
    
    artifacts = {
        "RewardContract": {
            "address": reward_address,
            "abi": rc_abi
        },
        "TaskContract": {
            "address": task_address,
            "abi": tc_abi
        }
    }
    
    try:
        with open("deployment_artifacts.json", "w") as f:
            json.dump(artifacts, f, indent=2)
        print("Artifact file generated.")
    except Exception as e:
        print(f"Error writing artifact file: {e}")

# --- Main execution script ---
if __name__ == "__main__":
    load_dotenv()
    
    # 1. Connect to the EVM node
    INFURA_URL = os.getenv("SEPOLIA_URL")
    PRIVATE_KEY = os.getenv("SEPOLIA_PRIVATE_KEY")
    
    if not INFURA_URL or not PRIVATE_KEY:
        print("Error: INFURA_URL and PRIVATE_KEY must be set in .env file")
        exit(1)
    if not PRIVATE_KEY.startswith("0x"):
        print("Error: PRIVATE_KEY in .env file must start with 0x")
        exit(1)

    try:
        w3 = Web3(Web3.HTTPProvider(INFURA_URL))
        if not w3.is_connected():
            print(f"Error: Failed to connect to Web3 provider at {INFURA_URL}")
            exit(1)
    except Exception as e:
        print(f"Error connecting to Web3: {e}")
        exit(1)

    print(f"Successfully connected to {INFURA_URL}")
    deployer_acct = w3.eth.account.from_key(PRIVATE_KEY)

    # 2. Compile
    (rc_abi, rc_bytecode, tc_abi, tc_bytecode) = compile_contracts()
    if rc_abi is None:
        exit(1)
    
    # 3. Deploy
    (reward_address, task_address) = deploy_contracts(
        w3, deployer_acct, rc_abi, rc_bytecode, tc_abi, tc_bytecode
    )
    if reward_address is None or task_address is None:
        print("Deployment failed. Exiting.")
        exit(1)
    
    # 4. Configure
    success = configure_permissions(w3, deployer_acct, rc_abi, reward_address, task_address)
    if not success:
        print("Permission configuration failed. Exiting.")
        exit(1)
    
    # 5. Generate Artifacts
    generate_artifacts_file(rc_abi, reward_address, tc_abi, task_address)
    
    print("\n--- DEPLOYMENT COMPLETE ---")
    print(f"RewardContract: {reward_address}")
    print(f"TaskContract:   {task_address}")
    print("Artifact file: deployment_artifacts.json")
