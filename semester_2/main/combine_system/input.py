import cv2
import zmq
import base64
import json
from datetime import datetime
import time

# ตั้งค่า ZeroMQ
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5555")

# สร้าง socket สำหรับส่งค่า FPS
fps_socket = context.socket(zmq.PUB)
fps_socket.bind("tcp://*:5558")

# ฟังก์ชันสำหรับเปิดการเชื่อมต่อกับกล้องหรือไฟล์วีดีโอ
def open_video_source(source):
    if isinstance(source, int) or source.startswith(("http://", "https://", "rtsp://")):
        # ถ้า source เป็นตัวเลข (เว็บแคม) หรือ URL (CCTV)
        cap = cv2.VideoCapture(source)
    else:
        # ถ้า source เป็นไฟล์วีดีโอ
        cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"ไม่สามารถเปิดแหล่งที่มา {source} ได้")
        return None
    return cap

# ฟังก์ชันสำหรับส่งเฟรม
def send_frame(cap, show_video, show_fps):
    ret, frame = cap.read()
    if not ret:
        return False

    # แปลงเฟรมเป็นสตริง base64
    _, buffer = cv2.imencode('.jpg', frame)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')

    # เพิ่ม timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    # สร้างข้อมูลที่จะส่ง (รวม timestamp และเฟรม)
    data = {
        "timestamp": timestamp,
        "frame": jpg_as_text
    }

    # แปลงข้อมูลเป็น JSON
    data_json = json.dumps(data)

    # ส่งข้อมูลผ่าน ZeroMQ พร้อมกับ topic "Sender_frame"
    socket.send_string("Sender_frame", zmq.SNDMORE)
    socket.send_string(data_json)

    # คำนวณ FPS เฉลี่ยใน 1 วินาที
    current_time = time.time()
    if not hasattr(send_frame, 'start_time'):
        send_frame.start_time = current_time
        send_frame.frame_count = 0

    send_frame.frame_count += 1
    elapsed_time = current_time - send_frame.start_time

    if elapsed_time >= 1.0:  # คำนวณ FPS ทุก 1 วินาที
        fps = send_frame.frame_count / elapsed_time
        send_frame.start_time = current_time
        send_frame.frame_count = 0

        # ส่งค่า FPS ไปยัง topic "FPS"
        fps_data = {
            "timestamp": timestamp,
            "fps": fps
        }
        fps_json = json.dumps(fps_data)
        fps_socket.send_string("FPS", zmq.SNDMORE)
        fps_socket.send_string(fps_json)

        # แสดง FPS ใน console
        if show_fps:
            print(f"FPS: {fps:.2f}")

    # แสดงเฟรม (optional)
    if show_video:
        cv2.imshow('Sender', frame)
    return True

# ตัวเลือกสำหรับผู้ใช้
source_type = input("เลือกแหล่งที่มาของวีดีโอ (1 สำหรับกล้อง, 2 สำหรับไฟล์วีดีโอ): ")
if source_type == "1":
    camera_source = input("เลือกแหล่งที่มาของกล้อง (0 สำหรับเว็บแคม, หรือ URL สำหรับ CCTV): ")
    try:
        camera_source = int(camera_source)  # ถ้าเป็นเว็บแคม
    except ValueError:
        pass  # ถ้าเป็น URL CCTV
elif source_type == "2":
    camera_source = input("ใส่พาธไฟล์วีดีโอ (เช่น video.mp4): ")
else:
    print("ตัวเลือกไม่ถูกต้อง")
    exit()

show_video = input("ต้องการแสดงวีดีโอหรือไม่? (y/n): ").lower() == 'y'
show_fps = input("ต้องการแสดง FPS หรือไม่? (y/n): ").lower() == 'y'

# เปิดการเชื่อมต่อกับแหล่งที่มา
cap = open_video_source(camera_source)
if cap is None:
    exit()

# รับค่า FPS ของวิดีโอต้นฉบับ
original_fps = cap.get(cv2.CAP_PROP_FPS)
if original_fps <= 0:
    original_fps = 30  # ใช้ค่า FPS เริ่มต้นหากอ่านค่า FPS ไม่ได้

# คำนวณเวลาหน่วงระหว่างเฟรม (ในหน่วยวินาที)
frame_delay = 1 / original_fps

while True:
    start_time = time.time()  # เก็บเวลาเริ่มต้นของเฟรม

    if not send_frame(cap, show_video, show_fps):
        break

    # หน่วงเวลาเพื่อควบคุมความเร็วของเฟรม
    elapsed_time = time.time() - start_time
    if elapsed_time < frame_delay:
        time.sleep(frame_delay - elapsed_time)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()