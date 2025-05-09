import cv2
import zmq
import base64
import json
import numpy as np
import mediapipe as mp
from datetime import datetime

# ตั้งค่า ZeroMQ
context = zmq.Context()
receiver_socket = context.socket(zmq.SUB)
receiver_socket.connect("tcp://localhost:5555")
receiver_socket.setsockopt_string(zmq.SUBSCRIBE, 'Sender_frame')

sender_socket = context.socket(zmq.PUB)
sender_socket.bind("tcp://*:5556")

# ตั้งค่า Mediapipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# ตัวเลือกแสดงวิดีโอ
show_video = input("ต้องการแสดงวิดีโอหรือไม่? (y/n): ").lower() == 'y'

while True:
    # รับเฟรมจาก ZeroMQ
    topic = receiver_socket.recv_string()
    data_json = receiver_socket.recv_string()
    data = json.loads(data_json)

    # แยก timestamp และเฟรม
    image_timestamp = data["timestamp"]
    jpg_as_text = data["frame"]
    
    # แปลงเฟรมจาก base64 กลับเป็นภาพ
    jpg_original = base64.b64decode(jpg_as_text)
    frame = cv2.imdecode(np.frombuffer(jpg_original, dtype=np.uint8), cv2.IMREAD_COLOR)

    # แปลงเฟรมเป็น RGB (Mediapipe ต้องการภาพในรูปแบบ RGB)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # ประมวลผลเฟรมด้วย Mediapipe Pose
    results = pose.process(rgb_frame)

    # วาดโครงกระดูกบนเฟรม (ถ้ามี landmark)
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # ดึงค่าพิกัดของ landmark ทั้ง 33 จุด
        landmarks = results.pose_landmarks.landmark
        height, width, _ = frame.shape

        # สร้าง list เพื่อเก็บค่าพิกัด (x, y)
        pose_data = []
        for landmark in landmarks:
            pose_data.extend([landmark.x, landmark.y])

        # คำนวณความกว้างและความสูงของเฟรม
        max_width = width
        max_height = height

        # เพิ่ม Pose_Timestamp
        pose_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        # สร้างข้อมูลที่จะส่ง
        pose_info = {
            "Image_Timestamp": image_timestamp,
            "Pose_Timestamp": pose_timestamp,
            "MAX_Height": max_height,
            "MAX_Width": max_width,
            "Landmarks": pose_data
        }

        # แปลงข้อมูลเป็น JSON
        pose_info_json = json.dumps(pose_info)

        # ส่งข้อมูลไปยัง topic PoseData
        sender_socket.send_string("PoseData", zmq.SNDMORE)
        sender_socket.send_string(pose_info_json)

    # แสดงเฟรม (ถ้าเลือกแสดงวิดีโอ)
    if show_video:
        cv2.imshow('Pose Detection', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()