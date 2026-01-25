
import asyncio
import json
import time
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

pc = RTCPeerConnection()

channel = pc.createDataChannel(
    "latency",
    ordered=False,
    maxRetransmits=0
)

@channel.on("open")
async def on_open():
    print("Latency channel open")
    while True:
        t0 = time.time()
        msg = {"t0": t0}
        channel.send(json.dumps(msg))
        await asyncio.sleep(0.1)  # 10 Hz ping

@channel.on("message")
def on_message(message):
    data = json.loads(message)
    t0 = data["t0"]
    rtt = (time.time() - t0) * 1000
    print(f"RTT: {rtt:.2f} ms | One-way ≈ {rtt/2:.2f} ms")

async def offer(request):
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })

async def answer(request):
    data = await request.json()
    await pc.setRemoteDescription(
        RTCSessionDescription(data["sdp"], data["type"])
    )
    return web.Response(text="OK")

app = web.Application()
app.router.add_get("/offer", offer)
app.router.add_post("/answer", answer)

web.run_app(app, port=8080)
