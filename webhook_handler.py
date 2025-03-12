#!/usr/bin/env python3
"""
Webhook handler for Make HTTP triggers.
This script receives webhook requests from Make and triggers the journal summarization process.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('webhook_handler')

# Import local modules
sys.path.append(str(Path(__file__).parent))
try:
    from perplexity_summarize import main as summarize_main
    summarize_available = True
except ImportError:
    logger.warning("Could not import perplexity_summarize. Summarization will not be available.")
    summarize_available = False

# Load environment variables
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

env_vars = load_env_vars()

# Initialize Flask app
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook requests"""
    try:
        # Get request data
        data = request.json
        logger.info(f"Received webhook request: {data}")
        
        # Validate request
        if not data or not isinstance(data, dict):
            return jsonify({"status": "error", "message": "Invalid request data"}), 400
        
        # Extract conversation ID
        conversation_id = data.get('conversation_id')
        if not conversation_id:
            return jsonify({"status": "error", "message": "Missing conversation_id"}), 400
        
        # Check if summarization is available
        if not summarize_available:
            return jsonify({"status": "error", "message": "Summarization is not available"}), 500
        
        # Prepare arguments for summarization
        args = argparse.Namespace()
        args.conversation_id = conversation_id
        args.elevenlabs_api_key = env_vars.get('ELEVENLABS_API_KEY') or env_vars.get('ELEVEN_API_KEY')
        args.perplexity_api_key = env_vars.get('PERPLEXITY_API_KEY')
        args.output_dir = 'journal_summaries'
        
        # Check if we should save to Google Sheets
        args.save_to_sheets = data.get('save_to_sheets', True)
        
        # Check if we should save to CSV
        args.save_to_csv = data.get('save_to_csv', True)
        args.csv_file = data.get('csv_file', 'journal_entries.csv')
        
        # Run summarization
        try:
            logger.info(f"Starting summarization for conversation {conversation_id}")
            result = summarize_main(args)
            
            if result == 0:
                logger.info(f"Summarization completed successfully for conversation {conversation_id}")
                return jsonify({
                    "status": "success",
                    "message": "Summarization completed successfully",
                    "conversation_id": conversation_id
                }), 200
            else:
                logger.error(f"Summarization failed for conversation {conversation_id} with exit code {result}")
                return jsonify({
                    "status": "error",
                    "message": f"Summarization failed with exit code {result}",
                    "conversation_id": conversation_id
                }), 500
                
        except Exception as e:
            logger.exception(f"Exception during summarization: {e}")
            return jsonify({
                "status": "error",
                "message": f"Exception during summarization: {str(e)}",
                "conversation_id": conversation_id
            }), 500
    
    except Exception as e:
        logger.exception(f"Exception handling webhook: {e}")
        return jsonify({"status": "error", "message": f"Exception handling webhook: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()}), 200

def main():
    """Main function to run the Flask app"""
    parser = argparse.ArgumentParser(description='Webhook handler for Make HTTP triggers')
    parser.add_argument('--host', default='0.0.0.0', help='Host to run the server on')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    # Check if summarization is available
    if not summarize_available:
        logger.warning("Summarization is not available. Webhook will not be able to summarize journals.")
    
    # Run the Flask app
    logger.info(f"Starting webhook handler on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)
    
    return 0

if __name__ == "__main__":
    exit(main())
