import Fastify from "fastify";
import WebSocket from "ws";
import dotenv from "dotenv";
import fastifyFormBody from "@fastify/formbody";
import fastifyWs from "@fastify/websocket";
import Twilio from "twilio";
import { exec } from "child_process";
import fs from "fs";
import path from "path";

// Load environment variables from .env file
dotenv.config();

const {
  ELEVENLABS_AGENT_ID,
  TWILIO_ACCOUNT_SID,
  TWILIO_AUTH_TOKEN,
  TWILIO_PHONE_NUMBER,
} = process.env;

// Check for the required environment variables
if (!ELEVENLABS_AGENT_ID || !TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN || !TWILIO_PHONE_NUMBER) {
  console.error("Missing required environment variables");
  process.exit(1);
}

// Initialize Fastify server
const fastify = Fastify();
fastify.register(fastifyFormBody);
fastify.register(fastifyWs);

// Initialize Twilio client
const twilioClient = Twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

// Log Twilio client initialization (without exposing full credentials)
console.log(`[Twilio] Client initialized with Account SID: ${TWILIO_ACCOUNT_SID.substring(0, 6)}...`);

const PORT = process.env.PORT || 8000;

// Root route for health check
fastify.get("/", async (_, reply) => {
  reply.send({ message: "Server is running" });
});

// Route to handle incoming calls from Twilio
fastify.all("/incoming-call-eleven", async (request, reply) => {
  // Determine the protocol (ws or wss) based on the request
  const protocol = request.headers['x-forwarded-proto'] === 'https' ? 'wss' : 'ws';
  
  // Generate TwiML response to connect the call to a WebSocket stream
  const twimlResponse = `<?xml version="1.0" encoding="UTF-8"?>
    <Response>
      <Connect>
        <Stream url="${protocol}://${request.headers.host}/media-stream" />
      </Connect>
    </Response>`;

  reply.type("text/xml").send(twimlResponse);
});

// WebSocket route for handling media streams from Twilio
fastify.register(async (fastifyInstance) => {
  fastifyInstance.get("/media-stream", { websocket: true }, (connection, req) => {
    console.info("[Server] Twilio connected to media stream.");

    let streamSid = null;

    // Connect to ElevenLabs Conversational AI WebSocket
    const elevenLabsWs = new WebSocket(
      `wss://api.elevenlabs.io/v1/convai/conversation?agent_id=${ELEVENLABS_AGENT_ID}`
    );

    elevenLabsWs.on("open", () => {
      console.log("[II] Connected to Conversational AI.");
    });

    elevenLabsWs.on("message", (data) => {
      try {
        const message = JSON.parse(data);
        handleElevenLabsMessage(message, connection);
      } catch (error) {
        console.error("[II] Error parsing message:", error);
      }
    });

    elevenLabsWs.on("error", (error) => {
      console.error("[II] WebSocket error:", error);
    });

    elevenLabsWs.on("close", () => {
      console.log("[II] Disconnected.");
    });

    const handleElevenLabsMessage = (message, connection) => {
      switch (message.type) {
        case "conversation_initiation_metadata":
          console.info("[II] Received conversation initiation metadata.");
          break;
        case "audio":
          if (message.audio_event?.audio_base_64) {
            const audioData = {
              event: "media",
              streamSid,
              media: {
                payload: message.audio_event.audio_base_64,
              },
            };
            connection.send(JSON.stringify(audioData));
          }
          break;
        case "interruption":
          connection.send(JSON.stringify({ event: "clear", streamSid }));
          break;
        case "ping":
          if (message.ping_event?.event_id) {
            const pongResponse = {
              type: "pong",
              event_id: message.ping_event.event_id,
            };
            elevenLabsWs.send(JSON.stringify(pongResponse));
          }
          break;
      }
    };

    connection.on("message", async (message) => {
      try {
        const data = JSON.parse(message);
        switch (data.event) {
          case "start":
            streamSid = data.start.streamSid;
            console.log(`[Twilio] Stream started with ID: ${streamSid}`);
            break;
          case "media":
            if (elevenLabsWs.readyState === WebSocket.OPEN) {
              const audioMessage = {
                user_audio_chunk: Buffer.from(data.media.payload, "base64").toString("base64"),
              };
              elevenLabsWs.send(JSON.stringify(audioMessage));
            }
            break;
          case "stop":
            elevenLabsWs.close();
            break;
          default:
            console.log(`[Twilio] Received unhandled event: ${data.event}`);
        }
      } catch (error) {
        console.error("[Twilio] Error processing message:", error);
      }
    });

    connection.on("close", () => {
      elevenLabsWs.close();
      console.log("[Twilio] Client disconnected");
    });

    connection.on("error", (error) => {
      console.error("[Twilio] WebSocket error:", error);
      elevenLabsWs.close();
    });
  });
});

