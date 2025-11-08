package main

import (
	"context"
	"crypto/ecdsa"
	"encoding/json"
	"log"
	"math/big"
	"net/http"
	"os" // <-- ADDED
	"strings"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/accounts/abi/bind"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethclient"
	"github.com/joho/godotenv" // <-- ADDED
)

var (
	infuraURL         string
	sepoliaPrivateKey string
)

const contractABI = `[{"inputs":[],"name":"retrieve","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"string","name":"_value","type":"string"}],"name":"store","outputs":[],"stateMutability":"nonpayable","type":"function"}]`


const contractBIN = `608060405234801561001057600080fd5b5061017e806100206000396000f3fe608060405234801561001057600080fd5b50600436106100365760003560e01c80632e64C26E1461003b5780636057361D1461005757b600080fd5b610055600480360381019061005091906100d0565b610075565b005b61005f610080565b60405161006c91906100f2565b60405180910390f35b806000819055505b5060008054905090565b600080546001600160a01b0319166001600160a01b0316909190509091505550565b6000815190506100c457600082825401925050819055506100cd565b90565b6000813590506100d8565b90565b6000602082840312156100ee576100ed61008f565b5b60006100fc848285016100c7565b91505092915050565b61010e81610086565b82525050565b60208101905061012657610002565b6101345760208201905061014e565b905081565b600080fd5b600081905091905056fe600081905091905056a164736f6c6343000811000a`

type apiResponse struct {
	BlockNumber     string `json:"blockNumber,omitempty"`
	Error           string `json:"error,omitempty"`
	ContractAddress string `json:"contractAddress,omitempty"`
}

// writeJSON sends a JSON response
func writeJSON(w http.ResponseWriter, data interface{}, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(data)
}

// connectHandler connects to Ethereum via the backend (Infura)
func connectHandler(w http.ResponseWriter, r *http.Request) {
	client, err := ethclient.DialContext(r.Context(), infuraURL)
	if err != nil {
		log.Printf("Failed to dial Infura: %v", err)
		writeJSON(w, apiResponse{Error: "Failed to connect to Ethereum node"}, http.StatusInternalServerError)
		return
	}
	defer client.Close()

	header, err := client.HeaderByNumber(context.Background(), nil)
	if err != nil {
		log.Printf("Failed to get block header: %v", err)
		writeJSON(w, apiResponse{Error: "Failed to retrieve block header from Ethereum"}, http.StatusInternalServerError)
		return
	}
	blockNumber := header.Number
	if blockNumber == nil {
		blockNumber = big.NewInt(0) // Handle nil case
	}
	log.Println("Successfully retrieved block number:", blockNumber.String())
	writeJSON(w, apiResponse{BlockNumber: blockNumber.String()}, http.StatusOK)
}

func deployHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, apiResponse{Error: "Method not allowed"}, http.StatusMethodNotAllowed)
		return
	}

	client, err := ethclient.DialContext(r.Context(), infuraURL)
	if err != nil {
		log.Printf("Failed to dial Infura: %v", err)
		writeJSON(w, apiResponse{Error: "Failed to connect to Ethereum node"}, http.StatusInternalServerError)
		return
	}
	defer client.Close()

	privateKey, err := crypto.HexToECDSA(sepoliaPrivateKey)
	if err != nil {
		log.Printf("Failed to parse private key: %v", err)
		writeJSON(w, apiResponse{Error: "Failed to parse private key"}, http.StatusInternalServerError)
		return
	}

	publicKey := privateKey.Public()
	publicKeyECDSA, ok := publicKey.(*ecdsa.PublicKey)
	if !ok {
		writeJSON(w, apiResponse{Error: "Invalid public key"}, http.StatusInternalServerError)
		return
	}
	fromAddress := crypto.PubkeyToAddress(*publicKeyECDSA)
	chainID, err := client.ChainID(context.Background())
	if err != nil {
		log.Printf("Failed to get chain ID: %v", err)
		writeJSON(w, apiResponse{Error: "Failed to get chain ID"}, http.StatusInternalServerError)
		return
	}
	nonce, err := client.PendingNonceAt(context.Background(), fromAddress)
	if err != nil {
		log.Printf("Failed to get nonce: %v", err)
		writeJSON(w, apiResponse{Error: "Failed to get nonce"}, http.StatusInternalServerError)
		return
	}

	gasPrice, err := client.SuggestGasPrice(context.Background())
	if err != nil {
		log.Printf("Failed to get gas price: %v", err)
		writeJSON(w, apiResponse{Error: "Failed to get gas price"}, http.StatusInternalServerError)
		return
	}

	auth, err := bind.NewKeyedTransactorWithChainID(privateKey, chainID)
	if err != nil {
		log.Printf("Failed to create transactor: %v", err)
		writeJSON(w, apiResponse{Error: "Failed to create transactor"}, http.StatusInternalServerError)
		return
	}
	auth.Nonce = big.NewInt(int64(nonce))
	auth.Value = big.NewInt(0)      // 0 ETH
	auth.GasLimit = uint64(3000000) // Gas limit
	auth.GasPrice = gasPrice

	parsedABI, err := abi.JSON(strings.NewReader(contractABI))
	if err != nil {
		log.Printf("Failed to parse ABI: %v", err)
		writeJSON(w, apiResponse{Error: "Failed to parse ABI"}, http.StatusInternalServerError)
		return
	}
	bytecode := common.FromHex(contractBIN)

	address, tx, _, err := bind.DeployContract(auth, parsedABI, bytecode, client, nil)
	if err != nil {
		log.Printf("Failed to deploy contract: %v", err)
		writeJSON(w, apiResponse{Error: "Failed to deploy contract: " + err.Error()}, http.StatusInternalServerError)
		return
	}

	log.Printf("Contract pending deploy: Address %s, Tx %s", address.Hex(), tx.Hash().Hex())

	writeJSON(w, apiResponse{ContractAddress: address.Hex()}, http.StatusOK)
}

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Printf("Warning: Error loading .env file. Using environment variables. %v", err)
	}

	infuraURL = os.Getenv("SEPOLIA_URL")
	sepoliaPrivateKey = os.Getenv("SEPOLIA_PRIVATE_KEY")

	if infuraURL == "" {
		log.Fatal("SEPOLIA_URL not set in .env file or environment")
	}
	if sepoliaPrivateKey == "" {
		log.Fatal("SEPOLIA_PRIVATE_KEY not set in .env file or environment")
	}
	http.HandleFunc("/api/connect", connectHandler)

	http.HandleFunc("/api/deploy", deployHandler)

	fs := http.FileServer(http.Dir("."))
	http.Handle("/", fs)

	port := ":8080"
	log.Printf("Server starting on http://localhost%s", port)
	log.Println("Serving files from the current directory.")
	log.Fatal(http.ListenAndServe(port, nil))
}
