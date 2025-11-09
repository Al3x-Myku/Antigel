# Firebase AI Recommendations Setup Guide

## Overview
This document describes the Firebase Firestore structure for the AI-powered task recommendation system.

## Database Structure

### Collection: `aiRecommendations`

This collection stores AI-generated task recommendations for users.

#### Document Structure
Each document represents a task recommendation for a specific user.

```javascript
{
  // Identifiers
  userId: string,              // Firebase UID of the user
  taskId: string,              // Reference to task document ID
  
  // Recommendation Metadata
  score: number,               // Match score (0.0 - 1.0)
  reason: string,              // Primary reason for recommendation
                               // Options: 'skills', 'interest', 'history', 'trending', 'community'
  
  // AI Analysis Data
  matchFactors: {
    skillMatch: number,        // 0.0 - 1.0
    interestMatch: number,     // 0.0 - 1.0
    experienceMatch: number,   // 0.0 - 1.0
    communityFit: number,      // 0.0 - 1.0
    rewardFit: number,         // 0.0 - 1.0
    availabilityMatch: number  // 0.0 - 1.0
  },
  
  // Context
  reasoning: string,           // AI-generated explanation (optional)
  tags: array<string>,         // Related tags/skills
  
  // Timestamps
  createdAt: timestamp,        // When recommendation was generated
  expiresAt: timestamp,        // When recommendation expires (optional)
  viewedAt: timestamp,         // When user viewed this recommendation (null if not viewed)
  clickedAt: timestamp,        // When user clicked on this recommendation (null if not clicked)
  
  // Status
  status: string,              // 'active', 'viewed', 'clicked', 'expired', 'dismissed'
  dismissed: boolean           // User manually dismissed this recommendation
}
```

#### Example Document
```javascript
// Document ID: auto-generated
{
  userId: "user123abc",
  taskId: "task456def",
  score: 0.87,
  reason: "skills",
  matchFactors: {
    skillMatch: 0.95,
    interestMatch: 0.82,
    experienceMatch: 0.88,
    communityFit: 0.75,
    rewardFit: 0.80,
    availabilityMatch: 0.90
  },
  reasoning: "This task matches your JavaScript and React skills, and you've completed similar tasks before.",
  tags: ["javascript", "react", "frontend"],
  createdAt: Timestamp(2025-11-09 10:30:00),
  expiresAt: Timestamp(2025-11-16 10:30:00),
  viewedAt: null,
  clickedAt: null,
  status: "active",
  dismissed: false
}
```

### Firestore Indexes Required

To efficiently query recommendations, create these composite indexes in Firebase Console:

```
Collection: aiRecommendations
Indexes:
1. userId (Ascending), score (Descending), createdAt (Descending)
2. userId (Ascending), status (Ascending), score (Descending)
3. taskId (Ascending), createdAt (Descending)
```

### Firestore Security Rules

Add these security rules to protect recommendation data:

```javascript
// Firestore Rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // AI Recommendations
    match /aiRecommendations/{recommendationId} {
      // Users can only read their own recommendations
      allow read: if request.auth != null && 
                  request.auth.uid == resource.data.userId;
      
      // Only server/cloud functions can write recommendations
      allow write: if false; // Use Cloud Functions or Admin SDK
      
      // Allow users to update status fields (viewed, clicked, dismissed)
      allow update: if request.auth != null && 
                    request.auth.uid == resource.data.userId &&
                    request.resource.data.diff(resource.data).affectedKeys()
                      .hasOnly(['viewedAt', 'clickedAt', 'status', 'dismissed']);
    }
  }
}
```

## Integration with Your AI Algorithm

### Step 1: Set Up Cloud Function or Backend Service

You'll need a backend service to run your AI algorithm. Options:

1. **Firebase Cloud Functions** (Recommended)
2. **Your Go Server** (testBlockchain.go)
3. **Python Microservice** (existing Python setup)

### Step 2: AI Algorithm Integration Points

Your AI algorithm should:

1. **Fetch User Profile Data**
   - User's completed tasks
   - User's skills and interests
   - User's joined communities
   - User's activity history

2. **Fetch Available Tasks**
   - Open tasks from joined communities
   - Tasks matching user skills
   - Trending tasks

3. **Calculate Recommendations**
   - Score each task based on multiple factors
   - Generate match factors breakdown
   - Determine primary reason for recommendation

4. **Store Recommendations in Firebase**
   - Create documents in `aiRecommendations` collection
   - Set expiration dates (e.g., 7 days)
   - Update existing recommendations if needed

### Step 3: Example AI Algorithm Flow (Pseudocode)

