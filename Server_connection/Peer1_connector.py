import asyncio
import time
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiohttp import web

pc = RTCPeerConnection()
channel = None
sent_times = {}

# Signaling
offer_data = None
answer_data = None

async def get_offer(request):
    while not offer_data:
        await asyncio.sleep(0.01)
    return web.json_response(offer_data)

async def post_answer(request):
    global answer_data
    answer_data = await request.json()
    return web.json_response({"ok": True})

# Data channel handlers
def on_open():
    print("✓ Connected")
    asyncio.ensure_future(send_pings())

def on_message(msg):
    if msg.startswith("pong:"):
        seq = msg.split(":")[1]
        if seq in sent_times:
            latency = (time.perf_counter() - sent_times[seq]) * 1000
            print(f"Latency: {latency:.2f} ms")
            del sent_times[seq]
    elif msg.startswith("ping:"):
        # Respond to peer's pings
        channel.send(msg.replace("ping:", "pong:"))

async def send_pings():
    await asyncio.sleep(1)
    for i in range(50):
        seq = str(i)
        sent_times[seq] = time.perf_counter()
        channel.send(f"ping:{seq}")
        await asyncio.sleep(0.1)

async def main():
    global offer_data, channel
    
    # Create data channel
    channel = pc.createDataChannel("data")
    channel.on("open", on_open)
    channel.on("message", on_message)
    
    # Create offer
    await pc.setLocalDescription(await pc.createOffer())
    while pc.iceGatheringState != "complete":
        await asyncio.sleep(0.01)
    
    offer_data = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    
    # Start signaling server
    app = web.Application()
    app.router.add_get('/offer', get_offer)
    app.router.add_post('/answer', post_answer)
    
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8080).start()
    
    print("Peer 1 ready on port 8080")
    print("Run on Peer 2: python peer2.py --host <THIS_IP>")
    
    # Wait for answer
    while not answer_data:
        await asyncio.sleep(0.1)
    
    await pc.setRemoteDescription(RTCSessionDescription(
        sdp=answer_data["sdp"], type=answer_data["type"]))
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())