from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

@app.route('/task', methods=['POST'])
def handle_task():
    try:
        data = request.get_json(force=True)
        description = data.get("description")

        if not description:
            return jsonify({"error": "Missing 'description' field"}), 400

        # Build the query
        query = f"Can you recommend someone for {description}. Just the whole json no other text"

        # Command to run
        cmd = [
            "graphrag",
            "query",
            "--root", "./graphrag",
            "--method", "local",
            "--query", query
        ]

        # Run the graphrag command
        process = subprocess.run(cmd, capture_output=True, text=True)

        # Print to stdout for server logs
        print("=== Graphrag Output ===")
        print(process.stdout.strip())
        print("========================")

        # Return the raw graphrag output as response
        if process.returncode == 0:
            try:
                # Attempt to parse output as JSON (if graphrag returns JSON)
                output_json = json.loads(process.stdout)
                return jsonify(output_json)
            except json.JSONDecodeError:
                # Return raw text if not JSON
                return process.stdout, 200, {"Content-Type": "text/plain"}
        else:
            return jsonify({
                "error": "graphrag command failed",
                "stderr": process.stderr
            }), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=25565)
