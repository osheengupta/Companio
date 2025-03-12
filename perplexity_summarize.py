#!/usr/bin/env python3
"""
Script to get conversation data from ElevenLabs API and summarize it using Perplexity API.
"""

import os
import json
import argparse
import requests
from datetime import datetime
import sys
from pathlib import Path
import csv

# Import functions from sheets.py
sys.path.append(str(Path(__file__).parent))
try:
    # Import only what we need to avoid initialization errors
    from sheets import save_to_sheets as sheets_save_to_sheets
    sheets_available = True
except (ImportError, Exception) as e:
    print(f"Warning: Could not import save_to_sheets from sheets.py: {e}")
    sheets_available = False
    sheets_save_to_sheets = None

def get_conversation_details(conversation_id, api_key):
    """Get details of a specific conversation from ElevenLabs API"""
    try:
        # API endpoint
        url = f"https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}"
        
        # Headers
        headers = {
            "xi-api-key": api_key
        }
        
        # Make the API request
        response = requests.get(url, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            conversation_data = response.json()
            print(f"Successfully retrieved conversation details for ID: {conversation_id}")
            return conversation_data
        else:
            print(f"Error retrieving conversation details: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Exception occurred while retrieving conversation details: {e}")
        return None

def extract_conversation_text(conversation_data):
    """Extract the conversation text from the conversation data"""
    if not conversation_data or 'transcript' not in conversation_data:
        return "No transcript found in conversation data."
    
    transcript = conversation_data.get('transcript', [])
    conversation_text = ""
    
    for message in transcript:
        role = message.get('role', '')
        content = message.get('message', '')
        conversation_text += f"{role.capitalize()}: {content}\n"
    
    return conversation_text

def summarize_with_perplexity(conversation_text, perplexity_api_key):
    """Summarize the conversation text using Perplexity API"""
    try:
        url = "https://api.perplexity.ai/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {perplexity_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama-3-sonar-small-32k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes journal entries. Extract key points, emotions, and insights from the journal entry."
                },
                {
                    "role": "user",
                    "content": f"Please summarize this journal entry conversation. Focus on extracting the main events, emotions, insights, and any action items mentioned:\n\n{conversation_text}"
                }
            ],
            "max_tokens": 1024
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            summary = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            return summary
        else:
            print(f"Error from Perplexity API: {response.status_code} - {response.text}")
            return "Failed to generate summary."
            
    except Exception as e:
        print(f"Exception occurred while summarizing with Perplexity: {e}")
        return "Failed to generate summary due to an error."

def save_to_file(conversation_data, summary, output_dir="journal_summaries"):
    """Save the conversation data and summary to a file"""
    try:
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        conversation_id = conversation_data.get('conversation_id', 'unknown')
        filename = f"{output_dir}/{timestamp}_{conversation_id}.json"
        
        # Prepare output data
        output_data = {
            "conversation": conversation_data,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"Saved conversation data and summary to {filename}")
        return filename
    
    except Exception as e:
        print(f"Error saving to file: {e}")
        return None

def save_raw_json(data, output_dir="journal_raw_data"):
    """Save the raw JSON data to a file"""
    try:
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        conversation_id = data.get('conversation_id', 'unknown')
        filename = f"{output_dir}/{timestamp}_{conversation_id}_raw.json"
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved raw JSON data to {filename}")
        return filename
    
    except Exception as e:
        print(f"Error saving raw JSON data: {e}")
        return None

def prepare_for_sheets(conversation_data, summary):
    """Prepare the data for Google Sheets in the expected format"""
    try:
        # Extract conversation metadata
        conversation_id = conversation_data.get('conversation_id', 'unknown')
        status = conversation_data.get('status', 'unknown')
        
        # Extract conversation text
        conversation_text = extract_conversation_text(conversation_data)
        
        # Extract transcript for analysis
        transcript = conversation_data.get('transcript', [])
        
        # Extract data collection fields if available
        # These would typically come from the webhook, but we'll try to extract them from the transcript
        major_events = ""
        mood = ""
        insights = ""
        action_items = ""
        
        # Try to extract action items from the summary
        if "action item" in summary.lower() or "to-do" in summary.lower():
            # Simple extraction - in a real app, you'd use NLP to extract these more accurately
            for line in summary.split('\n'):
                if "action item" in line.lower() or "to-do" in line.lower():
                    action_items += line + "\n"
        
        # Create a journal entry in the expected format for sheets.py
        journal_entry = {
            "history_item_id": conversation_id,
            "date": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
            "conversation": conversation_text,
            "text": conversation_text,
            "summary": summary,
            "major_events": major_events,
            "mood": mood,
            "insights": insights,
            "action_items": action_items,
            "character_count_change_from": len(conversation_text)  # Approximation for duration
        }
        
        return [journal_entry]  # Return as a list since save_to_sheets expects a list
        
    except Exception as e:
        print(f"Error preparing data for sheets: {e}")
        return None

def save_to_sheets(data):
    """Save data to Google Sheets using the imported function"""
    if not sheets_available:
        print("Error: Google Sheets integration is not available")
        return 0
    
    try:
        return sheets_save_to_sheets(data)
    except Exception as e:
        print(f"Error saving to Google Sheets: {e}")
        return 0

