import json
import subprocess
import sys

def main(json_path):
    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract description field
    description = data.get("description")
    if not description:
        print("Error: 'description' field not found in JSON.", file=sys.stderr)
        sys.exit(1)

    # Build query
    query = f"Can you recommend someone for {description}. Just the whole json no other text"

    # Build command
    cmd = [
        "graphrag",
        "query",
        "--root", "./graphrag",
        "--method", "local",
        "--query", query
    ]

    # Run the command and stream output to stdout
    process = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, text=True)
    process.communicate()

    # Exit with the same return code as graphrag
    sys.exit(process.returncode)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_graphrag.py <path_to_json_file>", file=sys.stderr)
        sys.exit(1)

    main(sys.argv[1])