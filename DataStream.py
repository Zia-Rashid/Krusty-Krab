import asyncio
import websockets

connected_clients = set()

async def handler(websocket, path):
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            print(f"Received: {message}")  # Log incoming messages if needed.
            # Relay the message to all connected clients.
            for client in connected_clients:
                if client != websocket:  # Avoid echoing back.
                    await client.send(message)
    except websockets.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)

async def main():
    async with websockets.serve(handler, "localhost", 8080):
        print("Local WebSocket server running on ws://localhost:8080")
        await asyncio.Future()  # Keep running.

if __name__ == "__main__":
    asyncio.run(main())
