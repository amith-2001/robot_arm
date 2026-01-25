import asyncio
import json
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, RTCSessionDescription

pc = RTCPeerConnection()

@pc.on("datachannel")
def on_datachannel(channel):
    print("Latency channel connected")

    @channel.on("message")
    def on_message(message):
        # Echo back immediately
        channel.send(message)

async def start():
    async with ClientSession() as session:
        async with session.get("http://localhost:8080/offer") as resp:
            offer = await resp.json()

        await pc.setRemoteDescription(
            RTCSessionDescription(offer["sdp"], offer["type"])
        )

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        await session.post(
            "http://localhost:8080/answer",
            json={
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            }
        )

asyncio.get_event_loop().run_until_complete(start())
asyncio.get_event_loop().run_forever()
