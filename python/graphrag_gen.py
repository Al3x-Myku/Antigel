import subprocess

# === CONFIG ===
PROJECT_ROOT = "./graphrag"

# === RUN GRAPH RAG INDEX ===
print(f"🚀 Running GraphRAG index for project root: {PROJECT_ROOT}\n")

# Run the CLI command
subprocess.run(["graphrag", "index", "--root", PROJECT_ROOT], check=True)

print("\n✅ GraphRAG indexing complete.")