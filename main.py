import os
import asyncio
import traceback
import json
import websockets
import base64
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from pathlib import Path
import uvicorn
from google import genai
from google.genai import types
from dotenv import load_dotenv
from services.gemini_script import InterviewQuestionGenerator, ResumeAnalyzer
from services.prompts import agent_prompt
from services.final_prompt import create_final_prompt
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# Audio settings
FORMAT = "int16"  # Format now as string since we're not using PyAudio directly
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.0-flash-live-001"

# Initialize Gemini client
client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)

# Define tools for Gemini
tools = [
    types.Tool(google_search=types.GoogleSearch()),
]

# Configuration for audio-only mode
from google.genai import types

CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
        )
    ),
    realtime_input_config=types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            disabled=False,
            start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
            end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
            prefix_padding_ms=100,
            silence_duration_ms=1000,
        )
    ),
    tools=tools,
)


# Create temp directories
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)
(TEMP_DIR / "resume").mkdir(exist_ok=True)
(TEMP_DIR / "jd").mkdir(exist_ok=True)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class InterviewState:
    def __init__(self):
        self.resume_path = None
        self.jd_path = None
        self.final_prompt = None
        self.candidate_name = None
        self.analyzer = ResumeAnalyzer(os.environ.get("OPENAI_API_KEY"))
        self.qa_generator = InterviewQuestionGenerator()

    async def prepare_interview(self, candidate_name):
        """Prepare the interview by analyzing resume and JD"""
        try:
            self.candidate_name = candidate_name
            # Parse and analyze documents
            resume_text = self.analyzer.parse_pdf(str(self.resume_path))
            jd_text = self.analyzer.parse_pdf(str(self.jd_path))
            analysis = self.analyzer.analyze_resume(resume_text)
            
            questions = self.analyzer.generate_questions(
                analysis=analysis,
                job_description=jd_text,
                interviewer_role="SD1",
                difficulty="hard"
            )

            # Get role specific information
            role = "SD1"
            role_specific_guidelines = self.qa_generator.role_specific_guidelines[role]
            role_personality = self.qa_generator.role_personalities[role]
            question_focus = self.qa_generator.question_focus[role]
            interviewer_details = self.qa_generator.interviewer_details[role]
            mandatory_questions = self.qa_generator.mandatory_questions[role]
            role_perspective = self.qa_generator.define_role_perspective(role)

            # Create final prompt with candidate name
            self.final_prompt = create_final_prompt(
                agent_prompt,
                role,
                15,  # minutes
                self.candidate_name,  # Using provided name
                "Interview for Software Development Engineer 1 position",
                role_specific_guidelines,
                role_personality,
                question_focus,
                interviewer_details,
                mandatory_questions,
                questions,
                role_perspective
            )
            #write final prompt to file
            with open(TEMP_DIR / "final_prompt.txt", "w") as f:
                f.write(self.final_prompt)
            return True
        
            
        
        except Exception as e:
            print(f"Error preparing interview: {e}")
            traceback.print_exc()
            return False

# Global interview state
interview_state = InterviewState()

@app.post("/upload/resume")
async def upload_resume(file: UploadFile = File(...)):
    try:
        file_path = TEMP_DIR / "resume" / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        interview_state.resume_path = file_path
        return JSONResponse(content={"status": "success", "path": str(file_path)})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.post("/upload/jd")
async def upload_jd(file: UploadFile = File(...)):
    try:
        file_path = TEMP_DIR / "jd" / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        interview_state.jd_path = file_path
        return JSONResponse(content={"status": "success", "path": str(file_path)})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

