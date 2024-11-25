import asyncio
import websockets
import websockets.connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataStream")

class Datastream:
    def __init__(self, uri):
        self.uri = uri
        self.connection = None    


    async def is_connected(self):
        return self.connection


    async def connect(self):
        try:
            self.connection = await websockets.connect(self.uri)
            logger.info(f"Connected to the {self.uri}")
        except Exception as e:
            logger.error(f"Error connecting to {self.uri}: {e}")

    async def send_data(self, data):
        if self.connection:
            await self.connection.send(data)
        else:
            logger.warning("No connection established")

    async def receive_data(self):
        if self.connection:
            return await self.connection.recv()
        else:
            logger.warning("No connection established")

    async def close(self):
        if self.connection:
            await self.connection.close()
            logger.info("Websocket connection closed")

    async def connect_with_retries(self, retries=5, delay=2):
        for attempt in range(retries):
            try:
                await self.connect()
                logger.info("Websocket connection established")
                return True
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
        logger.error("Max retries reached. Could not connect to WebSocket.")
        return False

    

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