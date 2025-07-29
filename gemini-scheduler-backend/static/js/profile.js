document.addEventListener('DOMContentLoaded', function() {
    const profileForm = document.getElementById('profile-form');
    const userEmailDisplay = document.getElementById('user-email');
    const preferenceText = document.getElementById('preference_text');
    const minTime = document.getElementById('min_meeting_time');
    const maxTime = document.getElementById('max_meeting_time');

    let currentUser = null;

    auth.onAuthStateChanged(user => {
        if (user) {
            currentUser = user;
            userEmailDisplay.textContent = `Logged in as: ${user.email}`;
            fetchPreferences(user);
        } else {
            // If no user is logged in, redirect to login page.
            window.location.href = '/';
        }
    });

    const fetchPreferences = (user) => {
        user.getIdToken().then(token => {
            fetch('/api/preferences', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data) {
                    preferenceText.value = data.preference_text || '';
                    minTime.value = data.min_meeting_time || '09:00';
                    maxTime.value = data.max_meeting_time || '17:00';
                }
            })
            .catch(error => console.error('Error fetching preferences:', error));
        });
    };

    profileForm.addEventListener('submit', (event) => {
        event.preventDefault();
        if (!currentUser) {
            alert("You must be logged in to save preferences.");
            return;
        }

        const preferencesData = {
            preference_text: preferenceText.value,
            min_meeting_time: minTime.value,
            max_meeting_time: maxTime.value
        };

        currentUser.getIdToken().then(token => {
            fetch('/api/preferences', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(preferencesData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Preferences saved successfully!');
                } else {
                    alert('Error saving preferences: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error saving preferences:', error);
                alert('An error occurred while saving preferences.');
            });
        });
    });
});
