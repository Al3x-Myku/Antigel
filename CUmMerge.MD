Community Rewards dApp - Deployment Package

This package contains the Solidity smart contracts and a Python deployment script for the Community Rewards dApp.

Prerequisites

Before you begin, you will need:

Python 3.10+ (with pip available).

Node.js and npm (to install OpenZeppelin).

An EVM Wallet Private Key (e.g., from MetaMask). This wallet must be funded with Sepolia ETH.

A Sepolia RPC Endpoint URL (e.g., from Infura, Alchemy, or QuickNode).

Setup Instructions

Install OpenZeppelin Contracts:
The smart contracts import OpenZeppelin libraries. You must install them locally so the compiler can find them.

npm install @openzeppelin/contracts


This will create a node_modules directory in this folder.

Install Python Dependencies:
The deployment script requires several Python libraries.

pip install -r requirements.txt


Configure Environment Variables:
Create a file named .env in this directory. Copy the contents of .env.example into it and fill in your own values.

cp .env.example .env


Now, edit .env:

INFURA_URL: Your full Sepolia RPC endpoint URL.

PRIVATE_KEY: Your wallet's private key (must start with 0x). Do not share this key with anyone.

Deployment

Once your setup is complete and your .env file is populated, simply run the Python script:

python deploy.py


The script will:

Install the correct Solidity compiler version.

Compile both RewardContract.sol and TaskContract.sol.

Deploy the RewardContract.

Deploy the TaskContract (using the new RewardContract address).

Send a final transaction to grant the MINTER_ROLE to the TaskContract.

Generate a deployment_artifacts.json file.

Output

If successful, you will see --- DEPLOYMENT COMPLETE --- in your terminal, and a new file named deployment_artifacts.json will be created.

This JSON file contains the contract addresses and ABIs, which your Go backend will use to interact with the deployed contracts.
