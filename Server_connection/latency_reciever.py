"""
WebRTC Latency Test - RECEIVER (Computer 2) - OPTIMIZED

Install dependencies first:
pip install aiortc aiohttp

Usage:
python receiver.py --remote-host <SENDER_IP> --remote-port 8080
"""

import asyncio
import logging
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebRTCReceiver:
    def __init__(self):
        # Configure for local network - no STUN/TURN needed
        config = RTCConfiguration(iceServers=[])
        self.pc = RTCPeerConnection(configuration=config)
        self.channel = None
        self.ping_count = 0
        
    async def create_answer(self, offer):
        """Create WebRTC answer"""
        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer["sdp"], type=offer["type"])
        )
        
        @self.pc.on("datachannel")
        def on_datachannel(channel):
            logger.info(f"✓ Data channel received: {channel.label}")
            self.channel = channel
            self.setup_channel_handlers()
        
        await self.pc.setLocalDescription(await self.pc.createAnswer())
        
        # Wait for ICE gathering
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
            logger.info("Ready to receive pings and respond immediately...\n")
        
        @self.channel.on("message")
        def on_message(message):
            if message.startswith("ping:"):
                # Respond immediately with minimal processing
                self.ping_count += 1
                pong_message = message.replace("ping:", "pong:")
                
                try:
                    self.channel.send(pong_message)
                except Exception as e:
                    logger.error(f"Failed to send pong: {e}")
                
                # Only log every 10th ping to reduce overhead
                if self.ping_count % 10 == 0:
                    seq = message.split(":")[1]
                    logger.info(f"Processed {self.ping_count} pings (latest: {seq})")
        
        @self.channel.on("close")
        def on_close():
            logger.info(f"\n✓ Data channel closed")
            logger.info(f"Total pings received: {self.ping_count}")


async def main(remote_host, remote_port):
    """Main function to run receiver"""
    logger.info("="*60)
    logger.info("📡 RECEIVER - WebRTC Latency Test (OPTIMIZED)")
    logger.info("="*60)
    logger.info(f"Connecting to sender at {remote_host}:{remote_port}...\n")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get offer from sender
            logger.info("↓ Fetching offer from sender...")
            async with session.get(f"http://{remote_host}:{remote_port}/offer") as resp:
                if resp.status != 200:
                    logger.error(f"Failed to get offer: HTTP {resp.status}")
                    return
                offer = await resp.json()
            
            logger.info("✓ Offer received")
            
            # Create answer
            logger.info("⚙ Creating answer...")
            rtc = WebRTCReceiver()
            answer = await rtc.create_answer(offer)
            
            # Send answer to sender
            logger.info("↑ Sending answer to sender...")
            async with session.post(f"http://{remote_host}:{remote_port}/answer", 
                                   json=answer) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to send answer: HTTP {resp.status}")
                    return
                await resp.json()
            
            logger.info("✓ Answer sent\n")
            logger.info("="*60)
            logger.info("🎉 WebRTC connection established!")
            logger.info("="*60 + "\n")
            
            # Keep running
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("\n\n👋 Shutting down...")
                await rtc.pc.close()
                
    except aiohttp.ClientConnectorError:
        logger.error(f"\n❌ ERROR: Could not connect to {remote_host}:{remote_port}")
        logger.error("Make sure:")
        logger.error("  1. The sender is running")
        logger.error("  2. The IP address is correct")
        logger.error("  3. Firewall allows the connection")
    except Exception as e:
        logger.error(f"\n❌ ERROR: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="WebRTC Latency Test - Receiver (Optimized)")
    parser.add_argument("--remote-host", required=True,
                       help="IP address of the sender computer")
    parser.add_argument("--remote-port", type=int, default=8080,
                       help="Port of the sender's signaling server (default: 8080)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.remote_host, args.remote_port))
    except KeyboardInterrupt:
        pass