def save_to_csv(data, csv_file="journal_entries.csv"):
    """Save journal entry data to a CSV file"""
    try:
        # Determine if this is a new file or if we're appending
        file_exists = os.path.isfile(csv_file)
        
        # Define CSV headers based on the data structure
        headers = [
            "Date", "Conversation ID", "Duration", "Summary", 
            "Text", "Major Events", "Insights", "Action Items", "Mood"
        ]
        
        # Open the file in append mode
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            
            # Write header if this is a new file
            if not file_exists:
                writer.writeheader()
            
            # Write each entry
            rows_added = 0
            for entry in data:
                # Format the data for CSV
                csv_row = {
                    "Date": entry.get("date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    "Conversation ID": entry.get("history_item_id", ""),
                    "Duration": entry.get("character_count_change_from", 0),
                    "Summary": entry.get("summary", ""),
                    "Text": entry.get("text", "")[:1000],  # Limit text length
                    "Major Events": entry.get("major_events", ""),
                    "Insights": entry.get("insights", ""),
                    "Action Items": entry.get("action_items", ""),
                    "Mood": entry.get("mood", "")
                }
                
                writer.writerow(csv_row)
                rows_added += 1
                
            print(f"Added {rows_added} entries to {csv_file}")
            return rows_added
            
    except Exception as e:
        print(f"Error saving to CSV: {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description='Get and summarize conversation from ElevenLabs')
    parser.add_argument('--conversation-id', required=True, help='ElevenLabs conversation ID')
    parser.add_argument('--elevenlabs-api-key', help='ElevenLabs API key (or set ELEVENLABS_API_KEY env var)')
    parser.add_argument('--perplexity-api-key', help='Perplexity API key (or set PERPLEXITY_API_KEY env var)')
    parser.add_argument('--output-dir', default='journal_summaries', help='Directory to save output files')
    parser.add_argument('--save-to-sheets', action='store_true', help='Save the summary to Google Sheets')
    parser.add_argument('--save-to-csv', action='store_true', help='Save the summary to CSV file')
    parser.add_argument('--csv-file', default='journal_entries.csv', help='CSV file to save to')
    
    args = parser.parse_args()
    
    # Get API keys from args or environment variables
    elevenlabs_api_key = args.elevenlabs_api_key or os.environ.get('ELEVENLABS_API_KEY')
    perplexity_api_key = args.perplexity_api_key or os.environ.get('PERPLEXITY_API_KEY')
    
    if not elevenlabs_api_key:
        print("Error: ElevenLabs API key is required. Provide it as an argument or set the ELEVENLABS_API_KEY environment variable.")
        print("\nUsage example:")
        print("  python perplexity_summarize.py --conversation-id pUzxZsY3v5OGjOYYOQ2f --elevenlabs-api-key YOUR_ELEVENLABS_KEY --perplexity-api-key YOUR_PERPLEXITY_KEY")
        return 1
    
    if not perplexity_api_key:
        print("Error: Perplexity API key is required. Provide it as an argument or set the PERPLEXITY_API_KEY environment variable.")
        print("\nUsage example:")
        print("  python perplexity_summarize.py --conversation-id pUzxZsY3v5OGjOYYOQ2f --elevenlabs-api-key YOUR_ELEVENLABS_KEY --perplexity-api-key YOUR_PERPLEXITY_KEY")
        return 1
    
    # Get conversation details
    conversation_data = get_conversation_details(args.conversation_id, elevenlabs_api_key)
    if not conversation_data:
        print("Failed to retrieve conversation data.")
        return 1
    
    # Save raw JSON data
    save_raw_json(conversation_data)
    
    # Extract conversation text
    conversation_text = extract_conversation_text(conversation_data)
    print("\nExtracted conversation text:")
    print(conversation_text[:500] + "..." if len(conversation_text) > 500 else conversation_text)
    
    # Summarize conversation
    print("\nGenerating summary...")
    summary = summarize_with_perplexity(conversation_text, perplexity_api_key)
    
    print("\nSummary:")
    print(summary)
    
    # Save to file
    save_to_file(conversation_data, summary, args.output_dir)
    
    # Save to Google Sheets if requested
    if args.save_to_sheets:
        if not sheets_available:
            print("\nGoogle Sheets integration is not available. Skipping save to sheets.")
        else:
            print("\nSaving to Google Sheets...")
            sheet_data = prepare_for_sheets(conversation_data, summary)
            if sheet_data:
                try:
                    rows_added = save_to_sheets(sheet_data)
                    print(f"Added {rows_added} entries to Google Sheets")
                except Exception as e:
                    print(f"Error saving to Google Sheets: {e}")
    
    # Save to CSV if requested
    if args.save_to_csv:
        print(f"\nSaving to CSV file: {args.csv_file}")
        sheet_data = prepare_for_sheets(conversation_data, summary)
        if sheet_data:
            try:
                rows_added = save_to_csv(sheet_data, args.csv_file)
                print(f"Added {rows_added} entries to CSV file")
            except Exception as e:
                print(f"Error saving to CSV: {e}")
    
    return 0

if __name__ == "__main__":
    exit(main())
