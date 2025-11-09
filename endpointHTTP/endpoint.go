package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"time"

	"cloud.google.com/go/firestore"
	firebase "firebase.google.com/go"
	"google.golang.org/api/option"
)

// TaskRequest represents the incoming task JSON
type TaskRequest struct {
	ID           string   `json:"id"`
	Title        string   `json:"title"`
	Description  string   `json:"description"`
	Requirements []string `json:"requirements"`
	Skills       []string `json:"skills"`
	Reward       float64  `json:"reward"`
	Deadline     string   `json:"deadline"`
	Creator      string   `json:"creator"`
}

// GraphRAGResponse represents the response from GraphRAG query
type GraphRAGResponse struct {
	SelectedMembers []SelectedMember `json:"selected_members"`
	TaskID          string           `json:"task_id"`
	Confidence      float64          `json:"confidence"`
	Reasoning       string           `json:"reasoning"`
}

// SelectedMember represents a member selected by GraphRAG
type SelectedMember struct {
	UserID    string   `json:"user_id"`
	Name      string   `json:"name"`
	Skills    []string `json:"skills"`
	Score     float64  `json:"score"`
	Rationale string   `json:"rationale"`
}

// FirebaseTaskUpdate represents the data to update in Firebase
type FirebaseTaskUpdate struct {
	SelectedMembers []SelectedMember `json:"selected_members"`
	UpdatedAt       time.Time        `json:"updated_at"`
	Status          string           `json:"status"`
}

var firestoreClient *firestore.Client

// initializeFirebase initializes the Firebase client
func initializeFirebase() error {
	ctx := context.Background()

	// Firebase configuration for taskmatch-openhack2025
	config := &firebase.Config{
		ProjectID: "taskmatch-openhack2025",
	}

	// Use service account key file for authentication
	opt := option.WithCredentialsFile("../python/serviceAccountKey.json")

	app, err := firebase.NewApp(ctx, config, opt)
	if err != nil {
		return fmt.Errorf("error initializing Firebase app: %v", err)
	}

	client, err := app.Firestore(ctx)
	if err != nil {
		return fmt.Errorf("error initializing Firestore client: %v", err)
	}

	firestoreClient = client
	log.Println("✅ Firebase initialized successfully")
	return nil
}

// runGraphRAGQuery executes the GraphRAG query command with task data
func runGraphRAGQuery(task TaskRequest) (*GraphRAGResponse, error) {
	log.Printf("🔍 Running GraphRAG query for task: %s", task.ID)

	// Convert task to JSON for GraphRAG input
	taskJSON, err := json.Marshal(task)
	if err != nil {
		return nil, fmt.Errorf("error marshaling task to JSON: %v", err)
	}

	// Prepare GraphRAG command with task data
	query := fmt.Sprintf("Find the best team members for this task: %s", string(taskJSON))

	// Run GraphRAG command (adjust command based on your GraphRAG setup)
	cmd := exec.Command("graphrag", "query",
		"--root", "../python/graphrag",
		"--method", "local",
		"--query", query)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err = cmd.Run()
	if err != nil {
		return nil, fmt.Errorf("GraphRAG command failed: %v, stderr: %s", err, stderr.String())
	}

	// Parse GraphRAG response
	output := stdout.String()
	log.Printf("📊 GraphRAG raw output: %s", output)

	// Extract JSON from GraphRAG output (you may need to adjust this parsing)
	response, err := parseGraphRAGOutput(output, task.ID)
	if err != nil {
		return nil, fmt.Errorf("error parsing GraphRAG output: %v", err)
	}

	log.Printf("✅ GraphRAG found %d selected members", len(response.SelectedMembers))
	return response, nil
}

// parseGraphRAGOutput parses the GraphRAG output and extracts member selection
func parseGraphRAGOutput(output, taskID string) (*GraphRAGResponse, error) {
	// This is a simplified parser - you may need to adjust based on actual GraphRAG output format
	response := &GraphRAGResponse{
		TaskID:          taskID,
		SelectedMembers: []SelectedMember{},
		Confidence:      0.8, // Default confidence
		Reasoning:       "GraphRAG analysis completed",
	}

	// Try to find JSON in the output
	lines := strings.Split(output, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "{") && strings.HasSuffix(line, "}") {
			var jsonResponse map[string]interface{}
			if err := json.Unmarshal([]byte(line), &jsonResponse); err == nil {
				// Parse the JSON response and extract member data
				if members, ok := jsonResponse["members"].([]interface{}); ok {
					for _, member := range members {
						if memberMap, ok := member.(map[string]interface{}); ok {
							selectedMember := SelectedMember{
								UserID:    fmt.Sprintf("%v", memberMap["user_id"]),
								Name:      fmt.Sprintf("%v", memberMap["name"]),
								Score:     0.8, // Default score
								Rationale: "Selected by GraphRAG analysis",
							}

							if skills, ok := memberMap["skills"].([]interface{}); ok {
								for _, skill := range skills {
									selectedMember.Skills = append(selectedMember.Skills, fmt.Sprintf("%v", skill))
								}
							}

							response.SelectedMembers = append(response.SelectedMembers, selectedMember)
						}
					}
				}
			}
		}
	}

	// If no structured data found, create mock response based on output analysis
	if len(response.SelectedMembers) == 0 {
		log.Println("⚠️ No structured member data found, creating analysis-based response")
		// You can implement text analysis here to extract member information
		// For now, return empty response
	}

	return response, nil
}

