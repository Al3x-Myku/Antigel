package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/accounts/abi/bind"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/ethclient"
)

// Global configuration
var (
	infuraURL      string
	ethClient      *ethclient.Client
	deploymentData DeploymentConfig
)

// Deployment configuration structure
type DeploymentConfig struct {
	Network                  string       `json:"network"`
	Deployer                 string       `json:"deployer"`
	RewardContract           ContractInfo `json:"rewardContract"`
	TaskContract             ContractInfo `json:"taskContract"`
	AchievementBadgeContract ContractInfo `json:"achievementBadgeContract"`
	DeploymentBlock          int64        `json:"deploymentBlock"`
}

type ContractInfo struct {
	Address string          `json:"address"`
	ABI     json.RawMessage `json:"abi"`
}

// Task structure matching the smart contract
type Task struct {
	ID          *big.Int `json:"id"`
	Title       string   `json:"title"`
	Description string   `json:"description"`
	Reward      *big.Int `json:"reward"`
	Completed   bool     `json:"completed"`
	Worker      string   `json:"worker"`
	Creator     string   `json:"creator"`
}

// API response structures
type APIResponse struct {
	Success     bool        `json:"success"`
	Data        interface{} `json:"data,omitempty"`
	Error       string      `json:"error,omitempty"`
	Message     string      `json:"message,omitempty"`
	BlockNumber string      `json:"blockNumber,omitempty"`
}

type TaskResponse struct {
	Tasks []Task `json:"tasks"`
	Count int    `json:"count"`
}

type ContractAddressResponse struct {
	RewardContract      string `json:"rewardContract"`
	TaskContract        string `json:"taskContract"`
	AchievementContract string `json:"achievementContract"`
	Network             string `json:"network"`
}

type UserStatsResponse struct {
	TasksCompleted  *big.Int `json:"tasksCompleted"`
	TokensEarned    *big.Int `json:"tokensEarned"`
	TasksCreated    *big.Int `json:"tasksCreated"`
	CurrentStreak   *big.Int `json:"currentStreak"`
	MaxStreak       *big.Int `json:"maxStreak"`
	TokenBalance    *big.Int `json:"tokenBalance"`
	AchievementNFTs []string `json:"achievementNFTs"`
}

// Utility functions
func writeJSON(w http.ResponseWriter, data interface{}, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

	if statusCode != 0 {
		w.WriteHeader(statusCode)
	}

	if err := json.NewEncoder(w).Encode(data); err != nil {
		log.Printf("Error encoding JSON response: %v", err)
	}
}

func writeError(w http.ResponseWriter, message string, statusCode int) {
	writeJSON(w, APIResponse{
		Success: false,
		Error:   message,
	}, statusCode)
}

func writeSuccess(w http.ResponseWriter, data interface{}, message string) {
	writeJSON(w, APIResponse{
		Success: true,
		Data:    data,
		Message: message,
	}, http.StatusOK)
}

// Initialize the application with Ethereum connection and deployment data
func initializeApp() error {
	log.Println("🚀 Initializing SideQuests Backend...")

	// Use a public Sepolia endpoint for read-only operations
	// For this demo, we'll use a public endpoint
	// In production, set SEPOLIA_URL environment variable
	envURL := os.Getenv("SEPOLIA_URL")
	if envURL != "" {
		infuraURL = envURL
	} else {
		// Use public Sepolia endpoint
		infuraURL = "https://rpc.sepolia.org"
	}

	// Connect to Ethereum network
	var err error
	ethClient, err = ethclient.Dial(infuraURL)
	if err != nil {
		return fmt.Errorf("failed to connect to Ethereum network: %v", err)
	}

	// Load deployment data
	deploymentPath := filepath.Join("python", "deployment.json")
	deploymentBytes, err := os.ReadFile(deploymentPath)
	if err != nil {
		return fmt.Errorf("failed to read deployment.json: %v", err)
	}

	if err := json.Unmarshal(deploymentBytes, &deploymentData); err != nil {
		return fmt.Errorf("failed to parse deployment.json: %v", err)
	}

	log.Printf("✅ Connected to %s network", deploymentData.Network)
	log.Printf("📝 Task Contract: %s", deploymentData.TaskContract.Address)
	log.Printf("💰 Reward Contract: %s", deploymentData.RewardContract.Address)
	log.Printf("🏆 Achievement Contract: %s", deploymentData.AchievementBadgeContract.Address)

	return nil
}

