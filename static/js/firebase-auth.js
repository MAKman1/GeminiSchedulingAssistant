// This file will handle Firebase authentication logic.
// We will initialize Firebase here and handle sign-in/sign-out.

// Note: Firebase config will need to be added here from the user's Firebase project.
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_AUTH_DOMAIN",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_STORAGE_BUCKET",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

document.addEventListener('DOMContentLoaded', function() {
    const signInButton = document.getElementById('sign-in-with-google');
    const signOutButton = document.getElementById('sign-out-button');

    // Logic for sign-in
    if (signInButton) {
        signInButton.addEventListener('click', () => {
            const provider = new firebase.auth.GoogleAuthProvider();
            auth.signInWithPopup(provider)
                .then((result) => {
                    // This gives you a Google Access Token. You can use it to access the Google API.
                    const credential = result.credential;
                    const token = credential.accessToken;
                    // The signed-in user info.
                    const user = result.user;
                    console.log('User signed in:', user);
                    window.location.href = '/profile'; // Redirect to profile after sign-in
                }).catch((error) => {
                    console.error('Error during sign-in:', error);
                });
        });
    }

    // Logic for sign-out
    if (signOutButton) {
        signOutButton.addEventListener('click', () => {
            auth.signOut().then(() => {
                console.log('User signed out.');
                window.location.href = '/'; // Redirect to login page
            }).catch((error) => {
                console.error('Error during sign-out:', error);
            });
        });
    }

    // Listen for auth state changes
    auth.onAuthStateChanged((user) => {
        if (user) {
            // User is signed in.
            if (signOutButton) signOutButton.style.display = 'block';
            // If on login page, redirect away
            if (window.location.pathname === '/') {
                window.location.href = '/chat';
            }
        } else {
            // User is signed out.
            if (signOutButton) signOutButton.style.display = 'none';
            // If not on login page, redirect to login
            if (window.location.pathname !== '/') {
                window.location.href = '/';
            }
        }
    });
});