// Route to initiate a journal call
fastify.post("/start-journal-entry", async (request, reply) => {
  const { to } = request.body; // Your phone number

  if (!to) {
    return reply.status(400).send({ error: "Your phone number is required" });
  }

  try {
    // For local testing, we need a public URL that Twilio can access
    // The user should run ngrok http 8000 in a separate terminal
    // and replace localhost:8000 with the ngrok URL
    
    // Check if we're using localhost or a public URL
    const host = request.headers.host;
    const isLocalhost = host.includes('localhost') || host.includes('127.0.0.1');
    
    if (isLocalhost) {
      console.warn("[Warning] You are using localhost. For Twilio to connect to your ElevenLabs agent, you need a public URL.");
      console.warn("[Warning] Please run 'ngrok http 8000' in a separate terminal and update your request to use the ngrok URL.");
    }
    
    // Use the webhook URL that connects to the ElevenLabs agent
    const call = await twilioClient.calls.create({
      url: `http://${request.headers.host}/incoming-call-eleven`,
      to: to,
      from: TWILIO_PHONE_NUMBER,
    });

    console.log(`[Twilio] Journal call initiated: ${call.sid}`);
    reply.send({ message: "Journal call initiated", callSid: call.sid });
  } catch (error) {
    console.error("[Twilio] Error initiating call:", error);
    // Add more detailed error information
    console.error(`[Twilio] Error details: Status: ${error.status}, Code: ${error.code}`);
    console.error(`[Twilio] More info: ${error.moreInfo}`);
    reply.status(500).send({ 
      error: "Failed to initiate call", 
      details: {
        status: error.status,
        code: error.code,
        moreInfo: error.moreInfo
      } 
    });
  }
});

// Route to handle webhook calls from ElevenLabs
fastify.post("/webhook/journal-entries", async (request, reply) => {
  console.log("[ElevenLabs] Received webhook for journal entry");
  
  try {
    // Log the raw request body for debugging
    if (process.env.DEBUG === "true") {
      console.log("[ElevenLabs] Webhook payload:", JSON.stringify(request.body, null, 2));
    }
    
    // Process and save the journal data
    await processJournalData(request.body);
    
    // Return success response
    reply.code(200).send({ success: true, message: "Journal entry received and processed" });
  } catch (error) {
    console.error("[ElevenLabs] Error processing webhook:", error);
    reply.code(500).send({ success: false, error: error.message });
  }
});

// Function to process journal data from ElevenLabs webhook
async function processJournalData(journalData) {
  try {
    // Create a temporary JSON file with the journal data
    const tempDir = path.join(process.cwd(), "temp");
    
    // Create temp directory if it doesn't exist
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir);
    }
    
    const tempFile = path.join(tempDir, `journal_data_${Date.now()}.json`);
    
    // Write journal data to temporary file
    fs.writeFileSync(tempFile, JSON.stringify(journalData, null, 2));
    
    console.log(`[ElevenLabs] Journal data saved to ${tempFile}`);
    
    // Run the Python script to process the journal data
    return new Promise((resolve, reject) => {
      exec(`python sheets.py --webhook-data "${tempFile}"`, (error, stdout, stderr) => {
        if (error) {
          console.error(`[Python] Error: ${error.message}`);
          reject(error);
          return;
        }
        
        if (stderr) {
          console.error(`[Python] stderr: ${stderr}`);
        }
        
        console.log(`[Python] stdout: ${stdout}`);
        
        // Clean up the temporary file
        try {
          fs.unlinkSync(tempFile);
        } catch (unlinkError) {
          console.error(`[ElevenLabs] Error removing temp file: ${unlinkError.message}`);
        }
        
        resolve(stdout);
      });
    });
  } catch (error) {
    console.error("[ElevenLabs] Error processing journal data:", error);
    throw error;
  }
}

// Start the Fastify server
fastify.listen({ port: PORT }, (err) => {
  if (err) {
    console.error("Error starting server:", err);
    process.exit(1);
  }
  console.log(`[Server] Listening on port ${PORT}`);
});
