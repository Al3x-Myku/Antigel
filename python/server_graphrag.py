from flask import Flask, request, jsonify
import subprocess
import json
import re

import firebase_admin
from firebase_admin import firestore, credentials

app = Flask(__name__)

# ---------- Firebase Admin Init ----------
# Uses GOOGLE_APPLICATION_CREDENTIALS or default creds.
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")  # <-- path to your file
    firebase_admin.initialize_app(cred)
db = firestore.client()


# ---------- CORS ----------
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    # In dev you can be permissive; tighten this in prod.
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"

    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Max-Age"] = "600"
    return response


@app.route("/task", methods=["OPTIONS"])
def task_preflight():
    return ("", 204)


# ---------- Helpers ----------

def extract_json_from_output(text: str):
    """
    Try to pull a JSON object out of Graphrag-style output.
    Handles:
    - ```json { ... } ```
    - plain `{ ... }`
    Returns dict or None.
    """
    if not text:
        return None

    # 1) ```json ... ``` fenced block
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 2) First { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 3) Direct full JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    return None


def upsert_ptask_from_user(user: dict):
    """
    Takes the parsed JSON user object and upserts into 'ptask/{uid}'.
    """
    if not isinstance(user, dict):
        return

    uid = user.get("uid")
    if not uid:
        return

    doc_ref = db.collection("ptask").document(uid)

    payload = {
        "uid": uid,
        "displayName": user.get("displayName"),
        "walletAddress": user.get("walletAddress"),
        "skills": user.get("skills"),
        "hlpBalance": user.get("hlpBalance", 0),
        "tasksCompleted": user.get("tasksCompleted", 0),
        "tasksInProgress": user.get("tasksInProgress", 0),
        "reputation": user.get("reputation", 0),
        "rating": user.get("rating", 0),
        "ratingCount": user.get("ratingCount", 0),
        "photoURL": user.get("photoURL"),
        "joinedCommunities": user.get("joinedCommunities", []),
        "badges": user.get("badges", []),
        "preferences": user.get("preferences", {}),
        "bio": user.get("bio"),
        "phoneNumber": user.get("phoneNumber"),
        "createdAt": user.get("createdAt"),
        "lastLoginAt": user.get("lastLoginAt"),
        # Optional: store full object for debugging / future use
        "raw": user,
    }

    doc_ref.set(payload, merge=True)


# ---------- Main Endpoint ----------

@app.route('/task', methods=['POST'])
def handle_task():
    try:
        data = request.get_json(force=True)

        # Expecting a "description" that we send into Graphrag.
        description = data.get("description")
        if not description:
            return jsonify({"error": "Missing 'description' field"}), 400

        # Build Graphrag query from the description
        query = f"Can you recommend someone for {description}. Just the whole json no other text"

        cmd = [
            "graphrag",
            "query",
            "--root", "./graphrag",
            "--method", "local",
            "--query", query
        ]

        process = subprocess.run(cmd, capture_output=True, text=True)

        # Log for debugging
        print("=== Graphrag Output ===")
        print(process.stdout.strip())
        print("========================")

        if process.returncode != 0:
            return jsonify({
                "error": "graphrag command failed",
                "stderr": process.stderr
            }), 500

        raw_output = process.stdout.strip()

        # Try to extract the user JSON from Graphrag's output
        user = extract_json_from_output(raw_output)

        if user:
            # Update Firestore: ptask/{uid}
            upsert_ptask_from_user(user)
            # Return the parsed user JSON to caller
            return jsonify(user), 200

        # Fallback: if it's valid JSON but not an object we expect
        try:
            parsed = json.loads(raw_output)
            return jsonify(parsed), 200
        except json.JSONDecodeError:
            # If it's not JSON at all: just return the text
            return raw_output, 200, {"Content-Type": "text/plain"}

    except Exception as e:
        print("Error in /task:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=25565)
