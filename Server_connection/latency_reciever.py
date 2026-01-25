import asyncio
import json
from aiohttp import web
from aiortc import RTCPeerConnection, RTCDataChannel, RTCConfiguration, RTCIceServer, RTCSessionDescription

# TURN + STUN servers
ice_servers = [
    RTCIceServer(urls="stun:stun.l.google.com:19302"),
    RTCIceServer(
        urls="turn:openrelay.metered.ca:443?transport=tcp",
        username="openrelayproject",
        credential="openrelayproject"
    )
]

pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))

@pc.on("datachannel")
def on_datachannel(channel):
    print(f"Latency channel connected: {channel.label}")

    @channel.on("message")
    def on_message(message):
        # Echo back immediately
        channel.send(message)

# HTTP signaling endpoint
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

# Listen on all interfaces
web.run_app(app, host="0.0.0.0", port=8080)
