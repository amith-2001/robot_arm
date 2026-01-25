"""
WebRTC Latency Test - SENDER (Computer 1) - OPTIMIZED

Install dependencies first:
pip install aiortc aiohttp

Usage:
python sender.py --host 0.0.0.0 --port 8080
"""

import asyncio
import time
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebRTCSender:
    def __init__(self):
        # Configure for local network - no STUN/TURN needed
        config = RTCConfiguration(iceServers=[])
        self.pc = RTCPeerConnection(configuration=config)
        self.channel = None
        self.latencies = []
        self.sent_times = {}
        self.lock = asyncio.Lock()
        
    async def create_offer(self):
        """Create WebRTC offer"""
        # Configure data channel for low latency
        self.channel = self.pc.createDataChannel(
            "latency-test",
            ordered=True,
            maxRetransmits=0  # Don't retransmit, prioritize speed
        )
        self.setup_channel_handlers()
        
        await self.pc.setLocalDescription(await self.pc.createOffer())
        
        # Wait for ICE gathering to complete
        while self.pc.iceGatheringState != "complete":
            await asyncio.sleep(0.01)
        
        return {
            "sdp": self.pc.localDescription.sdp,
            "type": self.pc.localDescription.type
        }
    
    def setup_channel_handlers(self):
        """Setup data channel event handlers"""
        @self.channel.on("open")
        def on_open():
            logger.info("✓ Data channel opened - Connection established!")
            logger.info("Starting high-frequency latency measurements...")
            asyncio.ensure_future(self.start_latency_test())
        
        @self.channel.on("message")
        def on_message(message):
            if message.startswith("pong:"):
                # Calculate latency with high precision
                parts = message.split(":")
                seq = parts[1]
                
                if seq in self.sent_times:
                    # Use time.perf_counter for higher precision
                    latency = (time.perf_counter() - self.sent_times[seq]) * 1000
                    self.latencies.append(latency)
                    
                    # Only log every 10th ping to avoid spam
                    if len(self.latencies) % 10 == 0:
                        logger.info(f"Ping {seq}: {latency:.3f} ms (count: {len(self.latencies)})")
                    
                    del self.sent_times[seq]
    
    async def start_latency_test(self, num_pings=100, interval=0.01):
        """Send pings rapidly and measure latency"""
        await asyncio.sleep(0.5)  # Brief stabilization
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Sending {num_pings} pings with {interval*1000:.1f}ms interval...")
        logger.info(f"{'='*60}\n")
        
        start_time = time.perf_counter()
        
        for i in range(num_pings):
            seq = str(i)
            self.sent_times[seq] = time.perf_counter()
            
            try:
                self.channel.send(f"ping:{seq}")
            except Exception as e:
                logger.error(f"Failed to send ping {seq}: {e}")
            
            # Much shorter interval for rapid testing
            await asyncio.sleep(interval)
        
        # Wait for remaining responses
        await asyncio.sleep(1)
        
        total_time = time.perf_counter() - start_time
        
        # Display results
        self.display_results(num_pings, total_time)
    
    def display_results(self, num_pings, total_time):
        """Display latency test results"""
        if self.latencies:
            avg = sum(self.latencies) / len(self.latencies)
            min_lat = min(self.latencies)
            max_lat = max(self.latencies)
            
            # Calculate percentiles
            sorted_lat = sorted(self.latencies)
            p50 = sorted_lat[len(sorted_lat) // 2]
            p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
            p99 = sorted_lat[int(len(sorted_lat) * 0.99)]
            
            # Calculate jitter (variance)
            if len(self.latencies) > 1:
                variance = sum((x - avg) ** 2 for x in self.latencies) / len(self.latencies)
                jitter = variance ** 0.5
            else:
                jitter = 0
            
            logger.info("\n" + "="*60)
            logger.info("📊 LATENCY TEST RESULTS")
            logger.info("="*60)
            logger.info(f"Test duration:     {total_time:.2f} seconds")
            logger.info(f"Packets sent:      {num_pings}")
            logger.info(f"Packets received:  {len(self.latencies)}")
            logger.info(f"Packet loss:       {((num_pings - len(self.latencies)) / num_pings * 100):.1f}%")
            logger.info(f"-" * 60)
            logger.info(f"Average latency:   {avg:.3f} ms")
            logger.info(f"Median (P50):      {p50:.3f} ms")
            logger.info(f"95th percentile:   {p95:.3f} ms")
            logger.info(f"99th percentile:   {p99:.3f} ms")
            logger.info(f"Min latency:       {min_lat:.3f} ms")
            logger.info(f"Max latency:       {max_lat:.3f} ms")
            logger.info(f"Jitter (std dev):  {jitter:.3f} ms")
            logger.info("="*60 + "\n")
            
            # Diagnosis
            if avg > 50:
                logger.warning("⚠️  HIGH LATENCY DETECTED!")
                logger.warning("Possible causes:")
                logger.warning("  - Network congestion")
                logger.warning("  - CPU/system load")
                logger.warning("  - WiFi instead of wired connection")
                logger.warning("  - Firewall/NAT traversal issues")
        else:
            logger.warning("❌ No responses received!")


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
            await asyncio.sleep(0.01)
        return web.json_response(self.offer)
    
    async def handle_answer(self, request):
        data = await request.json()
        self.answer = data
        logger.info("✓ Answer received from receiver")
        return web.json_response({"status": "ok"})
    
    async def handle_get_answer(self, request):
        while self.answer is None:
            await asyncio.sleep(0.01)
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
    logger.info("🚀 SENDER - WebRTC Latency Test (OPTIMIZED)")
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
        await asyncio.sleep(0.01)
    
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
    
    parser = argparse.ArgumentParser(description="WebRTC Latency Test - Sender (Optimized)")
    parser.add_argument("--host", default="0.0.0.0",
                       help="Host to bind signaling server (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080,
                       help="Port for signaling server (default: 8080)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        pass