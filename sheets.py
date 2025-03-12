import os
import requests
import json
import openai
import gspread
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import time
import csv
from pathlib import Path
import argparse
import sys

# Load environment variables
load_dotenv()

# Configuration from .env
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")
SHEET_NAME = os.getenv("SHEET_NAME", "Call Logs")  # Default to "Call Logs"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"  # Debug mode

# Validate required environment variables
if not ELEVEN_API_KEY:
    raise ValueError("ELEVEN_API_KEY is required in .env file")
if not GOOGLE_CREDS_PATH:
    raise ValueError("GOOGLE_CREDS_PATH is required in .env file")
if not os.path.exists(GOOGLE_CREDS_PATH):
    raise FileNotFoundError(f"Google credentials file not found at: {GOOGLE_CREDS_PATH}")

# Set OpenAI API key if available
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    print("Warning: OPENAI_API_KEY not set. Summarization will be disabled.")

def get_google_credentials():
    """Get Google OAuth credentials"""
    try:
        # Define the scopes for Google Sheets
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        # Get the path to the credentials file
        creds_path = os.environ.get('GOOGLE_CREDS_PATH', 'credentials.json')
        
        # Check if token file exists
        token_path = 'token.json'
        creds = None
        
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_info(
                    json.load(open(token_path)), SCOPES)
                print("Loaded credentials from token file")
            except Exception as e:
                print(f"Error loading token: {e}")
                creds = None
                
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("Refreshed expired credentials")
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                # Load credentials from the credentials.json file
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        creds_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    print("Generated new credentials")
                    
                    # Save the credentials for future use
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                    print(f"Saved credentials to {token_path}")
                except Exception as e:
                    print(f"Error generating credentials: {e}")
                    raise
        
        return creds
    
    except Exception as e:
        print(f"Error getting Google credentials: {e}")
        return None

