# Community Fixes Implementation Guide

## Summary of Required Changes

You need the following fixes for the community system:

### 1. ✅ UI Fixed - Reduced Banner Height
- Changed banner from aspect-[21/9] (huge) to h-48 (compact)
- Reduced heading size and padding
- Made layout compact to avoid scrolling

### 2. 🔨 TODO: Add Members Section

Add this HTML after the Stats Bar section in community.html (around line 120):

```html
<!-- Members Section -->
<div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
        <h2 class="text-cream text-2xl font-bold">Members</h2>
        <span id="totalMembers" class="text-text-muted-dark text-sm">0 members</span>
    </div>
    <div id="membersContainer" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Members will be loaded here -->
        <div class="text-center py-8 col-span-full">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
            <p class="text-text-muted-dark text-sm">Loading members...</p>
        </div>
    </div>
</div>
```

### 3. 🔨 TODO: Add Leave & Delete Buttons JavaScript

Add these buttons to the hero section (they're already added in HTML at lines 96-106).

Now add the JavaScript handlers at the end of the script section:

```javascript
// Leave Community
document.getElementById('leaveCommunityBtn')?.addEventListener('click', () => {
    document.getElementById('leaveModal').classList.remove('hidden');
});

document.getElementById('confirmLeaveBtn')?.addEventListener('click', async () => {
    if (!currentCommunityId || !currentUser) return;
    
    try {
        const communityRef = doc(db, 'communities', currentCommunityId);
        const userRef = doc(db, 'users', currentUser.uid);
        
        // Remove user from community members
        await updateDoc(communityRef, {
            members: arrayRemove(currentUser.uid),
            memberCount: increment(-1)
        });
        
        // Remove community from user's joined communities
        await updateDoc(userRef, {
            joinedCommunities: arrayRemove(currentCommunityId)
        });
        
        alert('You have left the community');
        window.location.href = '/my-communities';
    } catch (error) {
        console.error('Error leaving community:', error);
        alert('Error leaving community');
    }
});

// Delete Community (Admin Only)
document.getElementById('deleteCommunityBtn')?.addEventListener('click', () => {
    document.getElementById('deleteModal').classList.remove('hidden');
});

document.getElementById('confirmDeleteBtn')?.addEventListener('click', async () => {
    if (!currentCommunityId || !currentUser) return;
    
    const confirmText = document.getElementById('deleteConfirmInput').value;
    if (confirmText !== 'DELETE') {
        alert('Please type DELETE to confirm');
        return;
    }
    
    try {
        // Delete the community document
        await deleteDoc(doc(db, 'communities', currentCommunityId));
        
        alert('Community deleted successfully');
        window.location.href = '/my-communities';
    } catch (error) {
        console.error('Error deleting community:', error);
        alert('Error deleting community');
    }
});
```

### 4. 🔨 TODO: Add Modal HTML

Add these modals before the closing </body> tag:

```html
<!-- Leave Community Modal -->
<div id="leaveModal" class="hidden fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
    <div class="bg-card-dark border-2 border-red-500/50 rounded-2xl p-8 max-w-md w-full mx-4">
        <div class="flex items-center gap-4 mb-6">
            <div class="flex items-center justify-center size-12 rounded-full bg-red-500/20">
                <span class="material-symbols-outlined text-red-400 text-3xl">logout</span>
            </div>
            <h3 class="text-cream text-2xl font-bold">Leave Community?</h3>
        </div>
        <p class="text-text-muted-dark text-base mb-8">
            Are you sure you want to leave this community? You'll lose access to all tasks and discussions.
        </p>
        <div class="flex gap-4">
            <button onclick="document.getElementById('leaveModal').classList.add('hidden')" 
                    class="flex-1 px-6 py-3 rounded-xl bg-card-dark border-2 border-border-dark text-cream font-bold hover:border-primary/50 transition-colors">
                Cancel
            </button>
            <button id="confirmLeaveBtn" 
                    class="flex-1 px-6 py-3 rounded-xl bg-red-500 text-white font-bold hover:bg-red-600 transition-colors">
                Leave Community
            </button>
        </div>
    </div>
</div>

<!-- Delete Community Modal -->
<div id="deleteModal" class="hidden fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
    <div class="bg-card-dark border-2 border-red-600 rounded-2xl p-8 max-w-md w-full mx-4">
        <div class="flex items-center gap-4 mb-6">
            <div class="flex items-center justify-center size-12 rounded-full bg-red-600/20">
                <span class="material-symbols-outlined text-red-500 text-3xl">delete_forever</span>
            </div>
            <h3 class="text-cream text-2xl font-bold">Delete Community?</h3>
        </div>
        <p class="text-text-muted-dark text-base mb-4">
            ⚠️ This action is <span class="text-red-500 font-bold">PERMANENT</span> and cannot be undone!
        </p>
        <p class="text-text-muted-dark text-sm mb-6">
            All tasks, members, and data will be permanently deleted. Type <strong class="text-cream">DELETE</strong> to confirm:
        </p>
        <input type="text" id="deleteConfirmInput" 
               class="w-full bg-background-dark border-2 border-red-500 rounded-lg px-4 py-3 text-cream mb-6 outline-none focus:border-red-400" 
               placeholder="Type DELETE">
        <div class="flex gap-4">
            <button onclick="document.getElementById('deleteModal').classList.add('hidden')" 
                    class="flex-1 px-6 py-3 rounded-xl bg-card-dark border-2 border-border-dark text-cream font-bold hover:border-primary/50 transition-colors">
                Cancel
            </button>
            <button id="confirmDeleteBtn" 
                    class="flex-1 px-6 py-3 rounded-xl bg-red-600 text-white font-bold hover:bg-red-700 transition-colors">
                Delete Forever
            </button>
        </div>
    </div>
</div>
```

### 5. 🔨 TODO: Hide Invite-Only Communities

In communities.html, find the `displayCommunities` function and update it to filter out invite-only:

```javascript
function displayCommunities(communities) {
    const container = document.getElementById('communitiesContainer');
    container.innerHTML = '';

    // Filter out invite-only communities
    const visibleCommunities = communities.filter(community => 
        community.accessType !== 'invite'
    );

    if (visibleCommunities.length === 0) {
        container.innerHTML = `
            <div class="col-span-full text-center py-12">
                <span class="material-symbols-outlined text-6xl text-text-muted-dark mb-4">groups_off</span>
                <p class="text-text-muted-dark">No communities available to join</p>
            </div>
        `;
        return;
    }

    visibleCommunities.forEach(community => {
        const card = createCommunityCard(community);
        container.appendChild(card);
    });
}
```

### 6. 🔨 TODO: Load Members Function

Add this function in community.html script section:

```javascript
async function loadCommunityMembers(memberIds) {
    const container = document.getElementById('membersContainer');
    document.getElementById('totalMembers').textContent = `${memberIds.length} members`;
    
    if (memberIds.length === 0) {
        container.innerHTML = '<p class="text-text-muted-dark text-center py-4 col-span-full">No members yet</p>';
        return;
    }
    
    container.innerHTML = '';
    
    for (const memberId of memberIds) {
        try {
            const userRef = doc(db, 'users', memberId);
            const userSnap = await getDoc(userRef);
            
            if (!userSnap.exists()) continue;
            
            const userData = userSnap.data();
            const isAdmin = communityData.admins && communityData.admins.includes(memberId);
            
            const memberCard = document.createElement('div');
            memberCard.className = 'flex items-center gap-3 p-4 rounded-lg bg-background-dark border border-border-dark hover:border-primary/30 transition-colors';
            
            memberCard.innerHTML = `
                <div class="size-10 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                    <span class="text-primary font-bold">${(userData.displayName || userData.email || 'U')[0].toUpperCase()}</span>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-cream font-semibold truncate">${userData.displayName || userData.email || 'User'}</p>
                    <p class="text-text-muted-dark text-xs">${userData.tasksCompleted || 0} tasks completed</p>
                </div>
                ${isAdmin ? '<span class="text-xs px-2 py-1 rounded-full bg-primary/20 text-primary font-semibold flex-shrink-0">Admin</span>' : ''}
            `;
            
            container.appendChild(memberCard);
        } catch (error) {
            console.error('Error loading member:', memberId, error);
        }
    }
}
```

Then call it after loading community data:
```javascript
await loadCommunityMembers(communityData.members || []);
```

### 7. Show buttons based on user role

Update the community loading function to show/hide buttons:

```javascript
// Show leave button for all members
if (isMember) {
    document.getElementById('leaveCommunityBtn').classList.remove('hidden');
}

// Show admin buttons only for admins
if (isAdmin) {
    document.getElementById('adminSettingsBtn').classList.remove('hidden');
    document.getElementById('deleteCommunityBtn').classList.remove('hidden');
}
```

## Next Steps

After implementing these UI fixes, we need to:
1. Integrate blockchain task display (requires connecting to your deployed contracts)
2. Ensure dashboard only shows assigned tasks
3. Ensure community page shows all tasks from that community

Would you like me to implement any of these changes directly in the files, or provide more specific code for the blockchain integration?
