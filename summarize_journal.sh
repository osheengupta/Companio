#!/bin/bash

# This script runs the perplexity_summarize.py script with the necessary API keys
# Usage: ./summarize_journal.sh <conversation_id> [--save-to-sheets|--save-to-csv]

# Check if conversation ID is provided
if [ -z "$1" ]; then
    echo "Error: Conversation ID is required"
    echo "Usage: ./summarize_journal.sh <conversation_id> [--save-to-sheets|--save-to-csv]"
    exit 1
fi

CONVERSATION_ID="$1"
SAVE_OPTION=""

# Check for save options
if [ "$2" = "--save-to-sheets" ]; then
    SAVE_OPTION="--save-to-sheets"
elif [ "$2" = "--save-to-csv" ]; then
    SAVE_OPTION="--save-to-csv"
fi

# Load environment variables from .env file
if [ -f .env ]; then
    # Source the .env file instead of using export
    source .env
    echo "Loaded environment variables from .env"
else
    echo "Warning: .env file not found. Make sure to provide API keys as arguments."
fi

# Check if required API keys are set
if [ -z "$ELEVENLABS_API_KEY" ] && [ -z "$ELEVEN_API_KEY" ]; then
    echo "Error: ElevenLabs API key is not set. Please set ELEVENLABS_API_KEY or ELEVEN_API_KEY in .env"
    exit 1
fi

if [ -z "$PERPLEXITY_API_KEY" ]; then
    echo "Error: Perplexity API key is not set. Please set PERPLEXITY_API_KEY in .env"
    exit 1
fi

# Use ELEVEN_API_KEY as fallback for ELEVENLABS_API_KEY
if [ -z "$ELEVENLABS_API_KEY" ] && [ -n "$ELEVEN_API_KEY" ]; then
    ELEVENLABS_API_KEY="$ELEVEN_API_KEY"
    echo "Using ELEVEN_API_KEY for ElevenLabs authentication"
fi

# Run the Python script
echo "Running: python perplexity_summarize.py --conversation-id $CONVERSATION_ID $SAVE_OPTION"
python perplexity_summarize.py --conversation-id "$CONVERSATION_ID" \
    --elevenlabs-api-key "$ELEVENLABS_API_KEY" \
    --perplexity-api-key "$PERPLEXITY_API_KEY" \
    $SAVE_OPTION
