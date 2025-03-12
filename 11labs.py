import requests
import json
import os
from datetime import datetime

# Your API key - in a production environment, this should be stored in environment variables
API_KEY = "sk_299f5f99d01131853b2140c78384e84d7dd792e4614eb647"

# Base URL for ElevenLabs API
base_url = "https://api.elevenlabs.io/v1"

# Headers for API requests
headers = {
    "xi-api-key": API_KEY,
    "accept": "application/json"
}

def make_api_request(endpoint, method="GET", data=None):
    """Make a request to the ElevenLabs API"""
    url = f"{base_url}/{endpoint}"
    
    print(f"Making {method} request to: {url}")
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    else:
        print(f"Unsupported method: {method}")
        return None
    
    print(f"Response status code: {response.status_code}")
    
    if response.status_code in [200, 201]:
        try:
            data = response.json()
            return data
        except json.JSONDecodeError:
            print("Response is not JSON")
            return response.content
    else:
        print(f"Request failed: {response.status_code} {response.text}")
        return None

def get_user_info():
    """Get information about the current user"""
    return make_api_request("user")

def get_voices():
    """Get all available voices"""
    return make_api_request("voices")

def get_models():
    """Get all available models"""
    return make_api_request("models")

def get_history_items():
    """Get all history items"""
    return make_api_request("history")

def text_to_speech(text, voice_id, model_id="eleven_multilingual_v2"):
    """Convert text to speech using the specified voice and model"""
    endpoint = f"text-to-speech/{voice_id}"
    data = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    response = make_api_request(endpoint, method="POST", data=data)
    
    if response and not isinstance(response, dict):
        # If the response is binary audio data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tts_output_{timestamp}.mp3"
        
        with open(filename, "wb") as f:
            f.write(response)
        
        print(f"Audio saved to {filename}")
        return filename
    
    return None

def generate_summary_report():
    """Generate a summary report of the ElevenLabs API capabilities"""
    report = []
    report.append("# ElevenLabs API Capabilities Report")
    report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n## User Information")
    
    user_info = get_user_info()
    if user_info:
        subscription = user_info.get("subscription", {})
        report.append(f"- User ID: {user_info.get('user_id')}")
        report.append(f"- Subscription Tier: {subscription.get('tier')}")
        report.append(f"- Character Count: {subscription.get('character_count')} / {subscription.get('character_limit')}")
        report.append(f"- Voice Slots: {subscription.get('voice_slots_used')} / {subscription.get('voice_limit')}")
    else:
        report.append("- Failed to retrieve user information")
    
    report.append("\n## Available Voices")
    voices = get_voices()
    if voices:
        voice_list = voices.get("voices", [])
        report.append(f"- Total Voices: {len(voice_list)}")
        report.append("- First 5 voices:")
        for i, voice in enumerate(voice_list[:5]):
            report.append(f"  {i+1}. {voice.get('name')} (ID: {voice.get('voice_id')})")
    else:
        report.append("- Failed to retrieve voice information")
    
    report.append("\n## Available Models")
    models = get_models()
    if models and isinstance(models, list):
        report.append(f"- Total Models: {len(models)}")
        report.append("- Available Models:")
        for i, model in enumerate(models):
            report.append(f"  {i+1}. {model.get('name')} (ID: {model.get('model_id')})")
            report.append(f"     Description: {model.get('description')}")
    else:
        report.append("- Failed to retrieve model information")
    
    report.append("\n## History Items")
    history = get_history_items()
    if history:
        history_items = history.get("history", [])
        report.append(f"- Total History Items: {len(history_items)}")
        if history_items:
            report.append("- Recent History Items:")
            for i, item in enumerate(history_items[:5]):
                report.append(f"  {i+1}. Created: {item.get('created_at')}")
                text = item.get('text', '')
                report.append(f"     Text: {text[:100]}..." if len(text) > 100 else f"     Text: {text}")
        else:
            report.append("- No history items found")
    else:
        report.append("- Failed to retrieve history information")
    
    report.append("\n## API Endpoint Status")
    report.append("- ✅ /user - User information")
    report.append("- ✅ /voices - Available voices")
    report.append("- ✅ /models - Available models")
    report.append("- ✅ /history - History items")
    report.append("- ✅ /text-to-speech - Text to speech conversion")
    report.append("- ❌ /projects - Requires special subscription")
    report.append("- ❌ /conversational-ai - Not accessible or doesn't exist")
    
    report.append("\n## Conclusion")
    report.append("Based on the API exploration, the conversational-ai endpoint is not accessible with the current API key. The history endpoint works but shows no history items in the account. To access conversation data, you may need to:")
    report.append("1. Upgrade your subscription to access additional endpoints")
    report.append("2. Contact ElevenLabs support to inquire about the conversational-ai endpoint")
    report.append("3. Use the text-to-speech functionality to generate audio and then track those in your history")
    
    return "\n".join(report)

def main():
    print("Starting ElevenLabs API Exploration...")
    
    # Generate a summary report
    report = generate_summary_report()
    
    # Save the report to a file
    report_filename = "elevenlabs_api_report.md"
    with open(report_filename, "w") as f:
        f.write(report)
    
    print(f"\nReport saved to {report_filename}")
    
    # Print the report to the console
    print("\n" + report)
    
    # Optionally, demonstrate text-to-speech functionality
    print("\nDemonstrating text-to-speech functionality...")
    voices = get_voices()
    if voices:
        voice_list = voices.get("voices", [])
        if voice_list:
            # Use the first available voice
            first_voice_id = voice_list[0].get("voice_id")
            first_voice_name = voice_list[0].get("name")
            
            print(f"Using voice: {first_voice_name} (ID: {first_voice_id})")
            
            # Generate a sample text-to-speech
            sample_text = "Hello, this is a test of the ElevenLabs text to speech API."
            audio_file = text_to_speech(sample_text, first_voice_id)
            
            if audio_file:
                print(f"Text-to-speech demonstration successful. Audio saved to {audio_file}")
            else:
                print("Text-to-speech demonstration failed.")
        else:
            print("No voices available for text-to-speech demonstration.")

if __name__ == "__main__":
    main()