def get_call_history():
    """Retrieve paginated call history from ElevenLabs"""
    history = []
    
    # Define endpoints to try in order
    endpoints = [
        {"url": "https://api.elevenlabs.io/v1/history", "type": "standard"},
        {"url": "https://api.elevenlabs.io/v1/call-logs", "type": "call_logs"},
        {"url": "https://api.elevenlabs.io/v1/calls", "type": "calls"},
        {"url": "https://api.elevenlabs.io/v1/agent/calls", "type": "agent_calls"}
    ]
    
    # Try each endpoint
    for endpoint in endpoints:
        if DEBUG:
            print(f"Trying endpoint: {endpoint['url']}")
        
        try:
            page = 1
            max_retries = 3
            endpoint_history = []
            
            while True:
                for attempt in range(max_retries):
                    try:
                        if DEBUG:
                            print(f"Requesting page {page} from {endpoint['url']}...")
                        
                        response = requests.get(
                            url=endpoint['url'],
                            headers={"xi-api-key": ELEVEN_API_KEY},
                            params={"page_size": 100, "page": page}
                        )
                        
                        if DEBUG:
                            print(f"Response status code: {response.status_code}")
                            print(f"Response headers: {response.headers}")
                        
                        # If endpoint doesn't exist, move to next one
                        if response.status_code == 404:
                            if DEBUG:
                                print(f"Endpoint {endpoint['url']} not found (404)")
                            break
                        
                        if response.status_code == 429:  # Rate limit
                            wait_time = int(response.headers.get("Retry-After", 60))
                            print(f"Rate limit reached. Waiting {wait_time} seconds...")
                            time.sleep(wait_time)
                            continue
                            
                        response.raise_for_status()  # Raise exception for HTTP errors
                        data = response.json()
                        
                        if DEBUG:
                            print(f"Response data: {json.dumps(data, indent=2)[:500]}...")
                        
                        # Different endpoints might have different response structures
                        items = []
                        if endpoint['type'] == 'standard' and 'history' in data:
                            items = data['history']
                        elif endpoint['type'] == 'call_logs' and 'call_logs' in data:
                            items = data['call_logs']
                        elif endpoint['type'] == 'calls' and 'calls' in data:
                            items = data['calls']
                        elif endpoint['type'] == 'agent_calls' and 'calls' in data:
                            items = data['calls']
                        elif 'items' in data:
                            items = data['items']
                        
                        if not items:
                            if DEBUG:
                                print(f"No items found in response from {endpoint['url']}")
                            break
                            
                        endpoint_history.extend(items)
                        if DEBUG:
                            print(f"Added {len(items)} items from page {page}. Total items: {len(endpoint_history)}")
                        
                        # Check if there are more pages
                        has_more = False
                        if 'has_more' in data:
                            has_more = data['has_more']
                        elif 'next' in data:
                            has_more = data['next'] is not None
                        
                        if not has_more:
                            break
                            
                        page += 1
                        break  # Success, exit retry loop
                        
                    except requests.exceptions.RequestException as e:
                        print(f"API request failed: {e}")
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt  # Exponential backoff
                            print(f"Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                        else:
                            print(f"Failed to retrieve data after {max_retries} attempts: {e}")
                            break
                
                # If we broke out of the retry loop due to an error or end of pages
                if attempt == max_retries - 1 and not endpoint_history:
                    break
                
                # Define has_more here to ensure it's in scope
                has_more = False
                
                # If we got to the end of pages or got a 404, break out of the page loop
                if response.status_code == 404 or not has_more:
                    break
            
            # If we found history items from this endpoint, add them to the main history list
            if endpoint_history:
                print(f"Found {len(endpoint_history)} items from {endpoint['url']}")
                history.extend(endpoint_history)
                break  # We found a working endpoint, no need to try others
                
        except Exception as e:
            print(f"Error with endpoint {endpoint['url']}: {e}")
    
    return history

def summarize_text(text, max_tokens=100):
    """Generate a concise summary of a journal entry using OpenAI"""
    if not text or not OPENAI_API_KEY:
        return "No summary available"
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""
        Below is a transcript of a personal journal entry. Please create a concise summary (maximum 100 words) that captures:
        1. The main events or activities from the day
        2. Key insights, reflections, or realizations
        3. Any goals, intentions, or action items mentioned
        4. Notable emotional states or moods

        Transcript:
        {text}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates concise summaries of personal journal entries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
    
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Error generating summary"

def get_existing_entries(sheet):
    """Get existing entries to avoid duplicates"""
    try:
        all_values = sheet.get_all_values()
        if not all_values:
            return set()
            
        # Skip header row if it exists
        if all_values[0][0] == "Date" and all_values[0][1] == "Summary":
            all_values = all_values[1:]
            
        # Create a set of existing dates for quick lookup
        return {f"{row[0]}:{row[1]}" for row in all_values if row}
    except Exception as e:
        print(f"Error retrieving existing entries: {e}")
        return set()

def create_sample_data():
    """Create sample call log entries for testing purposes"""
    print("Creating sample call log entries for testing...")
    
    # Sample call data
    sample_calls = [
        {
            "history_item_id": "sample_call_1",
            "date": datetime.utcnow().isoformat() + "Z",
            "character_count_change_from": 120,  # Duration in seconds
            "text": "Hello, this is a sample call. The customer was inquiring about the new product features. We discussed pricing options and delivery timelines. The customer seemed satisfied with the information provided."
        },
        {
            "history_item_id": "sample_call_2",
            "date": (datetime.utcnow().replace(hour=datetime.utcnow().hour-1)).isoformat() + "Z",  # 1 hour ago
            "character_count_change_from": 180,  # Duration in seconds
            "text": "This is another sample call. The customer reported an issue with their account access. We verified their identity and reset their password. The issue was resolved and the customer can now access their account."
        },
        {
            "history_item_id": "sample_call_3",
            "date": (datetime.utcnow().replace(day=datetime.utcnow().day-1)).isoformat() + "Z",  # 1 day ago
            "character_count_change_from": 240,  # Duration in seconds
            "text": "Sample call from yesterday. The customer wanted to upgrade their subscription plan. We discussed the available options and the benefits of each plan. The customer decided to upgrade to the premium plan."
        }
    ]
    
    return sample_calls

def save_to_sheets(calls):
    """Save data to Google Sheets"""
    try:
        # Get Google OAuth credentials
        creds = get_google_credentials()
        
        # Authorize gspread with the credentials
        client = gspread.authorize(creds)
        
        # Try to open existing sheet or create a new one
        try:
            spreadsheet = client.open(SHEET_NAME)
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"Spreadsheet '{SHEET_NAME}' not found. Creating a new one...")
            spreadsheet = client.create(SHEET_NAME)
            # Optional: Share the spreadsheet with your email
            # spreadsheet.share('your-email@example.com', perm_type='user', role='writer')
            
        sheet = spreadsheet.sheet1
        
        # Add header if sheet is empty
        if not sheet.get_all_values():
            sheet.append_row(["Date", "Call ID", "Duration (sec)", "Summary", "Text", "Major Events", "Call Summary", "Action Items", "Customer Sentiment"])
            
        # Get existing entries to avoid duplicates
        existing_entries = get_existing_entries(sheet)
        
        # Process and add new entries
        rows_added = 0
        for call in calls:
            try:
                # Extract and format date
                timestamp = datetime.fromisoformat(call["date"].replace("Z", "+00:00"))
                formatted_date = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                call_id = call.get("history_item_id", "N/A")
                
                # Create unique entry key
                entry_key = f"{formatted_date}:{call_id}"
                
                # Skip if this entry already exists
                if entry_key in existing_entries:
                    print(f"Skipping existing entry: {formatted_date} (ID: {call_id})")
                    continue
                
                # Add row to sheet
                sheet.append_row([
                    formatted_date,
                    call_id,
                    call.get("character_count_change_from", 0),  # Using as duration approximation
                    call.get("summary", "No summary available"),
                    call.get("text", "")[:1000],  # Limit text length
                    call.get("major_events", ""),
                    call.get("call_summary", ""),
                    call.get("action_items", ""),
                    call.get("customer_sentiment", "")
                ])
                
                rows_added += 1
                print(f"Added entry: {formatted_date} (ID: {call_id})")
                
                # Avoid rate limits
                if rows_added % 10 == 0:
                    time.sleep(2)
                    
            except Exception as e:
                print(f"Error processing call: {e}")
                
        return rows_added
                
    except Exception as e:
        print(f"Error saving to Google Sheets: {e}")
        print("Falling back to CSV file...")
        return save_to_csv(calls)

