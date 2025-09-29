# receiver_udp_discover.py
import socket
import struct
import cv2
import numpy as np
import time
import threading

STREAM_PORT = 5005       # where the stream packets arrive
BEACON_PORT = 5006       # where we send discovery heartbeats (sender listens)
BEACON_INTERVAL = 1.0    # seconds: how often receiver advertises itself
PACKET_TIMEOUT = 2.0     # seconds to wait before discarding incomplete frames

# storage for incoming fragmented frames
frames = {}  # frame_id -> { 'parts': dict(part_idx->bytes), 'total': int, 'first_ts': float }

def try_assemble(frame_id):
    info = frames.get(frame_id)
    if not info:
        return None
    if len(info['parts']) != info['total']:
        return None
    parts = [info['parts'][i] for i in range(info['total'])]
    data = b"".join(parts)
    jpg = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(jpg, cv2.IMREAD_COLOR)
    del frames[frame_id]
    return img

def stream_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", STREAM_PORT))
    sock.settimeout(1.0)
    print(f"[stream] Listening on UDP {STREAM_PORT}")
    try:
        while True:
            try:
                packet, addr = sock.recvfrom(65536)
            except socket.timeout:
                # drop stale frames
                now = time.time()
                stale = [fid for fid, v in frames.items() if now - v['first_ts'] > PACKET_TIMEOUT]
                for fid in stale:
                    del frames[fid]
                continue

            if len(packet) < 8:
                continue
            header = packet[:8]
            frame_id, total_parts, part_idx = struct.unpack("!IHH", header)
            payload = packet[8:]

            if frame_id not in frames:
                frames[frame_id] = {'parts': {}, 'total': total_parts, 'first_ts': time.time()}
            frames[frame_id]['parts'][part_idx] = payload

            img = try_assemble(frame_id)
            if img is not None:
                cv2.imshow("Receiver", img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        cv2.destroyAllWindows()

def beacon_sender():
    # Send a small "HERE" UDP beacon on BEACON_PORT to any listener
    # We send from an ephemeral socket to broadcast address so sender can detect us.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # beacon payload: simple text with stream port
    payload = f"RECEIVER:{STREAM_PORT}".encode("utf-8")
    while True:
        try:
            # broadcast to local network (255.255.255.255)
            s.sendto(payload, ("255.255.255.255", BEACON_PORT))
        except Exception as e:
            # ignore send errors (some networks block broadcast)
            pass
        time.sleep(BEACON_INTERVAL)

if __name__ == "__main__":
    # run both threads: beacon + stream listener
    t1 = threading.Thread(target=beacon_sender, daemon=True)
    t1.start()
    stream_listener()
