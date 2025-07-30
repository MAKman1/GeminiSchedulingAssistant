import os
import logging
from datetime import datetime, timedelta
import google.auth
import google.oauth2.service_account
import googleapiclient.discovery

# Scopes required for the Google Calendar API
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']

def _get_calendar_service(user_to_impersonate: str):
    """Creates and returns a Google Calendar service object impersonating a user."""

    try:
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and os.path.exists(creds_path):
            # Use service account key file if it exists
            creds = google.oauth2.service_account.Credentials.from_service_account_file(
                creds_path, scopes=CALENDAR_SCOPES, subject=user_to_impersonate
            )
        else:
            # Fallback to Application Default Credentials
            creds, _ = google.auth.default(scopes=CALENDAR_SCOPES)
            creds = creds.with_subject(user_to_impersonate)

        service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logging.error(f"Error creating calendar service: {e}")
        raise e

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
    logging.info("--- Getting free/busy info ---")
    try:
        service = _get_calendar_service(user_to_impersonate)

        body = {
            "timeMin": start_time_str,
            "timeMax": end_time_str,
            "items": [{"id": email} for email in attendee_emails]
        }

        logging.info(f"Free/busy request body: {body}")
        free_busy_response = service.freebusy().query(body=body).execute()
        logging.info(f"Free/busy response: {free_busy_response}")
        calendars = free_busy_response.get('calendars', {})
    except Exception as e:
        logging.error(f"Error getting free/busy info: {e}")
        raise e

    attendee_data = []
    for email in attendee_emails:
        calendar_info = calendars.get(email, {})
        busy_slots = calendar_info.get('busy', [])
        attendee_data.append({
            "email": email,
            "busy_slots": busy_slots,
            "soft_blocks": [] # Placeholder for now
        })

    return {
        "internal_attendees": attendee_data,
        "external_attendees": [] # Placeholder for now
    }

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
    logging.info("--- Creating calendar event ---")
    try:
        service = _get_calendar_service(user_to_impersonate)

        event_body = {
            'summary': summary,
            'start': {
                'dateTime': start_time_str,
                'timeZone': 'Europe/London',
            },
            'end': {
                'dateTime': end_time_str,
                'timeZone': 'Europe/London',
            },
            'attendees': [{'email': email} for email in attendees],
            'reminders': {
                'useDefault': True,
            },
        }

        logging.info(f"Event body: {event_body}")
        created_event = service.events().insert(
            calendarId='primary',
            body=event_body,
            sendNotifications=True # Send invitations to attendees
        ).execute()

        logging.info(f"Event created: {created_event.get('htmlLink')}")
        return created_event
    except Exception as e:
        logging.error(f"Error creating calendar event: {e}")
        raise e
