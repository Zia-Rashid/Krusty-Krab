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


    async def keep_alive(self):
        """
        Pings to prevent connection timeout
        """
        while self.running:
            try:
                if self.connection and not self.connection.closed:
                    await self.connection.ping()
                    logger.info("Ping sent to keep connection alive.")
            except Exception as e:
                logger.error(f"Error sending ping: {e}")
            await asyncio.sleep(30)  # Send a ping every 30 seconds


    async def send_data(self, data):
        """
        send requests(Trade/Connection) to AlpacaAPI
        """
        if self.connection and not self.connection.closed:
            try:
                await self.connection.send(data)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed while sending data. Reconnecting...")
                await self.connect_with_retries()
            except Exception as e:
                logger.error(f"Error sending data: {e}")
                

    async def receive_data(self):
        """
        receive data from AlpacaAPI
        """
        if self.connection and not self.connection.closed:
            try:
                return await self.connection.recv()
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed while receiving data. Reconnecting...")
                await self.connect_with_retries()
            except Exception as e:
                logger.error(f"Error receiving data: {e}")
        return None

    async def close(self):
        if self.connection:
            try:
                await self.connection.close()
                logger.info("Websocket connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

    async def connect_with_retries(self, retries=5, delay=2):
        """
        will now check to see if there are already existing connections established
        """
        for attempt in range(retries):
            if self.connection and not self.connection.closed:
                logger.info("Connection already established.")
                return True
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