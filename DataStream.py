import asyncio
import websockets
import websockets.connection

# connected_clients = set()

class Datastream:
    def __init__(self, uri):
        self.uri = uri
        self.connection = None    


    async def connect(self):
        try:
            self.connection = await websockets.connect(self.uri)
            print(f"Connected to the {self.uri}")
        except Exception as e:
            print(f"Error connecting to {self.uri}: {e}")

    async def send_data(self, data):
        if self.connection:
            await self.connection.send(data)
        else:
            print("No connection established")

    async def receive_data(self):
        if self.connection:
            return await self.connection.recv()
        else:
            print("No connection established")

    async def close(self):
        if self.connection:
            await self.connection.close()
            print("Connection closed")
    

#Main function to run the WebSocket connection
async def main():
        datastream = Datastream("wss://paper-api.alpaca.markets/stream")
        await datastream.connect()

        #Send a sample message
        await datastream.send_data("Hello, Server!")
        
        #Receiving a response
        response = await datastream.receive_data()
        print(response)
        
        await datastream.close()

if __name__ == "__main__":
    asyncio.run(main())