// updateFirebaseWithMembers updates Firebase with the selected members
func updateFirebaseWithMembers(taskID string, response *GraphRAGResponse) error {
	log.Printf("📝 Updating Firebase for task %s with %d members", taskID, len(response.SelectedMembers))

	ctx := context.Background()

	updateData := FirebaseTaskUpdate{
		SelectedMembers: response.SelectedMembers,
		UpdatedAt:       time.Now(),
		Status:          "members_selected",
	}

	// Update the task document in Firestore
	_, err := firestoreClient.Collection("tasks").Doc(taskID).Update(ctx, []firestore.Update{
		{Path: "selected_members", Value: updateData.SelectedMembers},
		{Path: "updated_at", Value: updateData.UpdatedAt},
		{Path: "status", Value: updateData.Status},
		{Path: "graphrag_reasoning", Value: response.Reasoning},
		{Path: "confidence_score", Value: response.Confidence},
	})

	if err != nil {
		return fmt.Errorf("error updating Firestore: %v", err)
	}

	log.Printf("✅ Successfully updated Firebase for task %s", taskID)
	return nil
}

// processTaskHandler handles POST requests with task JSON
func processTaskHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Only POST method allowed", http.StatusMethodNotAllowed)
		return
	}

	log.Println("📥 Received task processing request")

	// Read request body
	body, err := io.ReadAll(r.Body)
	if err != nil {
		log.Printf("❌ Error reading request body: %v", err)
		http.Error(w, "Error reading request body", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	// Parse task JSON
	var task TaskRequest
	if err := json.Unmarshal(body, &task); err != nil {
		log.Printf("❌ Error parsing JSON: %v", err)
		http.Error(w, "Invalid JSON format", http.StatusBadRequest)
		return
	}

	log.Printf("📋 Processing task: %s - %s", task.ID, task.Title)

	// Run GraphRAG query
	graphRAGResponse, err := runGraphRAGQuery(task)
	if err != nil {
		log.Printf("❌ GraphRAG query failed: %v", err)
		http.Error(w, fmt.Sprintf("GraphRAG query failed: %v", err), http.StatusInternalServerError)
		return
	}

	// Update Firebase with selected members
	if err := updateFirebaseWithMembers(task.ID, graphRAGResponse); err != nil {
		log.Printf("❌ Firebase update failed: %v", err)
		http.Error(w, fmt.Sprintf("Firebase update failed: %v", err), http.StatusInternalServerError)
		return
	}

	// Return success response
	w.Header().Set("Content-Type", "application/json")
	response := map[string]interface{}{
		"success":                true,
		"task_id":                task.ID,
		"selected_members_count": len(graphRAGResponse.SelectedMembers),
		"confidence":             graphRAGResponse.Confidence,
		"reasoning":              graphRAGResponse.Reasoning,
	}

	if err := json.NewEncoder(w).Encode(response); err != nil {
		log.Printf("❌ Error encoding response: %v", err)
		http.Error(w, "Error encoding response", http.StatusInternalServerError)
		return
	}

	log.Printf("✅ Task %s processed successfully", task.ID)
}

func main() {
	log.Println("🚀 Starting GraphRAG Task Processing Endpoint...")

	// Initialize Firebase
	if err := initializeFirebase(); err != nil {
		log.Fatalf("❌ Failed to initialize Firebase: %v", err)
	}
	defer firestoreClient.Close()

	// Setup HTTP routes
	http.HandleFunc("/process-task", processTaskHandler)

	// Health check endpoint
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "OK")
	})

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "25565"
	}

	log.Printf("🌐 Server listening on port %s", port)
	log.Printf("📡 Endpoints available:")
	log.Printf("  POST /process-task - Process task with GraphRAG")
	log.Printf("  GET  /health       - Health check")

	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatalf("❌ Server failed to start: %v", err)
	}
}
