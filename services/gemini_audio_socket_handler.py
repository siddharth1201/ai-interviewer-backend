import time
import os
import asyncio
import traceback
import json
import websockets
import base64
from services.prompts import agent_prompt
from config.config import client, CONFIG, MODEL


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

