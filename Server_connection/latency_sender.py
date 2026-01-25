"""
WebRTC Latency Test - SENDER (Computer 1)

Install dependencies first:
pip install aiortc aiohttp

Usage:
python sender.py --host 0.0.0.0 --port 8080
"""

import asyncio
import time
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebRTCSender:
    def __init__(self):
        self.pc = RTCPeerConnection()
        self.channel = None
        self.latencies = []
        self.sent_times = {}
        
    async def create_offer(self):
        """Create WebRTC offer"""
        self.channel = self.pc.createDataChannel("latency-test")
        self.setup_channel_handlers()
        
        await self.pc.setLocalDescription(await self.pc.createOffer())
        await asyncio.sleep(0.1)  # Wait for ICE gathering
        
        return {
            "sdp": self.pc.localDescription.sdp,
            "type": self.pc.localDescription.type
        }
    
    def setup_channel_handlers(self):
        """Setup data channel event handlers"""
        @self.channel.on("open")
        def on_open():
            logger.info("✓ Data channel opened - Connection established!")
            logger.info("Starting latency measurements...")
            asyncio.ensure_future(self.start_latency_test())
        
        @self.channel.on("message")
        def on_message(message):
            if message.startswith("pong:"):
                # Calculate latency
                seq = message.split(":")[1]
                if seq in self.sent_times:
                    latency = (time.time() - self.sent_times[seq]) * 1000
                    self.latencies.append(latency)
                    logger.info(f"Ping {seq}: {latency:.2f} ms")
                    del self.sent_times[seq]
    
    async def start_latency_test(self, num_pings=20):
        """Send pings and measure latency"""
        await asyncio.sleep(1)  # Wait for connection to stabilize
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Sending {num_pings} pings...")
        logger.info(f"{'='*50}\n")
        
        for i in range(num_pings):
            seq = str(i)
            self.sent_times[seq] = time.time()
            self.channel.send(f"ping:{seq}")
            await asyncio.sleep(0.5)
        
        # Wait for all responses
        await asyncio.sleep(2)
        
        # Display results
        self.display_results(num_pings)
    
    def display_results(self, num_pings):
        """Display latency test results"""
        if self.latencies:
            avg = sum(self.latencies) / len(self.latencies)
            min_lat = min(self.latencies)
            max_lat = max(self.latencies)
            
            logger.info("\n" + "="*60)
            logger.info("📊 LATENCY TEST RESULTS")
            logger.info("="*60)
            logger.info(f"Packets sent:      {num_pings}")
            logger.info(f"Packets received:  {len(self.latencies)}")
            logger.info(f"Packet loss:       {((num_pings - len(self.latencies)) / num_pings * 100):.1f}%")
            logger.info(f"-" * 60)
            logger.info(f"Average latency:   {avg:.2f} ms")
            logger.info(f"Min latency:       {min_lat:.2f} ms")
            logger.info(f"Max latency:       {max_lat:.2f} ms")
            logger.info("="*60 + "\n")
        else:
            logger.warning("No responses received!")


class SignalingServer:
    def __init__(self):
        self.offer = None
        self.answer = None
    
    async def handle_offer(self, request):
        data = await request.json()
        self.offer = data
        return web.json_response({"status": "ok"})
    
    async def handle_get_offer(self, request):
        while self.offer is None:
            await asyncio.sleep(0.1)
        return web.json_response(self.offer)
    
    async def handle_answer(self, request):
        data = await request.json()
        self.answer = data
        logger.info("✓ Answer received from receiver")
        return web.json_response({"status": "ok"})
    
    async def handle_get_answer(self, request):
        while self.answer is None:
            await asyncio.sleep(0.1)
        return web.json_response(self.answer)


async def main(host="0.0.0.0", port=8080):
    """Main function to run sender"""
    # Start signaling server
    signaling = SignalingServer()
    app = web.Application()
    app.router.add_post('/offer', signaling.handle_offer)
    app.router.add_get('/offer', signaling.handle_get_offer)
    app.router.add_post('/answer', signaling.handle_answer)
    app.router.add_get('/answer', signaling.handle_get_answer)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info("="*60)
    logger.info("🚀 SENDER - WebRTC Latency Test")
    logger.info("="*60)
    logger.info(f"✓ Signaling server started on {host}:{port}")
    logger.info(f"\n📌 On the receiver computer, run:")
    logger.info(f"   python receiver.py --remote-host <THIS_COMPUTER_IP> --remote-port {port}")
    logger.info(f"\nWaiting for receiver to connect...\n")
    
    # Create offer
    rtc = WebRTCSender()
    offer = await rtc.create_offer()
    signaling.offer = offer
    
    # Wait for answer
    while signaling.answer is None:
        await asyncio.sleep(0.1)
    
    await rtc.pc.setRemoteDescription(
        RTCSessionDescription(
            sdp=signaling.answer["sdp"],
            type=signaling.answer["type"]
        )
    )
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("\n\n👋 Shutting down...")
        await rtc.pc.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="WebRTC Latency Test - Sender")
    parser.add_argument("--host", default="0.0.0.0",
                       help="Host to bind signaling server (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080,
                       help="Port for signaling server (default: 8080)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        pass