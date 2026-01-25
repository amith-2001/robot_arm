import asyncio
import json
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer

# Use a STUN server for NAT traversal
pc = RTCPeerConnection(
    configuration=RTCConfiguration(
        iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")]
    )
)

@pc.on("datachannel")
def on_datachannel(channel):
    print(f"Latency channel connected: {channel.label}")

    @channel.on("message")
    def on_message(message):
        # Echo back immediately
        channel.send(message)

# HTTP signaling endpoints
async def offer(request):
    data = await request.json()
    offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })

app = web.Application()
app.router.add_post("/offer", offer)

# Run server on all interfaces so laptop can reach
web.run_app(app, host="0.0.0.0", port=8080)
