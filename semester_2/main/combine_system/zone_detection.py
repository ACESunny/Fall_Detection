import cv2
import zmq
import base64
import json
import numpy as np
from datetime import datetime

# ตั้งค่า ZeroMQ
context = zmq.Context()

# Socket สำหรับรับเฟรมจาก Sender_frame
frame_socket = context.socket(zmq.SUB)
frame_socket.connect("tcp://localhost:5555")
frame_socket.setsockopt_string(zmq.SUBSCRIBE, "Sender_frame")

# Socket สำหรับรับข้อมูล Pose จาก PoseData
pose_socket = context.socket(zmq.SUB)
pose_socket.connect("tcp://localhost:5556")
pose_socket.setsockopt_string(zmq.SUBSCRIBE, "PoseData")

# Socket สำหรับส่งข้อมูล Zone ไปยัง ZoneDetector
zone_socket = context.socket(zmq.PUB)
zone_socket.bind("tcp://*:5557")

# โหลดข้อมูล Zone จากไฟล์ JSON
with open('zones.json', 'r') as f:
    zones_data = json.load(f)

# ตัวเลือกแสดงวิดีโอ
show_video = input("ต้องการแสดงวิดีโอหรือไม่? (y/n): ").lower() == 'y'

def draw_zones(frame, zones):
    for zone in zones:
        points = np.array([[point['x'], point['y']] for point in zone['points']], np.int32)
        points = points.reshape((-1, 1, 2))
        cv2.polylines(frame, [points], isClosed=True, color=(0, 255, 0), thickness=2)
        cv2.putText(frame, zone['name'], (points[0][0][0], points[0][0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

def is_point_in_zone(x, y, zone):
    points = np.array([[point['x'], point['y']] for point in zone['points']])
    return cv2.pointPolygonTest(points, (x, y), False) >= 0

def calculate_center(landmarks, width, height):
    """
    คำนวณจุดกึ่งกลางของ Pose จาก landmarks ที่ได้รับ
    landmarks: list ของค่าพิกัด [x0, y0, x1, y1, ..., x32, y32]
    width: ความกว้างของเฟรม
    height: ความสูงของเฟรม
    """
    # แปลง landmarks เป็น list ของ (x, y)
    x_coords = landmarks[::2]  # ค่า x อยู่ที่ index 0, 2, 4, ...
    y_coords = landmarks[1::2]  # ค่า y อยู่ที่ index 1, 3, 5, ...

    # คำนวณค่าเฉลี่ยของ x และ y
    center_x = int(np.mean(x_coords) * width)
    center_y = int(np.mean(y_coords) * height)

    return center_x, center_y

while True:
    # รับเฟรมจาก Sender_frame
    try:
        frame_topic = frame_socket.recv_string(flags=zmq.NOBLOCK)
        frame_data_json = frame_socket.recv_string(flags=zmq.NOBLOCK)
        frame_data = json.loads(frame_data_json)
        jpg_as_text = frame_data["frame"]
        jpg_original = base64.b64decode(jpg_as_text)
        frame = cv2.imdecode(np.frombuffer(jpg_original, dtype=np.uint8), cv2.IMREAD_COLOR)
    except zmq.Again:
        frame = None

    # รับข้อมูล Pose จาก PoseData
    try:
        pose_topic = pose_socket.recv_string(flags=zmq.NOBLOCK)
        pose_data_json = pose_socket.recv_string(flags=zmq.NOBLOCK)
        pose_data = json.loads(pose_data_json)
        landmarks = pose_data["Landmarks"]
        height, width = pose_data["MAX_Height"], pose_data["MAX_Width"]
    except zmq.Again:
        landmarks = None

    if frame is not None and landmarks is not None:
        # หาจุดกึ่งกลางของ Pose
        center_x, center_y = calculate_center(landmarks, width, height)

        # ตรวจสอบว่าจุดกึ่งกลางอยู่ใน Zone ใด
        zone_status = []
        for zone in zones_data['zones']:
            if is_point_in_zone(center_x, center_y, zone):
                zone_status.append({"name": zone['name'], "occupied": True})
                if show_video:
                    cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                    cv2.putText(frame, "Person in " + zone['name'], (center_x, center_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            else:
                zone_status.append({"name": zone['name'], "occupied": False})

        # ส่งข้อมูล Zone ไปยัง ZoneDetector
        zone_socket.send_string("ZoneDetector", zmq.SNDMORE)
        zone_socket.send_string(json.dumps(zone_status))

        # วาด Zone บนเฟรม (ถ้าเลือกแสดงวิดีโอ)
        if show_video:
            draw_zones(frame, zones_data['zones'])

        # แสดงเฟรม (ถ้าเลือกแสดงวิดีโอ)
        if show_video:
            cv2.imshow('Frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

cv2.destroyAllWindows()