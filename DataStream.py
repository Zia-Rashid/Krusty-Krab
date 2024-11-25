import asyncio
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataStream")

class Datastream:
    def __init__(self, uri):
        self.uri = uri
        self.connection = None    


    async def connect(self):
        try:
            self.connection = await websockets.connect(self.uri)
            logger.info(f"Connected to the {self.uri}")
        except Exception as e:
            logger.error(f"Error connecting to {self.uri}: {e}")
            self.connection = None

    async def send_data(self, data):
        if self.connection:
            try:
                await self.connection.send(data)
                logger.info(f"Send data: {data}")
            except Exception as e:
                logger.error(f"Failed to sent data: {e}")
        else:
            logger.warning("No connection established. Unable to send data.")
            asyncio.sleep(2)
            

    async def receive_data(self):
        if self.connection:
            try:
                data = await self.connection.recv()
                logger.info(f"Reveived data: {data}")
                return data
            except Exception as e:
                logger.error(f"Error receiving data: {e}")
                return None
        else:
            logger.warning("No connection established. Unable to receive data.")
            return None

    async def close(self):
        if self.connection:
            try:
                await self.connection.close()
                logger.info("Websocket connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

    async def connect_with_retries(self, retries=5, delay=2):
        for attempt in range(retries):
            await self.connect()
            if self.connection:
                logger.info("Websocket connection established")
                return True
            logger.warning(f"Retrying connection in {delay} seconds")
            await asyncio.sleep(delay)
        logger.error("Max tries reached. Could not connect to WebSocket.")
        return False
    

#Main function to run the WebSocket connection
async def main():
        datastream = Datastream("wss://paper-api.alpaca.markets/stream")
        await datastream.connect()

        #Send a sample message
        await datastream.send_data("Hello, Server!")
        
        #Receiving a response
        response = await datastream.receive_data()
        if response:
            print(response)
        
        await datastream.close()

if __name__ == "__main__":
    asyncio.run(main())