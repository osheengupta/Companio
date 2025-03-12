# Companio: Your AI Journaling Companion

Companio is an innovative AI journaling system that helps users maintain consistent journaling habits through natural phone conversations. The system proactively calls users at scheduled times, engages them in meaningful conversations about their day, and automatically processes these conversations into organized journal entries with concise summaries.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                             │
│                                  Daily Journal System                                       │
│                                                                                             │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌────────┐ │
│  │             │     │             │     │             │     │             │     │        │ │
│  │ ElevenLabs  │     │   Twilio    │     │ Conversation│     │ Perplexity  │     │Google  │ │
│  │  Voice AI   │────►│   Phone     │────►│ Extraction  │────►│Summarization│────►│Sheets  │ │
│  │   Agent     │     │  Service    │     │             │     │             │     │        │ │
│  │             │     │             │     │             │     │             │     │        │ │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └────────┘ │
│         │                   │                   │                   │                       │
│         │                   │                   │                   │                       │
│         │                   ▼                   │                   │                       │
│         │             ┌──────────┐              │                   │                       │
│         └────────────►│   User   │◄─────────────┘                   │                       │
│                       │          │                                  │                       │
│                       └──────────┘                                  │                       │
│                                                                     │                       │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## How It Works

1. **Scheduled Calls**: The ElevenLabs voice agent initiates calls to users at predetermined times through Twilio's telephony service.

2. **Natural Conversation**: When the user answers, they engage in a natural conversation with the AI agent about their day, thoughts, and experiences.

3. **Conversation Processing**: After the call, the system extracts the conversation text from ElevenLabs.

4. **Intelligent Summarization**: The conversation is sent to Perplexity AI, which generates a concise bullet-point summary highlighting key points, emotions, and insights.

5. **Organized Storage**: Both the full conversation and the summary are stored in Google Sheets for easy access and review.

## Features

- **Effortless Journaling**: Turn phone conversations into journal entries without any writing required
- **Natural Interaction**: Engage with an AI that asks thoughtful questions and responds empathetically
- **Intelligent Summaries**: Get concise bullet-point summaries of your journal entries
- **Organized Storage**: Access your journal entries and summaries in Google Sheets
- **Scheduled Check-ins**: Receive calls at times that work best for your schedule

## Technologies Used

### Languages
- JavaScript (Node.js)
- Python

### Frameworks & Libraries
- **Node.js**: Fastify, WebSocket, dotenv
- **Python**: Requests, Flask

### APIs & Services
- **ElevenLabs API**: Voice AI and conversation capabilities
- **Twilio API**: Phone call handling
- **Perplexity API**: Intelligent summarization using the llama-3-sonar-small-32k-online model
- **Google Sheets API**: Data storage and organization

## Setup and Installation

### Prerequisites
- Node.js and npm
- Python 3.7+
- Twilio account
- ElevenLabs account with Conversational AI access
- Perplexity API key
- Google account with Sheets API enabled

### Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/Daily-Journal.git
   cd Daily-Journal
   ```

2. **Install Node.js Dependencies**
   ```bash
   npm install
   ```

3. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the root directory with the following:
   ```
   # ElevenLabs Configuration
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ELEVENLABS_AGENT_ID=your_elevenlabs_agent_id
   
   # Twilio Configuration
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_PHONE_NUMBER=your_twilio_phone_number
   
   # Perplexity Configuration
   PERPLEXITY_API_KEY=your_perplexity_api_key
   
   # Google Sheets Configuration
   GOOGLE_CREDS_PATH=path_to_your_credentials.json
   SHEET_NAME=your_sheet_name
   ```

5. **Set Up Google Sheets Authentication**
   - Create a project in Google Cloud Console
   - Enable Google Sheets API
   - Create credentials (OAuth client ID)
   - Download the credentials JSON file and save it to the path specified in GOOGLE_CREDS_PATH

## Usage

### Starting the Server
```bash
node index copy.js
```

### Making Outbound Calls
Send a POST request to initiate a call to a user:
```bash
curl -X POST http://localhost:8000/make-outbound-call \
-H "Content-Type: application/json" \
-d '{"to": "+1234567890"}'
```

### Processing Journal Entries
After a call is completed, the system will automatically:
1. Extract the conversation from ElevenLabs
2. Generate a summary using Perplexity
3. Store the entry in Google Sheets

### Manually Processing a Specific Conversation
```bash
./summarize_journal.sh <conversation_id> --save-to-sheets
```

## System Components

### 1. ElevenLabs Voice AI
- **Main Files**: `11labs.py`
- **Purpose**: Provides the conversational AI agent that talks with users
- **Features**:
  - Initiates scheduled calls to users
  - Engages users in natural conversation about their day
  - Records and processes conversation data

### 2. Twilio Phone Service
- **Main Files**: `index.js`, `index copy.js`
- **Purpose**: Handles the telephony aspects of the system
- **Features**:
  - Makes outbound calls to users at scheduled times
  - Connects users to the ElevenLabs voice agent
  - Manages call state and telephony functions

### 3. Conversation Extraction
- **Main Files**: `perplexity_summarize.py`, `process_scraped_data.py`
- **Purpose**: Extracts and processes conversation text from ElevenLabs
- **Features**:
  - Retrieves conversation data from ElevenLabs API
  - Extracts relevant text from the conversation
  - Prepares text for summarization

### 4. Perplexity Summarization
- **Main Files**: `perplexity_summarize.py`
- **Purpose**: Summarizes journal conversations into concise bullet points
- **Features**:
  - Uses Perplexity API (llama-3-sonar-small-32k-online model)
  - Generates bullet-point summaries of conversations
  - Extracts key emotions, events, and insights

### 5. Google Sheets Storage
- **Main Files**: `sheets.py`
- **Purpose**: Stores journal entries and summaries
- **Features**:
  - Formats data for Google Sheets
  - Saves journal entries and summaries
  - Provides organized storage for reviewing journal history

## Future Development

- **Personalized Insights**: Implementing advanced analytics to provide users with personalized insights about their emotional patterns and well-being
- **Multi-Modal Access**: Expanding beyond phone calls to allow journaling through text messages, voice assistants, and a dedicated app
- **Custom Voice Agents**: Allowing users to customize their AI journaling companion's personality, questioning style, and voice
- **Integration with Health Apps**: Connecting with health and wellness apps to provide a more holistic view of mental and physical well-being

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- ElevenLabs for providing the voice AI technology
- Twilio for the telephony services
- Perplexity AI for the summarization capabilities
- The open-source community for the various libraries and tools used in this project