```python
def generate_recommendations_for_user(user_id):
    # 1. Get user profile
    user_profile = get_user_profile(user_id)
    user_skills = user_profile['skills']
    user_interests = user_profile['interests']
    completed_tasks = get_completed_tasks(user_id)
    
    # 2. Get candidate tasks
    available_tasks = get_available_tasks(user_id)
    
    # 3. Score each task
    recommendations = []
    for task in available_tasks:
        score = calculate_task_score(task, user_profile, completed_tasks)
        
        if score > 0.6:  # Threshold for recommendations
            recommendation = {
                'userId': user_id,
                'taskId': task['id'],
                'score': score,
                'reason': determine_primary_reason(task, user_profile),
                'matchFactors': calculate_match_factors(task, user_profile),
                'tags': extract_relevant_tags(task, user_skills),
                'reasoning': generate_explanation(task, user_profile, score),
                'createdAt': firestore.SERVER_TIMESTAMP,
                'expiresAt': firestore.SERVER_TIMESTAMP + timedelta(days=7),
                'status': 'active',
                'dismissed': False
            }
            recommendations.append(recommendation)
    
    # 4. Sort by score and limit to top recommendations
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    top_recommendations = recommendations[:10]
    
    # 5. Store in Firebase
    batch = db.batch()
    for rec in top_recommendations:
        doc_ref = db.collection('aiRecommendations').document()
        batch.set(doc_ref, rec)
    batch.commit()
    
    return top_recommendations

def calculate_task_score(task, user_profile, completed_tasks):
    """
    Calculate overall score for a task based on multiple factors
    """
    skill_match = calculate_skill_match(task['skills'], user_profile['skills'])
    interest_match = calculate_interest_match(task, user_profile['interests'])
    experience_match = calculate_experience_match(task, completed_tasks)
    community_fit = calculate_community_fit(task['communityId'], user_profile)
    reward_fit = calculate_reward_fit(task['reward'], user_profile)
    
    # Weighted average
    weights = {
        'skill': 0.30,
        'interest': 0.25,
        'experience': 0.20,
        'community': 0.15,
        'reward': 0.10
    }
    
    overall_score = (
        skill_match * weights['skill'] +
        interest_match * weights['interest'] +
        experience_match * weights['experience'] +
        community_fit * weights['community'] +
        reward_fit * weights['reward']
    )
    
    return overall_score
```

### Step 4: Triggering Recommendation Generation

**Option A: Scheduled (Batch Processing)**
- Run AI algorithm daily/weekly for all active users
- Use Cloud Scheduler + Cloud Functions
- Efficient for large user bases

**Option B: On-Demand (Real-time)**
- Generate recommendations when user visits dashboard
- Use Cloud Functions triggered by client request
- Better for small user bases or personalized experiences

**Option C: Event-Based**
- Trigger when user completes a task
- Trigger when new tasks are created
- Trigger when user joins a community

### Step 5: API Endpoint Example (Go Server)

Add this to your `testBlockchain.go`:

```go
// Get AI Recommendations for user
func getAIRecommendationsHandler(w http.ResponseWriter, r *http.Request) {
    if r.Method == http.MethodOptions {
        return
    }
    
    // Get user ID from query params
    userId := r.URL.Query().Get("userId")
    if userId == "" {
        writeError(w, "userId is required", http.StatusBadRequest)
        return
    }
    
    // Call your AI service or Python microservice
    recommendations, err := fetchAIRecommendations(userId)
    if err != nil {
        writeError(w, "Failed to fetch recommendations", http.StatusInternalServerError)
        return
    }
    
    writeSuccess(w, recommendations, "Recommendations fetched successfully")
}

// Register in main():
http.HandleFunc("/api/recommendations", getAIRecommendationsHandler)
```

## Frontend Integration (Already Done!)

The dashboard now includes:

✅ **UI Components**
- AI Recommended Tasks section with special styling
- Refresh button to reload recommendations
- Match percentage display
- Reason badges with color coding

✅ **JavaScript Functions**
- `loadAIRecommendedTasks(userId)` - Fetches and displays recommendations
- `createAIRecommendationCard()` - Renders recommendation cards
- Automatic loading on dashboard load
- Manual refresh capability

## Testing Your Setup

### 1. Manual Data Entry (Quick Test)

Use Firebase Console to manually create a test recommendation:

1. Go to Firestore Database
2. Create collection: `aiRecommendations`
3. Add document with this structure:

```javascript
{
  userId: "YOUR_TEST_USER_ID",
  taskId: "EXISTING_TASK_ID",
  score: 0.85,
  reason: "skills",
  matchFactors: {
    skillMatch: 0.90,
    interestMatch: 0.80,
    experienceMatch: 0.85,
    communityFit: 0.75,
    rewardFit: 0.80,
    availabilityMatch: 0.90
  },
  tags: ["test", "development"],
  reasoning: "Test recommendation",
  createdAt: [Click "Use server timestamp"],
  status: "active",
  dismissed: false
}
```

4. Reload your dashboard - you should see the recommendation!

### 2. Verify Queries Work

Check browser console for:
- ✅ Recommendations loaded successfully
- ❌ Any Firestore permission errors
- 📊 Query performance

## Next Steps

1. **Send me your AI algorithm code** - I'll help integrate it
2. **Choose integration method** - Cloud Function, Go server, or Python service
3. **Set up Firestore indexes** - Required for efficient queries
4. **Configure security rules** - Protect user data
5. **Test with real user data** - Validate recommendations quality

## Monitoring & Analytics

Track recommendation effectiveness:

```javascript
// Track when user clicks recommendation
async function trackRecommendationClick(recommendationId, taskId) {
  const recRef = doc(db, 'aiRecommendations', recommendationId);
  await updateDoc(recRef, {
    clickedAt: serverTimestamp(),
    status: 'clicked'
  });
  
  // Navigate to task
  window.location.href = `/task/${taskId}`;
}
```

## Maintenance

- **Clean up expired recommendations**: Run scheduled job to delete recommendations where `expiresAt < now()`
- **Update algorithm weights**: Based on user engagement metrics
- **A/B testing**: Test different recommendation strategies

---

**Ready to integrate your AI algorithm!** 🚀

Send me your algorithm code and I'll help you:
1. Connect it to Firebase
2. Set up the backend service
3. Optimize for performance
4. Add advanced features (collaborative filtering, deep learning, etc.)
