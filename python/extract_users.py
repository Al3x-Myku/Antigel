import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import shutil
from datetime import datetime

# === CONFIG ===
SERVICE_ACCOUNT_FILE = "serviceAccountKey.json"  # Path to your Firebase Admin SDK key
PROJECT_ID = "taskmatch-openhack2025"
COLLECTION_NAME = "users"        # Firestore collection name
OUTPUT_DIR = "graphrag/input"    # Output directory (GraphRAG input folder)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "users.txt")

# === CLEAN OUTPUT DIRECTORY ===
if os.path.exists(OUTPUT_DIR):
    print(f"🧹 Cleaning old output directory: {OUTPUT_DIR}")
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR)
print(f"📁 Created fresh directory: {OUTPUT_DIR}\n")

# === INITIALIZE FIREBASE ===
cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
firebase_admin.initialize_app(cred, {"projectId": PROJECT_ID})
db = firestore.client()

# === HELPER: Convert Firestore data to JSON-serializable ===
def clean_firestore_data(data):
    """Recursively converts Firestore types (like timestamps) into JSON-safe values."""
    if isinstance(data, dict):
        return {k: clean_firestore_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_firestore_data(v) for v in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    elif hasattr(data, "isoformat"):  # covers Firestore DatetimeWithNanoseconds
        try:
            return data.isoformat()
        except Exception:
            return str(data)
    elif isinstance(data, firestore.DocumentReference):
        return data.path
    else:
        return data

# === FUNCTIONS ===
def get_all_users():
    """Fetch all documents from the Firestore 'users' collection."""
    users_ref = db.collection(COLLECTION_NAME)
    docs = users_ref.stream()
    users = []
    for doc in docs:
        user_data = doc.to_dict()
        user_data["id"] = doc.id
        user_data = clean_firestore_data(user_data)
        users.append(user_data)
    return users

def save_all_users(users):
    """Save all users into one combined text file."""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for i, user in enumerate(users, start=1):
            json.dump(user, f, indent=2, ensure_ascii=False)
            f.write("\n\n")  # blank line between users
    print(f"✅ Saved {len(users)} users into {OUTPUT_FILE}")

# === MAIN ===
if __name__ == "__main__":
    print(f"🔄 Fetching users from Firestore collection '{COLLECTION_NAME}'...")
    users = get_all_users()
    print(f"✅ Retrieved {len(users)} users.\n")
    save_all_users(users)