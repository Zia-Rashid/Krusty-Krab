import asyncio
import websockets  
import json

async def handle_connection(websockets, path):
    print(f"Client connected")
    try:
        async for message in websockets:
            # Log received data
            print(f"Received: {message}")
            
            # Optionally, send a response back to the client
            response = {"status": "success", "received_data": message}
            await websockets.send(json.dumps(response))
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in connection handler: {e}")

async def main():
    # Start the WebSocket server on localhost:8080
    server = await websockets.serve(handle_connection, "0.0.0.0", 8080)
    print("Server is running on ws://localhost:8080" )
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
