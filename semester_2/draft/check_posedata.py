import zmq
import json
import time

# ตั้งค่า ZeroMQ
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5556")
socket.setsockopt_string(zmq.SUBSCRIBE, "PoseData")

while True:
    # รับข้อความจาก topic PoseData
    topic = socket.recv_string()
    data_json = socket.recv_string()
    data = json.loads(data_json)

    # หน่วงเวลา 1 วินาที
    time.sleep(1)

    # แสดงข้อความที่ได้รับ
    print("=" * 50)
    print(f"Image Timestamp: {data['Image_Timestamp']}")
    print(f"Pose Timestamp: {data['Pose_Timestamp']}")
    print(f"MAX Height: {data['MAX_Height']}")
    print(f"MAX Width: {data['MAX_Width']}")
    print("Landmarks (x, y):")
    for i in range(0, len(data['Landmarks']), 2):
        print(f"  Point {i//2}: ({data['Landmarks'][i]}, {data['Landmarks'][i+1]})")