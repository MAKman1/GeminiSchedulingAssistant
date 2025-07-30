import os
import json
import logging
from google import genai
from datetime import datetime
from google.genai import types

# Import our other modules
from firestore_db import get_user_preferences, add_event_to_session
from google_calendar import get_free_busy_info, create_calendar_event, reschedule_calendar_event

# --- Initialize the GenAI Client for Vertex AI ---
# The client is configured using environment variables.
# This block will execute when the Flask app starts.
client = None
try:
    if os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'False').lower() == 'true':
        # This is the configuration for Vertex AI
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('GOOGLE_CLOUD_LOCATION')
        client = genai.Client(vertexai=True, project=project_id, location=location)
        logging.info("GenAI client configured for Vertex AI.")
    else:
        # Fallback or default configuration if not using Vertex AI
        # For example, using Google AI Studio API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
            logging.info("GenAI client configured for Google AI Studio.")
        else:
            logging.warning("GenAI client not configured. Set GOOGLE_GENAI_USE_VERTEXAI or GOOGLE_API_KEY.")

except Exception as e:
    logging.critical(f"GenAI client failed to initialize. Environment variables may be missing: {e}")


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
    logging.info(f"--- Tool Called: get_comprehensive_attendee_data with args: {locals()} ---")

    # 1. Get user preferences from Firestore
    preferences = get_user_preferences(attendees)

    # 2. Get free/busy information from Google Calendar
    # The API expects RFC3339 format, so we append time and timezone info.
    start_time_iso = f"{start_date}T00:00:00Z"
    end_time_iso = f"{end_date}T23:59:59Z"

    free_busy_data = get_free_busy_info(
        attendee_emails=attendees,
        start_time_str=start_time_iso,
        end_time_str=end_time_iso,
        user_to_impersonate=user_to_impersonate
    )

    # 3. Consolidate results into a single dictionary
    for attendee in free_busy_data["internal_attendees"]:
        attendee["preference_rule"] = preferences.get(attendee["email"], {}).get("preference_text", "")

    logging.info(f"--- Tool Data Consolidated ---")
    return free_busy_data


# --- Main Agent Logic ---
def run_orchestrator_agent(session: dict) -> dict:
    """
    Runs the main agent logic using automatic function calling.
    Returns a dictionary containing the response text and debug information.
    """
    conversation_history = session.get('conversation_history', [])
    user_to_impersonate = os.getenv("AGENT_EMAIL")
    session_id = session.get("sessionId")

    # Extract event info for the prompt, ensuring it's not in the past
    events_for_prompt = []
    for event in session.get("events", []):
        try:
            end_time = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
            if end_time > datetime.now(end_time.tzinfo):
                events_for_prompt.append({
                    "id": event.get("id"),
                    "summary": event.get("summary"),
                    "start": event.get("start", {}).get("dateTime"),
                    "end": event.get("end", {}).get("dateTime"),
                })
        except (KeyError, TypeError):
            continue # Skip malformed events

    system_prompt = f"""
You are a helpful scheduling assistant. Your goal is to find a suitable meeting time for a list of attendees, or reschedule an existing meeting.
Your workflow should be as follows:
1.  When the user asks for availability, use the `get_comprehensive_attendee_data` tool to get the necessary information.
2.  Analyze the data and propose 2-3 specific meeting slots to the user.
3.  Wait for the user to confirm a time.
4.  Once the user confirms a time, use the `create_calendar_event` tool to book the meeting.
5.  If the user asks to reschedule an event, use the `reschedule_calendar_event` tool. You must have the `event_id` from the list of scheduled events below.

- Today's date is {datetime.utcnow().strftime('%Y-%m-%d (%A)')}.
- The current timezone is UK time.
- Your identity is {user_to_impersonate}. All messages from this email are from you.
- The user you are acting on behalf of is {user_to_impersonate}. You MUST pass their email to the `user_to_impersonate` argument for any tool calls.
- The user's message will be an excerpt from an email thread. Prioritize the last message in the thread, but use the previous messages for context.
- You have been provided with a list of attendees: {json.dumps(session['original_request_details']['attendees'])}. Use this list to check for availability.
- Here is a list of previously scheduled events in this session that can be rescheduled: {json.dumps(events_for_prompt)}
- After successfully creating an event using the `create_calendar_event` tool, your confirmation message to the user **must** include the `htmlLink` from the tool's output.
- When proposing a time, first look for slots where all attendees are free.
- If no completely free slots are available, you may propose a time that overlaps with a "soft block" (e.g., "focus time", "deep work", or a meeting with only 1 attendee).
- If you propose a time that overlaps with a soft block, you **must** mention it in your response and ask if it's okay to book over it (e.g., "I found a slot at 2pm, but I see you have 'focus time' scheduled. Would it be okay to book over that?").
- Do not ask for the attendees' email addresses as they have already been provided.
- Do not engage in conversational chit-chat. Be direct and helpful.
"""

    if not client:
        return {"text": "Error: GenAI client not initialized.", "debug_info": {}}

    # Convert the conversation history to the format expected by the SDK
    formatted_history = [
        types.Content(role=msg['role'], parts=[types.Part.from_text(text=msg['content'])])
        for msg in conversation_history
    ]

    logging.info("--- Sending request to GenAI ---")
    logging.info(f"System prompt: {system_prompt}")
    logging.info(f"Conversation history: {formatted_history}")

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=formatted_history,
        config=types.GenerateContentConfig(
            tools=[get_comprehensive_attendee_data, create_calendar_event, reschedule_calendar_event],
            system_instruction=system_prompt
        )
    )

    logging.info(f"--- Received response from GenAI: {response} ---")

    tool_calls = []
    tool_responses = []
    if response and response.automatic_function_calling_history:
        for content in response.automatic_function_calling_history:
            if content.role == 'model':
                for part in content.parts:
                    if part.function_call:
                        tool_calls.append({
                            "function_name": part.function_call.name,
                            "args": dict(part.function_call.args),
                        })
            if content.role == 'user':
                for part in content.parts:
                    if part.function_response:
                        # If a meeting was created, add it to the session
                        if part.function_response.name == "create_calendar_event":
                            event_data = dict(part.function_response.response)
                            if session_id and event_data:
                                add_event_to_session(session_id, event_data)
                        tool_responses.append({
                            "function_name": part.function_response.name,
                            "response": dict(part.function_response.response),
                        })

    debug_info = {
        "system_prompt": system_prompt,
        "conversation_history": [
            {"role": msg.role, "parts": [part.text for part in msg.parts]}
            for msg in formatted_history
        ],
        "tool_calls": tool_calls,
        "tool_responses": tool_responses,
        "full_response": str(response),
    }

    return {
        "text": response.text,
        "debug_info": debug_info
    }