def save_to_csv(data_list):
    """Save data to CSV file as fallback when Google Sheets fails"""
    csv_file = "journal_entries.csv"
    
    # Check if file exists
    file_exists = os.path.isfile(csv_file)
    
    # Get existing IDs to avoid duplicates
    existing_ids = set()
    if file_exists:
        try:
            with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'Call ID' in row:
                        existing_ids.add(row['Call ID'])
                    elif 'ID' in row:
                        existing_ids.add(row['ID'])
        except Exception as e:
            print(f"Error reading existing CSV: {e}")
    
    # Prepare data for CSV
    rows_added = 0
    with open(csv_file, 'a', newline='', encoding='utf-8') as f:
        # Define CSV headers
        fieldnames = ['Date', 'ID', 'Duration (sec)', 'Summary', 'Text', 'Major Events', 'Mood', 'Insights', 'Action Items']
        
        # Create CSV writer
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header if file is new
        if not file_exists:
            writer.writeheader()
        
        # Write data rows
        for item in data_list:
            item_id = item.get('id') or item.get('history_item_id')
            
            # Skip if this ID already exists in the CSV
            if item_id in existing_ids:
                print(f"Skipping existing entry: {item.get('date')} (ID: {item_id})")
                continue
            
            # Prepare row data
            row = {
                'Date': item.get('date'),
                'ID': item_id,
                'Duration (sec)': item.get('duration') or item.get('call_duration') or 0,
                'Summary': item.get('summary', 'No summary available'),
                'Text': item.get('conversation') or item.get('text', ''),
                'Major Events': item.get('major_events', ''),
                'Mood': item.get('mood', ''),
                'Insights': item.get('insights', ''),
                'Action Items': item.get('action_items', '')
            }
            
            # Write row to CSV
            writer.writerow(row)
            rows_added += 1
            print(f"Added entry to CSV: {item.get('date')} (ID: {item_id})")
    
    print(f"CSV file saved to: {os.path.abspath(csv_file)}")
    return rows_added

