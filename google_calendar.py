import os
import json
import logging
from datetime import datetime, timedelta
import google.auth
import google.auth.impersonated_credentials
import google.oauth2.service_account
import googleapiclient.discovery

# Scopes required for the Google Calendar API
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']

def _get_calendar_service(user_to_impersonate: str):
    """Creates and returns a Google Calendar service object impersonating a user."""
    try:
        creds = None
        creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if creds_json_str:
            # Priority 1: Use JSON from environment variable
            creds_info = json.loads(creds_json_str)
            creds = google.oauth2.service_account.Credentials.from_service_account_info(
                creds_info, scopes=CALENDAR_SCOPES, subject=user_to_impersonate
            )
        elif creds_path and os.path.exists(creds_path):
            # Priority 2: Use service account key file path
            creds = google.oauth2.service_account.Credentials.from_service_account_file(
                creds_path, scopes=CALENDAR_SCOPES, subject=user_to_impersonate
            )
        else:
            # Priority 3: Fallback to Application Default Credentials
            creds, _ = google.auth.default(scopes=CALENDAR_SCOPES)
            if user_to_impersonate:
                creds = google.auth.impersonated_credentials.Credentials(
                    source_credentials=creds,
                    target_principal=user_to_impersonate,
                    target_scopes=CALENDAR_SCOPES,
                    lifetime=3600
                )

        service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logging.error(f"Error creating calendar service: {e}")
        raise e

def get_free_busy_info(attendee_emails: list, start_time_str: str, end_time_str: str, user_to_impersonate: str) -> dict:
    """
    Fetches detailed event information for a list of attendees to identify busy times and potential soft blocks.

    Args:
        attendee_emails: List of emails for the attendees.
        start_time_str: The start of the time range to check (ISO 8601 format).
        end_time_str: The end of the time range to check (ISO 8601 format).
        user_to_impersonate: The email of the user to act on behalf of.

    Returns:
        A dictionary containing detailed busy slots for each calendar.
    """
    logging.info("--- Getting detailed free/busy info ---")
    service = _get_calendar_service(user_to_impersonate)
    attendee_data = []
    soft_block_keywords = ["focus time", "study time", "no meetings", "deep work"]

    for email in attendee_emails:
        try:
            events_result = service.events().list(
                calendarId=email,
                timeMin=start_time_str,
                timeMax=end_time_str,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            busy_slots = []
            soft_blocks = []
            for event in events:
                summary = event.get('summary', '').lower()
                attendees_count = len(event.get('attendees', []))
                event_details = {
                    'start': event['start'].get('dateTime', event['start'].get('date')),
                    'end': event['end'].get('dateTime', event['end'].get('date')),
                    'summary': summary,
                    'attendees_count': attendees_count
                }

                # Check if it's a soft block
                is_soft_block = any(keyword in summary for keyword in soft_block_keywords) or attendees_count <= 1
                
                if is_soft_block:
                    soft_blocks.append(event_details)
                else:
                    busy_slots.append(event_details)

            attendee_data.append({
                "email": email,
                "busy_slots": busy_slots,
                "soft_blocks": soft_blocks
            })
        except Exception as e:
            logging.error(f"Could not fetch calendar for {email}. It might be a permissions issue or the calendar doesn't exist. Error: {e}")
            # Add the attendee with empty lists if their calendar is inaccessible
            attendee_data.append({
                "email": email,
                "busy_slots": [],
                "soft_blocks": []
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

        # Exclude the agent's email from the attendee list
        agent_email = os.getenv("AGENT_EMAIL")
        if agent_email:
            attendees = [email for email in attendees if email.lower() != agent_email.lower()]

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

def reschedule_calendar_event(event_id: str, start_time_str: str, end_time_str: str, user_to_impersonate: str) -> dict:
    """
    Reschedules an existing calendar event.

    Args:
        event_id: The ID of the event to reschedule.
        start_time_str: The new start time of the event (ISO 8601 format).
        end_time_str: The new end time of the event (ISO 8601 format).
        user_to_impersonate: The email of the user whose calendar hosts the event.

    Returns:
        A dictionary representing the updated event.
    """
    logging.info(f"--- Rescheduling calendar event {event_id} ---")
    try:
        service = _get_calendar_service(user_to_impersonate)

        # First, get the existing event to preserve its other details
        event = service.events().get(calendarId='primary', eventId=event_id).execute()

        # Update the start and end times
        event['start']['dateTime'] = start_time_str
        event['end']['dateTime'] = end_time_str

        updated_event = service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event,
            sendNotifications=True
        ).execute()

        logging.info(f"Event rescheduled: {updated_event.get('htmlLink')}")
        return updated_event
    except Exception as e:
        logging.error(f"Error rescheduling event: {e}")
        raise e
