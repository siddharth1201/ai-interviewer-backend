# Modified websocket handler
import json
import os

import websockets

from services.interview_state import interview_state
from services.gemini_audio_socket_handler import GeminiAudioWebSocketHandler


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