import zmq
import json
import pandas as pd
from datetime import datetime

# ตั้งค่า ZeroMQ
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5556")
socket.setsockopt_string(zmq.SUBSCRIBE, "PoseData")

# สร้าง DataFrame เพื่อเก็บข้อมูล
columns = ['Image_Timestamp', 'Pose_Timestamp', 'Time_Difference']
df = pd.DataFrame(columns=columns)

# ฟังก์ชันสำหรับแปลง timestamp เป็นวินาที
def parse_timestamp(timestamp):
    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f").timestamp()

def main():
    global df  # ประกาศว่า df เป็นตัวแปร global

    print("กำลังรอรับข้อมูลจาก Topic PoseData...")

    while True:
        # รับข้อความจาก Topic PoseData
        topic = socket.recv_string()
        data_json = socket.recv_string()
        data = json.loads(data_json)

        # แยก timestamp
        image_timestamp = data["Image_Timestamp"]
        pose_timestamp = data["Pose_Timestamp"]

        # คำนวณผลต่างเวลา
        image_time = parse_timestamp(image_timestamp)
        pose_time = parse_timestamp(pose_timestamp)
        time_difference = pose_time - image_time

        # เพิ่มข้อมูลลงใน DataFrame
        new_row = pd.DataFrame([{
            'Image_Timestamp': image_timestamp,
            'Pose_Timestamp': pose_timestamp,
            'Time_Difference': time_difference
        }])
        df = pd.concat([df, new_row], ignore_index=True)

        # แสดงข้อมูลล่าสุด
        print(f"Image Timestamp: {image_timestamp}")
        print(f"Pose Timestamp: {pose_timestamp}")
        print(f"Time Difference: {time_difference:.6f} seconds")
        print("-" * 50)

if __name__ == '__main__':
    main()