# sender_udp_discover.py
import cv2
import socket
import struct
import time
import threading
import numpy as np

BEACON_PORT = 5006       # where receiver broadcasts its presence
STREAM_PORT = 5005       # port to send fragmented frames to (same as receiver STREAM_PORT)
CAMERA_INDEX = 1
JPEG_QUALITY = 80
CHUNK_SIZE = 60000
FPS = 15
BEACON_TIMEOUT = 5.0     # seconds to wait for beacon before complaining

# simple detection (replaceable)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
def detect(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    for (x,y,w,h) in faces:
        cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)
    return frame

# Shared discovered receiver info
discovered = {"ip": None, "port": None, "ts": 0.0}
lock = threading.Lock()

def beacon_listener():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", BEACON_PORT))
    except Exception as e:
        print(f"[beacon] bind failed: {e}")
        return
    s.settimeout(1.0)
    print(f"[beacon] Listening for receiver beacons on UDP {BEACON_PORT}...")
    while True:
        try:
            data, addr = s.recvfrom(1024)
        except socket.timeout:
            continue
        try:
            txt = data.decode("utf-8")
            # expect "RECEIVER:<stream_port>"
            if txt.startswith("RECEIVER:"):
                port = int(txt.split(":",1)[1])
                with lock:
                    discovered["ip"] = addr[0]
                    discovered["port"] = port
                    discovered["ts"] = time.time()
                    print(f"[beacon] discovered receiver at {addr[0]}:{port}")
        except Exception:
            continue

def wait_for_receiver(timeout=BEACON_TIMEOUT):
    start = time.time()
    while time.time() - start < timeout:
        with lock:
            if discovered["ip"] and (time.time() - discovered["ts"] < 10.0):
                return discovered["ip"], discovered["port"]
        time.sleep(0.1)
    return None, None

def stream_sender():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cap = cv2.VideoCapture(CAMERA_INDEX)
    frame_id = 0
    interval = 1.0 / FPS

    try:
        while True:
            # ensure we have a receiver
            dest_ip, dest_port = None, None
            with lock:
                if discovered["ip"] and (time.time() - discovered["ts"] < 10.0):
                    dest_ip = discovered["ip"]; dest_port = discovered["port"]

            if not dest_ip:
                # show waiting notice on preview until receiver found
                # try small wait and continue
                cv2.putText(np.zeros((200,400,3), np.uint8), "Waiting for receiver...", (10,100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                # poll again
                time.sleep(0.2)
                continue

            t0 = time.time()
            ret, frame = cap.read()
            if not ret:
                print("camera read failed")
                break
            frame = detect(frame)

            result, encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if not result:
                continue
            data = encoded.tobytes()
            data_len = len(data)
            total_parts = (data_len + CHUNK_SIZE - 1) // CHUNK_SIZE

            for part_idx in range(total_parts):
                start = part_idx * CHUNK_SIZE
                end = start + CHUNK_SIZE
                chunk = data[start:end]
                header = struct.pack("!IHH", frame_id, total_parts, part_idx)
                try:
                    sock.sendto(header + chunk, (dest_ip, dest_port))
                except Exception as e:
                    print(f"[stream] send error: {e}")
                    break

            # local preview
            cv2.imshow("Sender Preview", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            frame_id = (frame_id + 1) & 0xFFFFFFFF
            dt = time.time() - t0
            if dt < interval:
                time.sleep(interval - dt)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        sock.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    t = threading.Thread(target=beacon_listener, daemon=True)
    t.start()
    # optionally block until discovery (or just start streaming and wait)
    ip, port = wait_for_receiver(timeout=10.0)
    if ip:
        print(f"Found receiver at {ip}:{port}, starting stream.")
    else:
        print("No receiver discovered within timeout; continuing to listen and will start when found.")
    stream_sender()