def process_webhook_data(file_path):
    """Process journal data from ElevenLabs webhook"""
    print(f"Processing webhook data from: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            webhook_data = json.load(f)
            
        if DEBUG:
            print(f"Webhook data: {json.dumps(webhook_data, indent=2)[:500]}...")
        
        # Check if this is a journal entry completion event
        is_completion = False
        if "event" in webhook_data:
            event_type = webhook_data.get("event", "").lower()
            is_completion = "complete" in event_type or "end" in event_type or "disconnect" in event_type
            
            if is_completion:
                print("Detected journal entry completion event - processing journal summary")
        
        # Extract relevant information from webhook data
        # The function now handles multiple possible formats from ElevenLabs
        
        journal_data = []
        journal_info = {}
        
        # Check for ElevenLabs Data Collection fields
        collected_data = {}
        
        # Look for data collection fields in different possible locations
        if "data_collection" in webhook_data:
            collected_data = webhook_data["data_collection"]
        elif "collected_data" in webhook_data:
            collected_data = webhook_data["collected_data"]
        elif "analysis" in webhook_data:
            collected_data = webhook_data.get("analysis", {}).get("data_collection", {})
        
        # Extract specific data collection fields if they exist
        major_events = None
        mood = None
        insights = None
        action_items = None
        
        if collected_data:
            print("Found data collection fields from ElevenLabs")
            major_events = collected_data.get("major_events")
            mood = collected_data.get("mood")
            insights = collected_data.get("insights")
            action_items = collected_data.get("action_items")
            
            # Log the extracted fields
            if major_events:
                print(f"Major events: {major_events}")
            if mood:
                print(f"Mood: {mood}")
            if insights:
                print(f"Insights: {insights}")
            if action_items:
                print(f"Action items: {action_items}")
        
        # Determine which format we're dealing with and extract data accordingly
        
        # Format 1: Simple format with basic journal information
        if "call_id" in webhook_data and "transcript" in webhook_data:
            journal_info = {
                "id": webhook_data.get("call_id"),
                "created_at": webhook_data.get("timestamp") or datetime.now().isoformat(),
                "duration": webhook_data.get("duration") or 0,
                "conversation": webhook_data.get("transcript") or "",
                "user": webhook_data.get("caller", "Me"),
                "agent_id": webhook_data.get("agent_id", "Journal Assistant"),
            }
        
        # Format 2: ElevenLabs conversation format
        elif "id" in webhook_data and "conversation" in webhook_data and isinstance(webhook_data["conversation"], dict):
            messages = webhook_data.get("conversation", {}).get("messages", [])
            transcript = ""
            
            # Convert message array to transcript format
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                transcript += f"{role.capitalize()}: {content}\n"
            
            metadata = webhook_data.get("metadata", {})
            
            journal_info = {
                "id": webhook_data.get("id"),
                "created_at": webhook_data.get("created_at") or datetime.now().isoformat(),
                "duration": metadata.get("call_duration", 0),
                "conversation": transcript.strip(),
                "user": metadata.get("caller_id", "Me"),
                "called_number": metadata.get("called_number", "Journal Service"),
            }
        
        # Format 3: Twilio-style format
        elif "call_sid" in webhook_data and "call_data" in webhook_data:
            call_data_obj = webhook_data.get("call_data", {})
            
            journal_info = {
                "id": webhook_data.get("call_sid"),
                "created_at": webhook_data.get("timestamp") or datetime.now().isoformat(),
                "duration": call_data_obj.get("duration", 0),
                "conversation": call_data_obj.get("transcript", ""),
                "user": webhook_data.get("caller_id", "Me"),
                "called_number": webhook_data.get("called_number", "Journal Service"),
                "agent_id": webhook_data.get("agent_id", "Journal Assistant"),
                "status": call_data_obj.get("status", "Completed"),
            }
        
        # Format 4: History format with transcript array
        elif "history_item_id" in webhook_data and "transcript" in webhook_data and isinstance(webhook_data["transcript"], list):
            transcript_array = webhook_data.get("transcript", [])
            transcript = ""
            
            # Convert transcript array to text format
            for entry in transcript_array:
                speaker = entry.get("speaker", "unknown")
                text = entry.get("text", "")
                transcript += f"{speaker.capitalize()}: {text}\n"
            
            call_details = webhook_data.get("call_details", {})
            
            journal_info = {
                "id": webhook_data.get("history_item_id"),
                "created_at": webhook_data.get("date") or datetime.now().isoformat(),
                "duration": webhook_data.get("character_count_change_from", 0),
                "conversation": transcript.strip() or webhook_data.get("text", ""),
                "user": call_details.get("caller", "Me"),
                "called_number": call_details.get("recipient", "Journal Service"),
                "status": call_details.get("status", "Completed"),
            }
            
        # Format 5: ElevenLabs journal completion webhook
        elif "event" in webhook_data and is_completion:
            call_data_obj = webhook_data.get("call", {}) or webhook_data.get("data", {}) or {}
            transcript = webhook_data.get("transcript", "") or call_data_obj.get("transcript", "")
            
            # If transcript is in conversation format, extract it
            if isinstance(transcript, dict) and "messages" in transcript:
                messages = transcript.get("messages", [])
                text = ""
                for msg in messages:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    text += f"{role.capitalize()}: {content}\n"
                transcript = text.strip()
            
            journal_info = {
                "id": call_data_obj.get("id") or webhook_data.get("call_id") or f"journal-{int(time.time())}",
                "created_at": call_data_obj.get("created_at") or webhook_data.get("timestamp") or datetime.now().isoformat(),
                "duration": call_data_obj.get("duration") or webhook_data.get("duration") or 0,
                "conversation": transcript,
                "user": call_data_obj.get("caller_id") or webhook_data.get("caller") or "Me",
                "called_number": call_data_obj.get("called_number") or webhook_data.get("called") or "Journal Service",
                "status": "completed",
            }
        
        # Fallback: Try to extract whatever we can
        else:
            print("Unknown webhook format, attempting to extract basic information...")
            
            # Look for any identifiable ID
            journal_id = (
                webhook_data.get("call_id") or
                webhook_data.get("id") or
                webhook_data.get("call_sid") or
                webhook_data.get("history_item_id") or
                f"journal-{int(time.time())}"
            )
            
            # Look for any timestamp
            created_at = (
                webhook_data.get("timestamp") or
                webhook_data.get("created_at") or
                webhook_data.get("date") or
                datetime.now().isoformat()
            )
            
            # Look for any conversation text
            conversation = (
                webhook_data.get("transcript") or
                webhook_data.get("text") or
                webhook_data.get("conversation") or
                ""
            )
            
            # If conversation is a dict or list, try to extract text
            if isinstance(conversation, dict) and "messages" in conversation:
                messages = conversation.get("messages", [])
                text = ""
                for msg in messages:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    text += f"{role.capitalize()}: {content}\n"
                conversation = text.strip()
            elif isinstance(conversation, list):
                text = ""
                for item in conversation:
                    if isinstance(item, dict):
                        speaker = item.get("speaker", "unknown")
                        content = item.get("text", "")
                        text += f"{speaker.capitalize()}: {content}\n"
                conversation = text.strip()
            
            journal_info = {
                "id": journal_id,
                "created_at": created_at,
                "duration": webhook_data.get("duration", 0),
                "conversation": conversation,
            }
        
        # Format date for CSV
        try:
            # Try to parse the timestamp
            if isinstance(journal_info["created_at"], str):
                dt = datetime.fromisoformat(journal_info["created_at"].replace('Z', '+00:00'))
                journal_info["date"] = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                journal_info["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"Error parsing date: {e}")
            journal_info["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Make sure we have a history_item_id for Google Sheets
        journal_info["history_item_id"] = journal_info.get("id")
        
        # Add text field for summary generation
        journal_info["text"] = journal_info.get("conversation", "")
        
        # Add data collection fields to journal_info if they exist
        if major_events:
            journal_info["major_events"] = major_events
        if mood:
            journal_info["mood"] = mood
        if insights:
            journal_info["insights"] = insights
        if action_items:
            journal_info["action_items"] = action_items
            
        # Generate summary if conversation text is available and no summary from ElevenLabs
        if journal_info["conversation"] and OPENAI_API_KEY and not journal_info.get("summary"):
            journal_info["summary"] = summarize_text(journal_info["conversation"])
            print(f"Generated summary: {journal_info['summary'][:100]}...")
        else:
            if not journal_info.get("summary"):
                journal_info["summary"] = "No summary available"
            
        journal_data.append(journal_info)
        
        if journal_data:
            print(f"Processed {len(journal_data)} journal entries from webhook data")
            try:
                rows_added = save_to_sheets(journal_data)
                print(f"Added {rows_added} new entries to '{SHEET_NAME}'.")
                return rows_added
            except Exception as e:
                print(f"Error saving to Google Sheets: {e}")
                print("Falling back to CSV file...")
                rows_added = save_to_csv(journal_data)
                return rows_added
        else:
            print("No valid journal data found in webhook payload")
            return 0
            
    except Exception as e:
        print(f"Error processing webhook data: {e}")
        return 0

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process call logs from ElevenLabs')
    parser.add_argument('--webhook-data', type=str, help='Path to webhook data JSON file')
    args = parser.parse_args()
    
    # If webhook data is provided, process it
    if args.webhook_data:
        process_webhook_data(args.webhook_data)
        return
    
    # Otherwise, proceed with the regular flow
    print("Retrieving call history from ElevenLabs...")
    
    # Try alternative API endpoints if available
    try:
        # First try the main history endpoint
        calls = get_call_history()
        
        if not calls and DEBUG:
            print("Trying alternative endpoints...")
            # You could add alternative endpoints here if needed
        
    except Exception as e:
        print(f"Error retrieving call history: {e}")
        calls = []
    
    if not calls:
        print("No call history found")
        
        # Use sample data for testing if no real data is available
        use_sample = input("Would you like to use sample data for testing? (y/n): ").lower() == 'y'
        if use_sample:
            calls = create_sample_data()
        else:
            return
 
    print(f"Found {len(calls)} calls. Saving to Google Sheets...")
    rows_added = save_to_sheets(calls)
    
    print(f"Process completed. Added {rows_added} new entries to '{SHEET_NAME}'.")

if __name__ == "__main__":
    # Set DEBUG=true to enable debug output
    if DEBUG:
        print("Debug mode enabled")
    main()