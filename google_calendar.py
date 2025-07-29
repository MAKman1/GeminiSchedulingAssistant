import os
from datetime import datetime, timedelta
import google.oauth2.service_account
import googleapiclient.discovery

# Scopes required for the Google Calendar API
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']

def _get_calendar_service(user_to_impersonate: str):
    """Creates and returns a Google Calendar service object impersonating a user."""

    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Service account file not found at {creds_path}")

    # Create credentials with specified scopes and the user to impersonate
    creds = google.oauth2.service_account.Credentials.from_service_account_file(
        creds_path, scopes=CALENDAR_SCOPES, subject=user_to_impersonate
    )

    service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
    return service

def get_free_busy_info(attendee_emails: list, start_time_str: str, end_time_str: str, user_to_impersonate: str) -> dict:
    """
    Fetches the free/busy information for a list of attendees.

    Args:
        attendee_emails: List of emails for the attendees.
        start_time_str: The start of the time range to check (ISO 8601 format).
        end_time_str: The end of the time range to check (ISO 8601 format).
        user_to_impersonate: The email of the user to act on behalf of.

    Returns:
        A dictionary containing the busy time slots for each calendar.
    """
    service = _get_calendar_service(user_to_impersonate)

    body = {
        "timeMin": start_time_str,
        "timeMax": end_time_str,
        "items": [{"id": email} for email in attendee_emails]
    }

    free_busy_response = service.freebusy().query(body=body).execute()
    return free_busy_response.get('calendars', {})

def create_calendar_event(summary: str, start_time_str: str, end_time_str: str, attendees: list, user_to_impersonate: str) -> dict:
    """
    Creates a new event in the user's primary calendar.

    Args:
        summary: The title of the event.
        start_time_str: The start time of the event (ISO 8601 format).
        end_time_str: The end time of the event (ISO 8601 format).
        attendees: A list of attendee email addresses.
        user_to_impersonate: The email of the user whose calendar will host the event.

    Returns:
        A dictionary representing the created event.
    """
    service = _get_calendar_service(user_to_impersonate)

    event_body = {
        'summary': summary,
        'start': {
            'dateTime': start_time_str,
            'timeZone': 'UTC', # Use UTC for consistency
        },
        'end': {
            'dateTime': end_time_str,
            'timeZone': 'UTC',
        },
        'attendees': [{'email': email} for email in attendees],
        'reminders': {
            'useDefault': True,
        },
    }

    created_event = service.events().insert(
        calendarId='primary',
        body=event_body,
        sendNotifications=True # Send invitations to attendees
    ).execute()

    print(f"Event created: {created_event.get('htmlLink')}")
    return created_event
