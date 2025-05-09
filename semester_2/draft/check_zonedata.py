import zmq
import json

# ตั้งค่า ZeroMQ
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5557")
socket.setsockopt_string(zmq.SUBSCRIBE, "ZoneDetector")

print("กำลังรอรับข้อมูลจาก Topic ZoneDetector...")

while True:
    # รับข้อความจาก Topic ZoneDetector
    topic = socket.recv_string()
    data_json = socket.recv_string()
    data = json.loads(data_json)

    # แสดงข้อมูล Zone
    print("\nข้อมูล Zone ล่าสุด:")
    for zone in data:
        status = "มีคนอยู่" if zone['occupied'] else "ไม่มีคนอยู่"
        print(f"Zone: {zone['name']}, สถานะ: {status}")