import os
import google.generativeai as genai
from datetime import datetime

# Import our other modules
from firestore_db import get_user_preferences
from google_calendar import get_free_busy_info

# --- Initialize the GenAI Client for Vertex AI ---
# The client is configured using environment variables.
# This block will execute when the Flask app starts.
try:
    if os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'False').lower() == 'true':
        # This is the configuration for Vertex AI
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('GOOGLE_CLOUD_LOCATION')
        genai.configure(
            project=project_id,
            location=location,
        )
        print("GenAI client configured for Vertex AI.")
    else:
        # Fallback or default configuration if not using Vertex AI
        # For example, using Google AI Studio API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            print("GenAI client configured for Google AI Studio.")
        else:
            print("GenAI client not configured. Set GOOGLE_GENAI_USE_VERTEXAI or GOOGLE_API_KEY.")

except Exception as e:
    print(f"CRITICAL: GenAI client failed to initialize. Environment variables may be missing: {e}")


# --- Define the Python function that will be used as a tool ---
def get_comprehensive_attendee_data(attendees: list[str], start_date: str, end_date: str, user_to_impersonate: str) -> dict:
    """
    Fetches calendar availability and user-stated scheduling preferences for a list of attendees
    to find the best time for a meeting.

    Args:
        attendees: A list of attendee email addresses.
        start_date: The start date for the search window in YYYY-MM-DD format.
        end_date: The end date for the search window in YYYY-MM-DD format.
        user_to_impersonate: The email address of the user making the request, used for calendar authentication.
    """
    print(f"--- Tool Called: get_comprehensive_attendee_data with args: {locals()} ---")

    # 1. Get user preferences from Firestore
    preferences = get_user_preferences(attendees)

    # 2. Get free/busy information from Google Calendar
    # The API expects RFC3339 format, so we append time and timezone info.
    start_time_iso = f"{start_date}T00:00:00Z"
    end_time_iso = f"{end_date}T23:59:59Z"

    busy_slots = get_free_busy_info(
        attendee_emails=attendees,
        start_time_str=start_time_iso,
        end_time_str=end_time_iso,
        user_to_impersonate=user_to_impersonate
    )

    # 3. Consolidate results into a single dictionary
    consolidated_data = {
        "attendees": attendees,
        "preferences": preferences,
        "busy_slots": busy_slots
    }

    print(f"--- Tool Data Consolidated ---")
    return consolidated_data


# --- Main Agent Logic ---
def run_orchestrator_agent(session: dict) -> str:
    """
    Runs the main agent logic using automatic function calling.
    """
    conversation_history = session.get('conversation_history', [])

    # Determine the user making the request to impersonate for API calls.
    # Assumption: The first attendee in the original request is the user.
    try:
        user_to_impersonate = session['original_request_details']['attendees'][0]
    except (KeyError, IndexError, TypeError):
        return "Error: Cannot determine the user making the request. The 'original_request_details' must contain a list of 'attendees'."

    # Guide the model with a system prompt.
    system_prompt = f"""
You are a helpful scheduling assistant. Your goal is to find a suitable meeting time for a list of attendees.
- Today's date is {datetime.utcnow().strftime('%Y-%m-%d')}.
- The user you are acting on behalf of is {user_to_impersonate}. You MUST pass their email to the `user_to_impersonate` argument for any tool calls.
- Use the `get_comprehensive_attendee_data` tool to get all necessary information. Do not ask for information you can get from the tool.
- Infer date ranges from user requests (e.g., "next week," "tomorrow").
- After getting tool data, analyze everything (busy slots, preferences) and propose 2-3 specific meeting slots.
- If no slots are available, inform the user and ask for alternative times.
"""

    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash-001',
        system_instruction=system_prompt,
        tools=[get_comprehensive_attendee_data]
    )

    # Use the existing conversation history to continue the chat
    chat = model.start_chat(history=conversation_history)
    latest_user_message = conversation_history[-1]['content']

    # The send_message method automatically handles the tool-calling loop
    response = chat.send_message(latest_user_message)

    return response.text
