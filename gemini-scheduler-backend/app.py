import os
import datetime
from flask import Flask, request, jsonify, render_template, g
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials

# Load environment variables from .env file at the very start
load_dotenv()

# Initialize Firebase Admin SDK
# The service account key is specified in the GOOGLE_APPLICATION_CREDENTIALS env var
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred)

# Now import custom modules that rely on the loaded environment variables
from firestore_db import get_or_create_session, update_session, get_user_preferences, update_user_preferences, get_sessions_for_user
from agents import run_orchestrator_agent
from utils import token_required

app = Flask(__name__)

@app.route('/api/preferences', methods=['GET'])
@token_required
def get_preferences_route():
    """
    Endpoint to get the authenticated user's preferences.
    """
    user_email = g.current_user['email']
    try:
        preferences = get_user_preferences([user_email]).get(user_email, {})
        return jsonify(preferences)
    except Exception as e:
        print(f"Error getting preferences: {e}")
        return jsonify({"error": "Failed to get preferences."}), 500

@app.route('/api/preferences', methods=['POST'])
@token_required
def update_preferences_route():
    """
    Endpoint to update the authenticated user's preferences.
    """
    user_email = g.current_user['email']
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    preferences_data = {
        "preference_text": data.get("preference_text", ""),
        "min_meeting_time": data.get("min_meeting_time", "09:00"),
        "max_meeting_time": data.get("max_meeting_time", "17:00"),
    }

    try:
        update_user_preferences(user_email, preferences_data)
        return jsonify({"success": True, "message": "Preferences updated."})
    except Exception as e:
        print(f"Error updating preferences: {e}")
        return jsonify({"error": "Failed to update preferences."}), 500

@app.route('/api/sessions', methods=['GET'])
@token_required
def get_sessions_route():
    """
    Endpoint to get all sessions for the authenticated user.
    """
    user_email = g.current_user['email']
    try:
        sessions = get_sessions_for_user(user_email)
        # We can simplify the data returned to the list view
        session_previews = [
            {
                "sessionId": s.get("sessionId"),
                "title": s.get("original_request_details", {}).get("meeting_title", "Untitled Chat"),
                "last_updated": s.get("last_updated")
            } for s in sessions
        ]
        return jsonify(session_previews)
    except Exception as e:
        print(f"Error getting sessions: {e}")
        return jsonify({"error": "Failed to get sessions."}), 500

@app.route('/api/sessions/<session_id>', methods=['GET'])
@token_required
def get_single_session_route(session_id):
    """
    Endpoint to get the full details of a single session.
    """
    user_email = g.current_user['email']
    try:
        session = get_or_create_session(session_id=session_id)
        # Security check: ensure the session belongs to the authenticated user
        if not session or session.get('user_email') != user_email:
            return jsonify({"error": "Session not found or access denied."}), 404
        return jsonify(session)
    except Exception as e:
        print(f"Error getting single session: {e}")
        return jsonify({"error": "Failed to get session details."}), 500

@app.route('/api/chat', methods=['POST'])
@token_required
def chat():
    """
    Main chat endpoint to handle the conversation with the scheduling agent.
    """
    # 1. Get data from the request body
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    session_id = data.get('sessionId')
    user_message = data.get('message')

    if not user_message:
        return jsonify({"error": "The 'message' field is required."}), 400

    # 2. Retrieve the session from Firestore or create a new one
    session = get_or_create_session(session_id=session_id, user_email=g.current_user['email'])

    # 3. If this is the first message of a new session, store original request details
    is_new_conversation = not session_id or not session.get('conversation_history')
    if is_new_conversation:
        attendees_csv = data.get('attendees_csv')
        if not attendees_csv:
            return jsonify({"error": "The 'attendees_csv' field is required for a new chat."}), 400

        # Parse the CSV string and add the current user's email
        attendees = [email.strip() for email in attendees_csv.split(',') if email.strip()]
        user_email = g.current_user['email']
        if user_email not in attendees:
            attendees.insert(0, user_email)

        initial_details = {
            "attendees": attendees,
            "duration_minutes": data.get("duration_minutes"),
            "meeting_title": data.get("meeting_title")
        }

        session['original_request_details'] = initial_details
        session['status'] = 'AWAITING_INPUT'

    # 4. Append the user's message to the conversation history
    # The roles 'user' and 'model' are used to match the Gemini API's expected format.
    user_message_entry = {"role": "user", "content": user_message}
    session.setdefault('conversation_history', []).append(user_message_entry)

    # 5. Call the orchestrator agent to get the AI's response
    try:
        assistant_response_text = run_orchestrator_agent(session)
        session['status'] = 'AWAITING_CONFIRMATION' # Assume agent is proposing slots
    except Exception as e:
        print(f"ERROR: An exception occurred in the agent: {e}")
        assistant_response_text = "I'm sorry, I encountered an internal error and couldn't process your request. Please try again later."
        session['status'] = 'FAILED'

    # 6. Append the assistant's response to the history
    assistant_message_entry = {"role": "model", "content": assistant_response_text}
    session['conversation_history'].append(assistant_message_entry)

    # 7. Update the entire session state in Firestore
    update_data = {
        "conversation_history": session['conversation_history'],
        "status": session['status'],
        "original_request_details": session['original_request_details']
    }
    update_session(session['sessionId'], update_data)

    # 8. Return the agent's response and session ID to the client
    return jsonify({
        "sessionId": session['sessionId'],
        "response": assistant_response_text
    })

# ++++++++++ Frontend Routes ++++++++++

@app.route('/')
def login_route():
    """Renders the login page."""
    return render_template('login.html')

@app.route('/profile')
def profile_route():
    """Renders the profile page."""
    # TODO: Add a check to ensure the user is authenticated
    return render_template('profile.html')

@app.route('/chat')
def chat_route():
    """Renders the chat page."""
    # TODO: Add a check to ensure the user is authenticated
    return render_template('chat.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
