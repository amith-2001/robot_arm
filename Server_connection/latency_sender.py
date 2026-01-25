import asyncio
import json
import time
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, RTCConfiguration, RTCIceServer, RTCSessionDescription

# TURN + STUN
ice_servers = [
    RTCIceServer(urls="stun:stun.l.google.com:19302"),
    RTCIceServer(
        urls="turn:openrelay.metered.ca:443?transport=tcp",
        username="openrelayproject",
        credential="openrelayproject"
    )
]

pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))

channel = pc.createDataChannel(
    "latency",
    ordered=False,
    maxRetransmits=0
)

@channel.on("open")
async def on_open():
    print("Latency channel open. Starting pings...")
    while True:
        t0 = time.time()
        channel.send(json.dumps({"t0": t0}))
        await asyncio.sleep(0.1)  # 10 Hz ping

@channel.on("message")
def on_message(message):
    data = json.loads(message)
    t0 = data["t0"]
    rtt = (time.time() - t0) * 1000
    print(f"RTT: {rtt:.2f} ms | One-way ≈ {rtt/2:.2f} ms")

async def main():
    server_ip = "SERVER_PUBLIC_OR_LAN_IP"  # Receiver’s IP visible to your laptop
    async with ClientSession() as session:
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        async with session.post(f"http://{server_ip}:8080/offer", json={
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }) as resp:
            answer = await resp.json()

        await pc.setRemoteDescription(
            RTCSessionDescription(answer["sdp"], answer["type"])
        )

asyncio.get_event_loop().run_until_complete(main())
asyncio.get_event_loop().run_forever()