// API Handlers

// Health check and network status
func healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	header, err := ethClient.HeaderByNumber(ctx, nil)
	if err != nil {
		log.Printf("Failed to get block header: %v", err)
		writeError(w, "Failed to retrieve block header from Ethereum", http.StatusInternalServerError)
		return
	}

	blockNumber := header.Number
	if blockNumber == nil {
		blockNumber = big.NewInt(0)
	}

	writeSuccess(w, map[string]interface{}{
		"blockNumber": blockNumber.String(),
		"network":     deploymentData.Network,
		"timestamp":   time.Now().Unix(),
	}, "Network connection successful")
}

// Get contract addresses
func contractAddressesHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		return
	}

	response := ContractAddressResponse{
		RewardContract:      deploymentData.RewardContract.Address,
		TaskContract:        deploymentData.TaskContract.Address,
		AchievementContract: deploymentData.AchievementBadgeContract.Address,
		Network:             deploymentData.Network,
	}

	writeSuccess(w, response, "Contract addresses retrieved")
}

// Get contract ABIs
func contractABIsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		return
	}

	response := map[string]interface{}{
		"rewardContract":      json.RawMessage(deploymentData.RewardContract.ABI),
		"taskContract":        json.RawMessage(deploymentData.TaskContract.ABI),
		"achievementContract": json.RawMessage(deploymentData.AchievementBadgeContract.ABI),
	}

	writeSuccess(w, response, "Contract ABIs retrieved")
}

// Get tasks from the blockchain
func getTasksHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		return
	}

	// Parse ABI
	taskABI, err := abi.JSON(strings.NewReader(string(deploymentData.TaskContract.ABI)))
	if err != nil {
		writeError(w, fmt.Sprintf("Failed to parse task contract ABI: %v", err), http.StatusInternalServerError)
		return
	}

	// Create contract instance
	taskContractAddress := common.HexToAddress(deploymentData.TaskContract.Address)
	taskContract := bind.NewBoundContract(taskContractAddress, taskABI, ethClient, ethClient, ethClient)

	// Get total task count
	results := make([]interface{}, 1)
	err = taskContract.Call(nil, &results, "getTaskCount")
	if err != nil {
		writeError(w, fmt.Sprintf("Failed to get task count: %v", err), http.StatusInternalServerError)
		return
	}

	taskCount, ok := results[0].(*big.Int)
	if !ok {
		writeError(w, "Invalid task count format", http.StatusInternalServerError)
		return
	}

	tasks := make([]Task, 0)

	// Fetch each task (starting from 0 since arrays are 0-indexed)
	for i := int64(0); i < taskCount.Int64(); i++ {
		taskResults := make([]interface{}, 6) // TaskStruct has 6 fields
		err = taskContract.Call(nil, &taskResults, "tasks", big.NewInt(i))
		if err != nil {
			log.Printf("Error fetching task %d: %v", i, err)
			continue
		}

		// Parse task data according to TaskStruct: title, description, reward, creator, worker, isCompleted
		title, _ := taskResults[0].(string)
		description, _ := taskResults[1].(string)
		reward, _ := taskResults[2].(*big.Int)
		creator, _ := taskResults[3].(common.Address)
		worker, _ := taskResults[4].(common.Address)
		isCompleted, _ := taskResults[5].(bool)

		task := Task{
			ID:          big.NewInt(i),
			Title:       title,
			Description: description,
			Reward:      reward,
			Creator:     creator.Hex(),
			Worker:      worker.Hex(),
			Completed:   isCompleted,
		}

		tasks = append(tasks, task)
	}

	response := TaskResponse{
		Tasks: tasks,
		Count: len(tasks),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// Get user statistics (simplified version)
func getUserStatsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		return
	}

	userAddress := r.URL.Query().Get("address")
	if userAddress == "" {
		writeError(w, "User address is required", http.StatusBadRequest)
		return
	}

	if !common.IsHexAddress(userAddress) {
		writeError(w, "Invalid Ethereum address", http.StatusBadRequest)
		return
	}

	// For now, return mock data since complex contract calls need more setup
	// In production, this would make actual contract calls
	response := UserStatsResponse{
		TasksCompleted:  big.NewInt(5),
		TokensEarned:    big.NewInt(1000),
		TasksCreated:    big.NewInt(3),
		CurrentStreak:   big.NewInt(2),
		MaxStreak:       big.NewInt(4),
		TokenBalance:    big.NewInt(1000),
		AchievementNFTs: []string{"1", "2"},
	}

	writeSuccess(w, response, "User statistics retrieved")
}

