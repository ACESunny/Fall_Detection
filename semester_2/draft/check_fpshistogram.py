import zmq
import json
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time

# ตั้งค่า ZeroMQ
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5558")
socket.setsockopt_string(zmq.SUBSCRIBE, "FPS")

# สร้าง list เพื่อเก็บค่า FPS
fps_data = []

# ฟังก์ชันสำหรับอัปเดตกราฟ
def update_graph(frame):
    try:
        # รับข้อความจาก Topic FPS
        topic = socket.recv_string(flags=zmq.NOBLOCK)
        data_json = socket.recv_string(flags=zmq.NOBLOCK)
        data = json.loads(data_json)

        # แยกค่า FPS
        fps = data["fps"]
        fps_data.append(fps)

        # แสดงค่า FPS ล่าสุด
        print(f"FPS: {fps:.2f}")

        # ล้างกราฟเดิม
        ax.clear()

        # สร้างกราฟ Histogram
        ax.hist(fps_data, bins=20, color='blue', edgecolor='black')
        
        ax.set_title('Real-Time FPS Histogram')
        ax.set_xlabel('FPS')
        ax.set_ylabel('Frequency')
        ax.grid(True)

    except zmq.Again:
        pass  # ไม่มีข้อมูลใหม่

# สร้างกราฟ
fig, ax = plt.subplots()

# ใช้ FuncAnimation เพื่ออัปเดตกราฟทุก 1 วินาที
ani = FuncAnimation(fig, update_graph, interval=1000)

# แสดงกราฟ
plt.show()