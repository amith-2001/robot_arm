import asyncio
import time
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription

pc = RTCPeerConnection()
channel = None
sent_times = {}

def on_datachannel(ch):
    global channel
    channel = ch
    
    @channel.on("open")
    def on_open():
        print("✓ Connected")
        asyncio.ensure_future(send_pings())
    
    @channel.on("message")
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

async def main(host):
    pc.on("datachannel", on_datachannel)
    
    async with aiohttp.ClientSession() as session:
        # Get offer
        async with session.get(f"http://{host}:8080/offer") as resp:
            offer = await resp.json()
        
        # Create answer
        await pc.setRemoteDescription(RTCSessionDescription(
            sdp=offer["sdp"], type=offer["type"]))
        await pc.setLocalDescription(await pc.createAnswer())
        
        while pc.iceGatheringState != "complete":
            await asyncio.sleep(0.01)
        
        # Send answer
        answer = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        async with session.post(f"http://{host}:8080/answer", json=answer) as resp:
            await resp.json()
        
        print("Peer 2 connected")
        await asyncio.Event().wait()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    args = parser.parse_args()
    
    asyncio.run(main(args.host))