#!/usr/bin/env python3
"""
Process scraped ElevenLabs conversation data and integrate with the summarization workflow.
This script reads the scraped JSON files and can either:
1. Display a list of available conversations
2. Summarize a specific conversation
3. Batch summarize multiple conversations
"""

import os
import json
import argparse
import glob
from datetime import datetime
from pathlib import Path

# Try to import the summarization module
try:
    from perplexity_summarize import summarize_with_perplexity
    summarization_available = True
except ImportError:
    summarization_available = False
    print("Warning: perplexity_summarize module not available. Summarization features will be disabled.")

def load_env_vars():
    """Load environment variables from .env file if available"""
    env_vars = {}
    env_path = Path(__file__).parent / ".env"
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                env_vars[key] = value.strip('"').strip("'")
    
    return env_vars

def find_scraped_files(data_dir="conversation_data"):
    """Find all scraped JSON files in the data directory"""
    # Create directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    # Find all JSON files
    json_files = glob.glob(f"{data_dir}/*.json")
    return sorted(json_files, reverse=True)  # Sort by newest first

def load_conversation_data(file_path):
    """Load conversation data from a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return None

def list_conversations(file_path):
    """List all conversations in a file"""
    data = load_conversation_data(file_path)
    if not data:
        return
    
    conversations = data.get("conversations", [])
    print(f"\nFound {len(conversations)} conversations in {os.path.basename(file_path)}:")
    
    for i, conv in enumerate(conversations):
        print(f"{i+1}. ID: {conv.get('conversation_id')}")
        print(f"   Title: {conv.get('title')}")
        print(f"   Date: {conv.get('date')}")
        print(f"   Messages: {len(conv.get('transcript', []))}")
        print()

def get_conversation_text(conversation):
    """Extract text from a conversation transcript"""
    transcript = conversation.get("transcript", [])
    conversation_text = ""
    
    for message in transcript:
        role = message.get("role", "")
        content = message.get("message", "")
        conversation_text += f"{role.capitalize()}: {content}\n\n"
    
    return conversation_text

def summarize_conversation(file_path, conversation_index, api_key=None):
    """Summarize a specific conversation from a file"""
    if not summarization_available:
        print("Error: Summarization module not available")
        return
    
    data = load_conversation_data(file_path)
    if not data:
        return
    
    conversations = data.get("conversations", [])
    if conversation_index < 0 or conversation_index >= len(conversations):
        print(f"Error: Invalid conversation index {conversation_index+1}")
        return
    
    conversation = conversations[conversation_index]
    conversation_text = get_conversation_text(conversation)
    
    print(f"\nSummarizing conversation: {conversation.get('title')}")
    print(f"Date: {conversation.get('date')}")
    print(f"ID: {conversation.get('conversation_id')}")
    print(f"Length: {len(conversation_text)} characters")
    
    # Get API key if not provided
    if not api_key:
        env_vars = load_env_vars()
        api_key = env_vars.get("PERPLEXITY_API_KEY", "")
    
    if not api_key:
        print("Error: Perplexity API key not found")
        return
    
    # Summarize the conversation
    summary = summarize_with_perplexity(conversation_text, api_key)
    
    if summary:
        print("\n--- SUMMARY ---")
        print(summary)
        
        # Save summary to file
        output_dir = "summaries"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        title_slug = conversation.get('title', 'untitled').replace(' ', '_').lower()
        output_file = f"{output_dir}/{title_slug}_{timestamp}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Title: {conversation.get('title')}\n")
            f.write(f"Date: {conversation.get('date')}\n")
            f.write(f"ID: {conversation.get('conversation_id')}\n\n")
            f.write("--- SUMMARY ---\n\n")
            f.write(summary)
            f.write("\n\n--- ORIGINAL TRANSCRIPT ---\n\n")
            f.write(conversation_text)
        
        print(f"\nSummary saved to: {output_file}")
    else:
        print("Error: Failed to generate summary")

def main():
    parser = argparse.ArgumentParser(description="Process scraped ElevenLabs conversation data")
    parser.add_argument("--list", "-l", action="store_true", help="List available conversations")
    parser.add_argument("--file", "-f", help="Specify JSON file to use (defaults to most recent)")
    parser.add_argument("--summarize", "-s", type=int, help="Summarize conversation by index (1-based)")
    parser.add_argument("--api-key", help="Perplexity API key (optional, will use .env if not provided)")
    
    args = parser.parse_args()
    
    # Find available files
    json_files = find_scraped_files()
    
    if not json_files:
        print("No scraped conversation files found in the conversation_data directory")
        return
    
    # Determine which file to use
    file_to_use = args.file if args.file else json_files[0]
    
    if args.file and args.file not in json_files:
        print(f"Warning: Specified file {args.file} not found")
        print(f"Using most recent file: {json_files[0]}")
        file_to_use = json_files[0]
    
    # List conversations if requested
    if args.list:
        list_conversations(file_to_use)
    
    # Summarize conversation if requested
    if args.summarize is not None:
        # Convert from 1-based to 0-based index
        summarize_conversation(file_to_use, args.summarize - 1, args.api_key)
    
    # If no action specified, show available files and list conversations in the most recent file
    if not args.list and args.summarize is None:
        print("Available scraped files:")
        for i, file in enumerate(json_files):
            print(f"{i+1}. {os.path.basename(file)}")
        
        print("\nTo view conversations in a file, use: python process_scraped_data.py --list")
        print("To summarize a conversation, use: python process_scraped_data.py --summarize N")
        
        # Show conversations in the most recent file
        list_conversations(file_to_use)

if __name__ == "__main__":
    main()
