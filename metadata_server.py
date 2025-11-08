#!/usr/bin/env python3
"""
Simple NFT Metadata Server for Achievement Badges
Serves metadata in a format that MetaMask can display properly
"""

from flask import Flask, jsonify
from flask_cors import CORS
from web3 import Web3
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Sepolia connection
INFURA_URL = "https://sepolia.infura.io/v3/713dcbe5e2254d718e5040c2ae716c3f"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

# Load contract info
with open('python/deployment.json', 'r') as f:
    deployment = json.load(f)

ACHIEVEMENT_ADDRESS = deployment['achievementBadgeContract']['address']
ACHIEVEMENT_ABI = deployment['achievementBadgeContract']['abi']

achievement_contract = w3.eth.contract(
    address=ACHIEVEMENT_ADDRESS,
    abi=ACHIEVEMENT_ABI
)

@app.route('/')
def index():
    return jsonify({
        "name": "SideQuests Achievement NFT Metadata Server",
        "contract": ACHIEVEMENT_ADDRESS,
        "network": "Sepolia",
        "usage": "/metadata/<token_id>"
    })

@app.route('/metadata/<int:token_id>')
def get_metadata(token_id):
    """Get NFT metadata for a specific token ID"""
    try:
        # Get badge data from contract
        badge = achievement_contract.functions.badges(token_id).call()
        
        # Parse badge data
        achievement_type = badge[0]
        title = badge[1]
        description = badge[2]
        image_uri = badge[3]
        minted_at = badge[4]
        rarity = badge[5]
        
        # Rarity mapping
        rarity_names = {
            1: "Common",
            2: "Rare",
            3: "Epic",
            4: "Legendary"
        }
        
        # Build metadata response
        metadata = {
            "name": f"{title} #{token_id}",
            "description": description,
            "image": image_uri,
            "external_url": f"https://sidequests.com/achievements/{token_id}",
            "attributes": [
                {
                    "trait_type": "Rarity",
                    "value": rarity_names.get(rarity, "Common")
                },
                {
                    "trait_type": "Achievement Type",
                    "value": str(achievement_type)
                },
                {
                    "trait_type": "Minted At",
                    "display_type": "date",
                    "value": minted_at
                }
            ]
        }
        
        return jsonify(metadata)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "token_id": token_id
        }), 404

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Check if contract is accessible
        total_supply = achievement_contract.functions.totalSupply().call()
        return jsonify({
            "status": "healthy",
            "contract": ACHIEVEMENT_ADDRESS,
            "total_nfts": total_supply
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    print(f"\n🚀 Starting SideQuests NFT Metadata Server")
    print(f"📝 Contract: {ACHIEVEMENT_ADDRESS}")
    print(f"🌐 Network: Sepolia")
    print(f"\n💡 NFT metadata available at: http://localhost:5000/metadata/<token_id>")
    print(f"Example: http://localhost:5000/metadata/1\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
