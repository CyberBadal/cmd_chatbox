import asyncio
import websockets
import json
import sys

async def send_messages(websocket, username):
    while True:
        try:
            message_text = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            message_text = message_text.strip()
            if not message_text:
                continue

            # Example: To send a message to a user, format input like: recipient_username: message_text
            if ":" not in message_text:
                print("Invalid format. Use: recipient_username: message")
                continue

            to_user, message = message_text.split(":", 1)
            to_user = to_user.strip()
            message = message.strip()

            message_data = {
                "to": to_user,
                "message": message
            }
            await websocket.send(json.dumps(message_data))
        except Exception as e:
            print(f"Error sending message: {e}")
            break

async def receive_messages(websocket, username):
    try:
        async for message in websocket:
            print(f"\nReceived: {message}\n> ", end="", flush=True)
    except websockets.exceptions.ConnectionClosed:
        print("\nConnection closed.")

async def chat_client(username):
    uri = f'ws://localhost:8000/ws/{username}'
    async with websockets.connect(uri) as websocket:
        print(f"Connected as {username}. You can chat now!")
        print("Send messages in format: recipient_username: your message")
        print("Type your messages below:")

        send_task = asyncio.create_task(send_messages(websocket, username))
        receive_task = asyncio.create_task(receive_messages(websocket, username))

        done, pending = await asyncio.wait(
            [send_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

if __name__ == "__main__":
    username = input("Enter your username: ")
    try:
        asyncio.run(chat_client(username))
    except KeyboardInterrupt:
        print("\nChat client closed.")