import time
class GeminiAudioWebSocketHandler:
    def __init__(self, websocket, initial_prompt=agent_prompt, gain=1.0):
        self.websocket = websocket
        self.audio_in_queue = asyncio.Queue()
        self.out_queue = asyncio.Queue(maxsize=10000)
        self.session = None
        self.initial_prompt = initial_prompt
        self.gain = gain
        self.active = True
        self.last_audio_time = time.time()


    async def apply_gain(self, data, gain):
        """Applies a gain factor to the audio data."""
        if gain == 1.0:
            return data
        
        import numpy as np
        # Convert the base64 data to a numpy array of integers
        audio_bytes = base64.b64decode(data)
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)

        # Apply the gain, clipping to avoid overflow
        audio_array = (audio_array * gain).astype(np.int16)

        # Convert back to base64
        return base64.b64encode(audio_array.tobytes()).decode('utf-8')

    async def send_audio_to_gemini(self):
        """Background task to read audio from the websocket and send it to Gemini"""
        try:
            while self.active:
                msg = await self.out_queue.get()
                await self.session.send_realtime_input(audio=msg)
        except Exception as e:
            print(f"Error in send_audio_to_gemini: {e}")
            traceback.print_exc()

    async def receive_from_gemini(self):
        """Background task to read from Gemini and forward to the websocket"""
        try:
            while self.active:
                turn = self.session.receive()
                async for response in turn:
                    response_data = {}
                    
                    if data := response.data:
                        # Debug info
                        print(f"Received audio data from Gemini: {len(data)} bytes")
                        
                        # Convert binary audio data to base64 for WebSocket transmission
                        audio_base64 = base64.b64encode(data).decode('utf-8')
                        response_data['audio'] = audio_base64
                    
                    if text := response.text:
                        response_data['text'] = text
                        print(f"Response text: {text}")
                    
                    if response_data:
                        await self.websocket.send(json.dumps(response_data))
                        print(f"Sent message to client: {len(response_data.get('audio', ''))} bytes audio, {len(response_data.get('text', ''))} chars text")

                # If you interrupt the model, it sends a turn_complete.
                # For interruptions to work, we need to notify the client
                await self.websocket.send(json.dumps({"turn_complete": True}))
                print("Turn complete signal sent to client")
        except Exception as e:
            print(f"Error in receive_from_gemini: {e}")
            traceback.print_exc()

    async def handle_websocket_messages(self):
        """Process incoming messages from the WebSocket client"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    # Handle text messages
                    if "text" in data:
                        text = data["text"]
                        print(f"Received text: {text}")
                        
                        # Check if this is a command to end the session
                        if text.lower() == "q":
                            self.active = False
                            await self.websocket.send(json.dumps({"command": "session_ended"}))
                            break
                            
                        await self.session.send(input=text, end_of_turn=True)
                    
                    # Handle audio data
                    elif "audio" in data:
                        audio_data = data["audio"]  # Should be base64 encoded
                        
                            # Update the timestamp
                        self.last_audio_time = time.time()
                        # Apply gain if needed
                        if self.gain != 1.0:
                            audio_data = await self.apply_gain(audio_data, self.gain)
                        
                        # Send to Gemini
                        await self.out_queue.put({
                            "data": base64.b64decode(audio_data), 
                            "mime_type": "audio/pcm"
                        })
                    
                    # Handle client-side commands
                    elif "command" in data:
                        if data["command"] == "interrupt":
                            # Implement interruption logic if needed
                            pass
                
                except json.JSONDecodeError:
                    print("Received non-JSON message")
                except Exception as e:
                    print(f"Error processing message: {e}")
                    traceback.print_exc()
        
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
        except Exception as e:
            print(f"Error in handle_websocket_messages: {e}")
            traceback.print_exc()
        finally:
            self.active = False

    async def monitor_silence(self):
        """Monitor for prolonged silence and signal end of speech."""
        try:
            while self.active:
                await asyncio.sleep(0.5)  # Check every 0.5 seconds
                time_since_last_audio = time.time() - self.last_audio_time
                if time_since_last_audio > 2.0:  # 2 seconds threshold
                    print("Detected 2 seconds of silence. Signaling end of speech.")
                    msg = await self.out_queue.get()
                    await self.session.send_realtime_input(audio=msg)
                    await self.session.send_realtime_input(audio_stream_end=True)
                    self.last_audio_time = time.time()  # Reset to prevent repeated signals
        except Exception as e:
            print(f"Error in monitor_silence: {e}")
            traceback.print_exc()



    async def run(self):
        """Main handler for a WebSocket connection"""
        try:
            async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
                self.session = session
                
                # Send initial prompt if provided
                if self.initial_prompt:
                    print("Sending initial prompt to Gemini...")
                    await self.session.send(input=self.initial_prompt, end_of_turn=True)
                    print("Initial prompt sent.")
                    
                # Notify client that we're ready
                await self.websocket.send(json.dumps({"status": "ready"}))
                
                # Create tasks for handling audio streams
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.send_audio_to_gemini())
                    tg.create_task(self.receive_from_gemini())
                    tg.create_task(self.handle_websocket_messages())
                    tg.create_task(self.monitor_silence())
        except asyncio.CancelledError:
            print("Session cancelled")
        except Exception as e:
            print(f"Error in WebSocket handler: {e}")
            traceback.print_exc()
            error_msg = {"error": str(e)}
            try:
                await self.websocket.send(json.dumps(error_msg))
            except:
                pass
        finally:
            self.active = False
            print("WebSocket handler finished")

# Modified websocket handler
async def websocket_handler(websocket):
    """Handler for new WebSocket connections"""
    print(f"New WebSocket connection from {websocket.remote_address}")
    
    # Parse query parameters
    query_params = {}
    path = websocket.request.path if hasattr(websocket, 'request') else ''
    print(f"Path: {path}")
    
    if "?" in path:
        base_path, query_string = path.split("?", 1)
        for param in query_string.split("&"):
            if "=" in param:
                key, value = param.split("=", 1)
                query_params[key] = value
    
    # Get gain parameter and candidate name
    gain = float(query_params.get("gain", 1.0))
    candidate_name = query_params.get("name")
    
    if not candidate_name:
        await websocket.send(json.dumps({
            "error": "Candidate name is required"
        }))
        return
    
    # Check if both files are uploaded
    if not interview_state.resume_path or not interview_state.jd_path:
        await websocket.send(json.dumps({
            "error": "Please upload both resume and JD before connecting"
        }))
        return
    
    # Prepare interview with candidate name
    print(f"Preparing interview for {candidate_name}...")
    success = await interview_state.prepare_interview(candidate_name)
    if not success:
        await websocket.send(json.dumps({
            "error": "Failed to prepare interview"
        }))
    else:
        await websocket.send(json.dumps({
            "success": "Interview prepared successfully"
        }))    
    

    # Create handler with prepared prompt
    handler = GeminiAudioWebSocketHandler(websocket, initial_prompt=interview_state.final_prompt, gain=gain)
    await handler.run()

async def websocket_server():
    host = os.environ.get("WEBSOCKET_HOST", "localhost")
    port = int(os.environ.get("WEBSOCKET_PORT", 8765))
    
    print("\n=== WebSocket Server Configuration ===")
    print(f"Starting WebSocket server on ws://{host}:{port}")
    print("=====================================\n")
    
    server = await websockets.serve(websocket_handler, host, port)
    print(f"WebSocket server is running on ws://{host}:{port}")
    await server.wait_closed()

async def main():
    print("\n=== Starting AI Interviewer Server ===")
    
    # Run both FastAPI and WebSocket server
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=8000, 
        loop="asyncio",
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    print("\n=== FastAPI Server Configuration ===")
    print(f"Starting FastAPI server on http://0.0.0.0:8000")
    print("===================================\n")
    
    try:
        await asyncio.gather(
            server.serve(),
            websocket_server()
        )
    except Exception as e:
        print(f"Server error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())