import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger("rootlens.websocket")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """
        Broadcast JSON message payload to all active clients.
        """
        if not self.active_connections:
            return
        
        logger.debug(f"Broadcasting message: {message}")
        inactive_sockets = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send websocket message, flagging socket: {str(e)}")
                inactive_sockets.append(connection)

        # Clean up dead sockets
        for socket in inactive_sockets:
            self.disconnect(socket)

manager = ConnectionManager()
