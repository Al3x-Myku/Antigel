// Shared Authentication Module
import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-app.js';
import { 
    getAuth, 
    onAuthStateChanged,
    setPersistence,
    browserLocalPersistence
} from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-auth.js';

// Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyCBV3CuuYD_8w843LgPQqAICGnmvDtOt5k",
    authDomain: "taskmatch-openhack2025.firebaseapp.com",
    projectId: "taskmatch-openhack2025",
    storageBucket: "taskmatch-openhack2025.firebasestorage.app",
    messagingSenderId: "248164216629",
    appId: "1:248164216629:web:16b5982c9a7beae2b5a67c",
    measurementId: "G-WWN061CS59"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Enable persistence
setPersistence(auth, browserLocalPersistence).catch((error) => {
    console.error('Failed to enable persistence:', error);
});

// Check if user is logged in
export function requireAuth(redirectTo = '/login') {
    return new Promise((resolve, reject) => {
        onAuthStateChanged(auth, (user) => {
            if (user) {
                console.log('✅ User is logged in:', user.email);
                resolve(user);
            } else {
                console.log('❌ No user, redirecting to:', redirectTo);
                window.location.href = redirectTo;
                reject('Not authenticated');
            }
        });
    });
}

// Check if user is NOT logged in (for login/register pages)
export function requireGuest(redirectTo = '/dashboard') {
    return new Promise((resolve) => {
        onAuthStateChanged(auth, (user) => {
            if (user) {
                console.log('✅ User already logged in, redirecting to:', redirectTo);
                window.location.href = redirectTo;
            } else {
                console.log('✅ Guest access granted');
                resolve();
            }
        });
    });
}

// Get current user
export function getCurrentUser() {
    return new Promise((resolve) => {
        onAuthStateChanged(auth, (user) => {
            resolve(user);
        });
    });
}

// Logout
export async function logout() {
    try {
        await auth.signOut();
        console.log('✅ Logged out successfully');
        window.location.href = '/login';
    } catch (error) {
        console.error('❌ Logout failed:', error);
    }
}

export { auth, app };
