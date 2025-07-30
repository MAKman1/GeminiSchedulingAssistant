import uuid
from google.cloud import firestore

# Initialize the Firestore client
db = firestore.Client()

SESSIONS_COLLECTION = "sessions"
PREFERENCES_COLLECTION = "user_preferences"

def get_or_create_session(session_id: str = None, user_email: str = None) -> dict:
    """
    Retrieves an existing session from Firestore or creates a new one.
    If a new session is created, it must be associated with a user.

    Args:
        session_id: The ID of the session to retrieve. If None, a new session is created.
        user_email: The email of the user creating the session. Required for new sessions.

    Returns:
        A dictionary representing the session data.
    """
    if session_id:
        session_ref = db.collection(SESSIONS_COLLECTION).document(session_id)
        session_doc = session_ref.get()
        if session_doc.exists:
            return session_doc.to_dict()

    if not user_email:
        raise ValueError("user_email is required to create a new session.")

    session_data = {
        "sessionId": session_id,
        "user_email": user_email, # Associate session with the user
        "status": "AWAITING_INPUT",
        "last_updated": firestore.SERVER_TIMESTAMP,
        "original_request_details": {},
        "conversation_history": [],
        "suggested_slots": [],
        "events": [] # New field to store scheduled events
    }
    db.collection(SESSIONS_COLLECTION).document(session_id).set(session_data)
    return session_data

def get_sessions_for_user(user_email: str) -> list[dict]:
    """
    Fetches all sessions for a specific user, ordered by most recent.

    Args:
        user_email: The email of the user whose sessions to fetch.

    Returns:
        A list of session dictionaries.
    """
    sessions_query = db.collection(SESSIONS_COLLECTION).where("user_email", "==", user_email).order_by("last_updated", direction=firestore.Query.DESCENDING)
    sessions = [doc.to_dict() for doc in sessions_query.stream()]
    return sessions

def update_session(session_id: str, data_to_update: dict):
    """
    Updates a session document in Firestore.

    Args:
        session_id: The ID of the session to update.
        data_to_update: A dictionary containing the fields to update.
    """
    session_ref = db.collection(SESSIONS_COLLECTION).document(session_id)
    data_to_update['last_updated'] = firestore.SERVER_TIMESTAMP
    session_ref.update(data_to_update)
    print(f"Session {session_id} updated.")

def add_event_to_session(session_id: str, event_data: dict):
    """
    Adds a created event to the session's event list.

    Args:
        session_id: The ID of the session to update.
        event_data: A dictionary containing the event details from the Calendar API.
    """
    session_ref = db.collection(SESSIONS_COLLECTION).document(session_id)
    update_data = {
        "events": firestore.ArrayUnion([event_data]),
        "last_updated": firestore.SERVER_TIMESTAMP
    }
    session_ref.update(update_data)
    print(f"Event added to session {session_id}.")

def get_user_preferences(list_of_emails: list) -> dict:
    """
    Fetches user preferences for a list of email addresses.

    Args:
        list_of_emails: A list of user email addresses.

    Returns:
        A dictionary where keys are email addresses and values are their preferences document.
    """
    if not list_of_emails:
        return {}

    preferences = {}
    # Use a 'in' query to fetch multiple documents by email.
    # Firestore 'in' queries are limited to 10 items per query.
    # For a more robust solution, we would chunk the list_of_emails.
    # For this implementation, we assume the list is small.
    docs = db.collection(PREFERENCES_COLLECTION).where("email", "in", list_of_emails).stream()

    for doc in docs:
        data = doc.to_dict()
        if 'email' in data:
            preferences[data['email']] = data # Return the whole document

    return preferences

def update_user_preferences(email: str, preferences_data: dict):
    """
    Creates or updates a user's preferences document in Firestore.

    Args:
        email: The user's email, used as the document ID.
        preferences_data: A dictionary of preferences to set.
    """
    # Ensure the email is part of the data being written
    preferences_data['email'] = email

    pref_ref = db.collection(PREFERENCES_COLLECTION).document(email)
    # Use set with merge=True to create or update the document without overwriting
    pref_ref.set(preferences_data, merge=True)
    print(f"Preferences for {email} updated.")
