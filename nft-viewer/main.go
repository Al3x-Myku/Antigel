package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"math/big"
	"net/url"
	"os"
	"strings"

	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/ethclient"
)

const (
	SEPOLIA_RPC_URL = "https://sepolia.infura.io/v3/713dcbe5e2254d718e5040c2ae716c3f"
)

// Deployment configuration structure
type DeploymentConfig struct {
	AchievementBadgeContract struct {
		Address string          `json:"address"`
		ABI     json.RawMessage `json:"abi"`
	} `json:"achievementBadgeContract"`
}

// NFT Metadata structures
type NFTAttribute struct {
	TraitType string      `json:"trait_type"`
	Value     interface{} `json:"value"`
}

type NFTMetadata struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	Image       string         `json:"image"`
	Attributes  []NFTAttribute `json:"attributes"`
}

// Badge data from contract
type BadgeData struct {
	AchievementType *big.Int
	Title           string
	Description     string
	ImageURI        string
	MintedAt        *big.Int
	Rarity          *big.Int
}

// Rarity mapping
var rarityNames = map[int64]string{
	1: "Common",
	2: "Rare",
	3: "Epic",
	4: "Legendary",
}

// Achievement type mapping
var achievementTypes = map[int64]string{
	0:  "First Quest",
	1:  "Getting Started",
	2:  "Task Hunter",
	3:  "Dedicated Worker",
	4:  "Veteran Quester",
	5:  "Quest Master",
	6:  "Early Adopter",
	7:  "Token Collector",
	8:  "Wealth Builder",
	9:  "Token Whale",
	10: "Community Builder",
	11: "Mentor",
	12: "Week Warrior",
	13: "Monthly Champion",
	14: "Top Performer",
	15: "Helpful Reviewer",
}

// Achievement image URLs
var achievementImages = map[int64]string{
	0:  "https://img.icons8.com/fluency/96/000000/bullseye.png",
	1:  "https://img.icons8.com/fluency/96/000000/running.png",
	2:  "https://img.icons8.com/fluency/96/000000/search.png",
	3:  "https://img.icons8.com/fluency/96/000000/worker-male.png",
	4:  "https://img.icons8.com/fluency/96/000000/medal.png",
	5:  "https://img.icons8.com/fluency/96/000000/crown.png",
	6:  "https://img.icons8.com/fluency/96/000000/rocket.png",
	7:  "https://img.icons8.com/fluency/96/000000/money-bag.png",
	8:  "https://img.icons8.com/fluency/96/000000/profit.png",
	9:  "https://img.icons8.com/fluency/96/000000/whale.png",
	10: "https://img.icons8.com/fluency/96/000000/conference-call.png",
	11: "https://img.icons8.com/fluency/96/000000/teacher.png",
	12: "https://img.icons8.com/fluency/96/000000/calendar-7.png",
	13: "https://img.icons8.com/fluency/96/000000/calendar-30.png",
	14: "https://img.icons8.com/fluency/96/000000/trophy.png",
	15: "https://img.icons8.com/fluency/96/000000/rating.png",
}

// Call contract method
func callContract(client *ethclient.Client, contractAddress common.Address, contractABI abi.ABI, methodName string, result interface{}, args ...interface{}) error {
	// Pack the method call
	data, err := contractABI.Pack(methodName, args...)
	if err != nil {
		return fmt.Errorf("failed to pack method call: %v", err)
	}

	// Create call message
	msg := ethereum.CallMsg{
		To:   &contractAddress,
		Data: data,
	}

	// Execute call
	output, err := client.CallContract(context.Background(), msg, nil)
	if err != nil {
		return fmt.Errorf("contract call failed: %v", err)
	}

	// Unpack the result
	if err := contractABI.UnpackIntoInterface(result, methodName, output); err != nil {
		return fmt.Errorf("failed to unpack result: %v", err)
	}

	return nil
}

// Get badge data from contract
func getBadgeData(client *ethclient.Client, contractAddress common.Address, contractABI abi.ABI, tokenID int64) (*BadgeData, error) {
	var result struct {
		AchievementType uint8
		Title           string
		Description     string
		ImageURI        string
		MintedAt        *big.Int
		Rarity          *big.Int
	}

	err := callContract(client, contractAddress, contractABI, "badges", &result, big.NewInt(tokenID))
	if err != nil {
		return nil, err
	}

	return &BadgeData{
		AchievementType: big.NewInt(int64(result.AchievementType)),
		Title:           result.Title,
		Description:     result.Description,
		ImageURI:        result.ImageURI,
		MintedAt:        result.MintedAt,
		Rarity:          result.Rarity,
	}, nil
}

// Get total supply of NFTs
func getTotalSupply(client *ethclient.Client, contractAddress common.Address, contractABI abi.ABI) (int64, error) {
	var result *big.Int
	err := callContract(client, contractAddress, contractABI, "totalSupply", &result)
	if err != nil {
		return 0, err
	}
	return result.Int64(), nil
}

// Decode data URI
func decodeDataURI(dataURI string) (*NFTMetadata, error) {
	if !strings.HasPrefix(dataURI, "data:application/json,") {
		return nil, fmt.Errorf("invalid data URI format")
	}

	// Remove prefix
	jsonData := strings.TrimPrefix(dataURI, "data:application/json,")

	// URL decode
	decoded, err := url.QueryUnescape(jsonData)
	if err != nil {
		return nil, fmt.Errorf("failed to decode URI: %v", err)
	}

	// Parse JSON
	var metadata NFTMetadata
	if err := json.Unmarshal([]byte(decoded), &metadata); err != nil {
		return nil, fmt.Errorf("failed to parse JSON: %v", err)
	}

	return &metadata, nil
}

