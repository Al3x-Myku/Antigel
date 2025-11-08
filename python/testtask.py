import json
from web3 import Web3

# 1. INFORMAȚIILE CONTRACTULUI
CONTRACT_ADDRESS = "0xa564E0967A252E813051Cb278BF84fE567617D2E"

# ABI-ul contractului (interfața) - acum formatat corect ca un string pe mai multe linii
CONTRACT_ABI_STRING = """
[{"inputs":[{"internalType":"address","name":"_rewardContractAddress","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"id","type":"uint256"},{"indexed":true,"internalType":"address","name":"completer","type":"address"}],"name":"TaskClaimed","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"id","type":"uint256"},{"indexed":true,"internalType":"address","name":"completer","type":"address"}],"name":"TaskCompleted","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"id","type":"uint256"},{"indexed":true,"internalType":"address","name":"creator","type":"address"},{"indexed":false,"internalType":"string","name":"metadataURI","type":"string"}],"name":"TaskCreated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"id","type":"uint256"},{"indexed":true,"internalType":"address","name":"verifier","type":"address"}],"name":"TaskVerified","type":"event"},{"inputs":[{"internalType":"uint256","name":"_taskId","type":"uint256"}],"name":"claimTask","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_taskId","type":"uint256"}],"name":"completeTask","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"string","name":"_metadataURI","type":"string"},{"internalType":"uint256[]","name":"_rewardIds","type":"uint256[]"},{"internalType":"uint256[]","name":"_rewardAmounts","type":"uint256[]"}],"name":"createTask","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_taskId","type":"uint256"}],"name":"getTask","outputs":[{"components":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"address","name":"creator","type":"address"},{"internalType":"address","name":"completer","type":"address"},{"internalType":"string","name":"metadataURI","type":"string"},{"internalType":"enum TaskContract.TaskStatus","name":"status","type":"uint8"},{"internalType":"uint256[]","name":"rewardIds","type":"uint256[]"},{"internalType":"uint256[]","name":"rewardAmounts","type":"uint256[]"}],"internalType":"struct TaskContract.Task","name":"","type":"tuple"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"rewardContract","outputs":[{"internalType":"contract IRewardContract","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"taskCounter","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"tasks","outputs":[{"internalType":"uint256","name":"id","type":"uint26"},{"internalType":"address","name":"creator","type":"address"},{"internalType":"address","name":"completer","type":"address"},{"internalType":"string","name":"metadataURI","type":"string"},{"internalType":"enum TaskContract.TaskStatus","name":"status","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_taskId","type":"uint256"}],"name":"verifyTask","outputs":[],"stateMutability":"nonpayable","type":"function"}]
"""

# Încărcăm string-ul ABI într-o listă Python folosind 'json.loads'
CONTRACT_ABI = json.loads(CONTRACT_ABI_STRING)


# 2. CONECTARE LA SEPOLIA
# Folosim un nod RPC public pentru Sepolia
SEPOLIA_RPC_URL = "https://ethereum-sepolia.publicnode.com"
web3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))

if not web3.is_connected():
    print("Eroare: Nu s-a putut conecta la nodul Sepolia.")
    exit()

print(f"Conectat la Sepolia (Block: {web3.eth.block_number})\n")

# Maparea statusului (ca în JS)
STATUS_LABELS = ['Created', 'InProgress', 'Completed', 'Verified']

def format_task(task_data):
    """Formatează datele brute ale task-ului pentru afișare."""
    (id, creator, completer, metadata, status_id, reward_ids, reward_amounts) = task_data
    
    # Formatează recompensele
    rewards_str = []
    for i in range(len(reward_ids)):
        # Converteste suma din Wei în Ether (la fel ca ethers.utils.formatEther)
        amount_ether = Web3.from_wei(reward_amounts[i], 'ether')
        rewards_str.append(f"ID {reward_ids[i]}: {amount_ether} tokens")

    return f"""
----------------------------------------
TASK #{id}
  Status:     {STATUS_LABELS[status_id]}
  URI:        {metadata}
  Creator:    {creator}
  Completer:  {completer}
  Rewards:    {', '.join(rewards_str)}
----------------------------------------
"""

def get_all_tasks():
    """Preia toate task-urile din contract."""
    try:
        # 3. INIȚIALIZEAZĂ CONTRACTUL
        contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

        # 4. PASUL 1: Află numărul total de task-uri
        task_count = contract.functions.taskCounter().call()

        if task_count == 0:
            print("Nu a fost găsit niciun task în contract.")
            return

        print(f"Total task-uri de preluat: {task_count}\n")
        
        all_tasks = []

        # 5. PASUL 2: Iterează și preia fiecare task
        # Reține: taskCounter-ul pornește de la 1
        for i in range(1, task_count + 1):
            print(f"Se preia task-ul #{i}...")
            # Apeleză funcția 'getTask(uint256)'
            task_data = contract.functions.getTask(i).call()
            all_tasks.append(task_data)
            
            # Afișează task-ul formatat
            print(format_task(task_data))

        print("\nToate task-urile au fost preluate cu succes.")
        return all_tasks

    except Exception as e:
        print(f"A apărut o eroare: {e}")
        if "BadFunctionCallOutput" in str(e):
            print("Sfat: Verifică dacă adresa contractului și ABI-ul sunt corecte.")

# --- Rulează scriptul ---
if __name__ == "__main__":
    get_all_tasks()