// Get NFT metadata
func getNFTMetadataHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		return
	}

	tokenIDStr := r.URL.Query().Get("tokenId")
	if tokenIDStr == "" {
		writeError(w, "Token ID is required", http.StatusBadRequest)
		return
	}

	tokenID, err := strconv.ParseInt(tokenIDStr, 10, 64)
	if err != nil {
		writeError(w, "Invalid token ID", http.StatusBadRequest)
		return
	}

	// For now, return mock metadata
	// In production, this would call the contract's tokenURI function
	response := map[string]interface{}{
		"tokenId":     tokenID,
		"uri":         fmt.Sprintf("https://api.sidequests.io/metadata/%d", tokenID),
		"name":        fmt.Sprintf("SideQuests Badge #%d", tokenID),
		"description": "Achievement badge for completing SideQuests tasks",
		"image":       fmt.Sprintf("https://api.sidequests.io/images/badge_%d.png", tokenID),
	}

	writeSuccess(w, response, "NFT metadata retrieved")
}

// HTML Page Handlers
func landingPageHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		return
	}

	// Add CORS headers
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	http.ServeFile(w, r, "landingpage.html")
}

func loginPageHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		return
	}

	// Add CORS headers
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	http.ServeFile(w, r, "login.html")
}

func registerPageHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		return
	}

	// Add CORS headers
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	http.ServeFile(w, r, "register.html")
}

func appPageHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		return
	}

	// Add CORS headers
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	http.ServeFile(w, r, "index.html")
}

// Static assets handler (for CSS, JS, images, etc.)
func staticAssetsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodOptions {
		return
	}

	// Add CORS headers
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

	// Only allow specific file types for security
	path := r.URL.Path[9:] // Remove "/static/" prefix
	if isAllowedStaticFile(path) {
		http.ServeFile(w, r, path)
	} else {
		http.Error(w, "File not found", http.StatusNotFound)
	}
}

// Helper function to check allowed static file types
func isAllowedStaticFile(path string) bool {
	allowedExtensions := []string{".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot"}
	for _, ext := range allowedExtensions {
		if strings.HasSuffix(strings.ToLower(path), ext) {
			return true
		}
	}
	return false
}

func main() {
	// Initialize the application
	if err := initializeApp(); err != nil {
		log.Fatalf("Failed to initialize application: %v", err)
	}

	// Set up API routes
	http.HandleFunc("/api/health", healthHandler)
	http.HandleFunc("/api/contracts/addresses", contractAddressesHandler)
	http.HandleFunc("/api/contracts/abis", contractABIsHandler)
	http.HandleFunc("/api/tasks", getTasksHandler)
	http.HandleFunc("/api/users/stats", getUserStatsHandler)
	http.HandleFunc("/api/nft/metadata", getNFTMetadataHandler)

	// Set up page routes (secure HTML serving)
	http.HandleFunc("/", landingPageHandler)
	http.HandleFunc("/login", loginPageHandler)
	http.HandleFunc("/register", registerPageHandler)
	http.HandleFunc("/app", appPageHandler)

	// Static assets (CSS, JS, images, etc.)
	http.HandleFunc("/static/", staticAssetsHandler)
	// Start server
	port := ":8080"
	log.Printf("🚀 SideQuests Backend Server starting on http://localhost%s", port)
	log.Printf("🏠 Landing page available at: http://localhost%s/", port)
	log.Printf("🔐 Login page available at: http://localhost%s/login", port)
	log.Printf("📝 Register page available at: http://localhost%s/register", port)
	log.Printf("💻 Main app available at: http://localhost%s/app", port)
	log.Printf("🌐 API endpoints available at /api/*")
	log.Printf("🗂️ Static assets available at /static/*")

	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}
