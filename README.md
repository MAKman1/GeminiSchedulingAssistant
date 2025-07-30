# Gemini Scheduling Assistant

This is a Flask-based web application that acts as an AI-powered scheduling assistant. It uses the Google Gemini family of models via Vertex AI to understand natural language requests, find available meeting slots by checking Google Calendars, and suggest times, all through a conversational chat interface.

## Features

- **Conversational Interface**: Schedule meetings using natural language in a chat-based UI.
- **Google Calendar Integration**: Automatically checks the calendars of specified attendees for free/busy times.
- **User Preferences**: Users can set custom preferences, such as "don't book meetings on Friday afternoons," which the AI will consider.
- **Firebase Authentication**: Secure login using a "Sign in with Google" flow, ensuring only authorized users can access the application.
- **Persistent Chat Sessions**: View and continue previous scheduling conversations.

---

## Prerequisites

Before you begin, ensure you have the following:

1.  **Python 3.8+**: [Installation Guide](https://www.python.org/downloads/)
2.  **Google Cloud Project**:
    *   A Google Cloud account with an active project.
    *   The **Vertex AI API**, **Firestore API**, and **Google Calendar API** must be enabled for your project.
3.  **Firebase Project**:
    *   A Firebase project linked to your Google Cloud project.
    *   **Google Authentication** enabled as a sign-in method.
4.  **Service Account**:
    *   A service account created in your Google Cloud project.
    *   This service account needs roles/permissions for Vertex AI, Firestore, and Google Calendar.
    *   Crucially, you must grant it **domain-wide delegation** for the Google Calendar scope (`https://www.googleapis.com/auth/calendar`).
    *   You must have its JSON key file.

---

## Setup and Installation

Follow these steps to get the application running locally.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Set up a Python Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
# venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate
```

### 3. Install Dependencies

Install all the required Python packages.

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root of the project by copying the example file.

```bash
cp .env.example .env
```

Now, edit the `.env` file with your specific project details:

```
FLASK_APP=app.py
FLASK_DEBUG=True

# --- Google GenAI SDK for Vertex AI ---
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT=your-gcp-project-id  # <-- REPLACE THIS
GOOGLE_CLOUD_LOCATION=your-gcp-region     # <-- REPLACE THIS (e.g., us-central1)

# --- Service Account for other Google Cloud APIs ---
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
```

### 5. Add Your Service Account Key

Place your downloaded service account JSON key file in the root of the project and rename it to `service-account.json`.

### 6. Configure Firebase for the Frontend

Open the `static/js/firebase-auth.js` file. You will see a `firebaseConfig` object with placeholder values. Replace these with the actual configuration values from your Firebase project's web app settings.

You can find this configuration in the Firebase console:
*Project Settings* > *General* > *Your apps* > *Web app* > *SDK setup and configuration*.

```javascript
// static/js/firebase-auth.js

const firebaseConfig = {
  apiKey: "YOUR_API_KEY", // <-- REPLACE
  authDomain: "YOUR_AUTH_DOMAIN", // <-- REPLACE
  projectId: "YOUR_PROJECT_ID", // <-- REPLACE
  storageBucket: "YOUR_STORAGE_BUCKET", // <-- REPLACE
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID", // <-- REPLACE
  appId: "YOUR_APP_ID" // <-- REPLACE
};
```

### 7. Create Firestore Index

The application queries the `sessions` collection by `user_email` and orders by `last_updated`. Firestore requires a composite index for this.

The first time you run the app and try to view the chat page, the Flask server will log an error message that contains a direct link to create this index in the Google Cloud Console. Click the link, confirm the creation, and wait a few minutes for the index to build. This is a one-time setup step.

---

## Running the Application

Once all the setup steps are complete, you can run the Flask development server.

```bash
flask run
```

Navigate to `http://127.0.0.1:5000` in your web browser. You should be greeted with the login page.

---

## Project Structure

```
.
├── app.py                  # Main Flask application, API endpoints, and frontend routes
├── agents.py               # Core logic for the AI agent and its tools
├── google_calendar.py      # Handles all Google Calendar API interactions
├── firestore_db.py         # Handles all Firestore database interactions
├── utils.py                # Helper functions (e.g., authentication decorator)
│
├── templates/              # HTML files for the frontend
│   ├── base.html
│   ├── login.html
│   ├── profile.html
│   └── chat.html
│
├── static/                 # CSS and JavaScript files
│   ├── css/style.css
│   └── js/
│       ├── firebase-auth.js
│       ├── profile.js
│       └── chat.js
│
├── requirements.txt        # Python dependencies
├── .env.example            # Template for environment variables
├── service-account.json    # (You must provide this) Google Cloud service account key
└── README.md               # This file
```