// Display NFT metadata
func displayNFT(client *ethclient.Client, contractAddress common.Address, contractABI abi.ABI, tokenID int64) error {
	// Get badge data
	badge, err := getBadgeData(client, contractAddress, contractABI, tokenID)
	if err != nil {
		return fmt.Errorf("failed to get badge data: %v", err)
	}

	// Get image URL from mapping
	imageURL := achievementImages[badge.AchievementType.Int64()]
	if imageURL == "" {
		imageURL = badge.ImageURI
	}

	// Get rarity name
	rarityName := rarityNames[badge.Rarity.Int64()]
	if rarityName == "" {
		rarityName = "Unknown"
	}

	// Get achievement type name
	achievementName := achievementTypes[badge.AchievementType.Int64()]
	if achievementName == "" {
		achievementName = "Unknown"
	}

	// Print NFT information
	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Printf("🏆 NFT #%d: %s\n", tokenID, badge.Title)
	fmt.Println(strings.Repeat("=", 70))
	fmt.Printf("\n📊 NFT INFORMATION:\n")
	fmt.Printf("  Achievement Type: %d (%s)\n", badge.AchievementType.Int64(), achievementName)
	fmt.Printf("  Title: %s\n", badge.Title)
	fmt.Printf("  Description: %s\n", badge.Description)
	fmt.Printf("  Rarity: %s\n", rarityName)
	fmt.Printf("  Minted At: %d\n", badge.MintedAt.Int64())
	fmt.Printf("\n🖼️  IMAGE:\n")
	fmt.Printf("  URL: %s\n", imageURL)
	fmt.Printf("\n💡 To view the image, open this URL in your browser:\n")
	fmt.Printf("  %s\n", imageURL)
	fmt.Println(strings.Repeat("=", 70))

	return nil
}

// Display all NFTs
func displayAllNFTs(client *ethclient.Client, contractAddress common.Address, contractABI abi.ABI) error {
	totalSupply, err := getTotalSupply(client, contractAddress, contractABI)
	if err != nil {
		return fmt.Errorf("failed to get total supply: %v", err)
	}

	if totalSupply == 0 {
		fmt.Println("\n📭 No NFTs have been minted yet.")
		fmt.Println("\n💡 To mint your first NFT:")
		fmt.Println("   1. Connect wallet to the app")
		fmt.Println("   2. Complete a task")
		fmt.Println("   3. The creator will complete the task and you'll get:")
		fmt.Println("      - HLP tokens (reward)")
		fmt.Println("      - Achievement NFT (badge)")
		return nil
	}

	fmt.Printf("\n📦 Total NFTs minted: %d\n", totalSupply)

	for i := int64(1); i <= totalSupply; i++ {
		if err := displayNFT(client, contractAddress, contractABI, i); err != nil {
			log.Printf("Error displaying NFT #%d: %v", i, err)
			continue
		}
	}

	fmt.Printf("\n✅ Successfully displayed %d NFT(s)\n\n", totalSupply)
	return nil
}

func main() {
	fmt.Println(`
╔══════════════════════════════════════════════════════════════════════╗
║              SideQuests NFT Viewer (Go Edition)                      ║
║                                                                      ║
║  This program displays NFT metadata including photos and             ║
║  descriptions from your Achievement NFT contract.                    ║
╚══════════════════════════════════════════════════════════════════════╝
	`)

	// Connect to Sepolia
	client, err := ethclient.Dial(SEPOLIA_RPC_URL)
	if err != nil {
		log.Fatalf("❌ Failed to connect to Sepolia: %v", err)
	}
	defer client.Close()

	blockNumber, err := client.BlockNumber(context.Background())
	if err != nil {
		log.Fatalf("❌ Failed to get block number: %v", err)
	}

	fmt.Printf("✅ Connected to Sepolia (Block: %d)\n", blockNumber)

	// Load deployment configuration
	deploymentData, err := ioutil.ReadFile("../python/deployment.json")
	if err != nil {
		log.Fatalf("❌ Failed to read deployment.json: %v", err)
	}

	var deployment DeploymentConfig
	if err := json.Unmarshal(deploymentData, &deployment); err != nil {
		log.Fatalf("❌ Failed to parse deployment.json: %v", err)
	}

	contractAddress := common.HexToAddress(deployment.AchievementBadgeContract.Address)
	fmt.Printf("📝 Achievement Contract: %s\n", contractAddress.Hex())

	// Parse ABI
	contractABI, err := abi.JSON(strings.NewReader(string(deployment.AchievementBadgeContract.ABI)))
	if err != nil {
		log.Fatalf("❌ Failed to parse contract ABI: %v", err)
	}

	// Check if specific token ID is provided
	if len(os.Args) > 1 {
		var tokenID int64
		fmt.Sscanf(os.Args[1], "%d", &tokenID)
		if tokenID > 0 {
			if err := displayNFT(client, contractAddress, contractABI, tokenID); err != nil {
				log.Fatalf("❌ Error: %v", err)
			}
			return
		}
	}

	// Display all NFTs
	if err := displayAllNFTs(client, contractAddress, contractABI); err != nil {
		log.Fatalf("❌ Error: %v", err)
	}

	fmt.Println(`
📚 USAGE:
   
   View all NFTs:
     go run viewNFT.go
   
   View specific NFT:
     go run viewNFT.go 1
     go run viewNFT.go 2
   
   Or build and run:
     go build viewNFT.go
     ./viewNFT
     ./viewNFT 1
	`)
}
