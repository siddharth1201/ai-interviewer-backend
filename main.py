import asyncio
import traceback
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv
from routes.web_sockets import websocket_server
from fastapi.middleware.cors import CORSMiddleware
from routes.uploads import router as uploads_router

load_dotenv()

# Audio settings


app = FastAPI()
app.include_router(uploads_router)
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


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