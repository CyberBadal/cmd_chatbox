import os
import motor.motor_asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from datetime import datetime
from bson import ObjectId

app = FastAPI(title="Simple Chat Backend")

# Connect to MongoDB (adjust URI as needed)
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = client.simple_chat

# Manage active WebSocket connections per user
class ConnectionManager:
    def __init__(self):
        self.connections = {}

    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        if username not in self.connections:
            self.connections[username] = []
        self.connections[username].append(websocket)

    def disconnect(self, username: str, websocket: WebSocket):
        self.connections[username].remove(websocket)
        if not self.connections[username]:
            del self.connections[username]

    async def send_message(self, user: str, message: dict):
        # Convert ObjectId to string if present
        message["_id"] = str(message["_id"]) if "_id" in message else None
        connections = self.connections.get(user, [])
        for ws in connections:
            await ws.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{username}")
async def websocket_chat(websocket: WebSocket, username: str):
    await manager.connect(username, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # data: {"to": str, "message": str}
            to_user = data.get("to")
            message_text = data.get("message")
            timestamp = datetime.utcnow().isoformat()

            # Save message
            msg_doc = {
                "from": username,
                "to": to_user,
                "message": message_text,
                "timestamp": timestamp
            }
            result = await db.messages.insert_one(msg_doc)
            msg_doc["_id"] = result.inserted_id  # Get the inserted ObjectId

            # Send to sender and receiver if connected
            await manager.send_message(username, msg_doc)
            if to_user != username:
                await manager.send_message(to_user, msg_doc)

    except WebSocketDisconnect:
        manager.disconnect(username, websocket)

@app.get("/history/{user1}/{user2}")
async def get_history(user1: str, user2: str):
    messages = []
    cursor = db.messages.find({
        "$or": [
            {"from": user1, "to": user2},
            {"from": user2, "to": user1}
        ]
    }).sort("timestamp", 1)
    async for msg in cursor:
        msg["_id"] = str(msg["_id"])  # Convert ObjectId to string
        messages.append(msg)
    return messages

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simple-chat-backend:app", host="0.0.0.0", port=8000, reload=True)
