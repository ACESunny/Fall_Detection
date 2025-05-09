import zmq
import cv2
import numpy as np
import time
from datetime import datetime
import os
import json
import base64

def setup_output_folder():
    # สร้างโฟลเดอร์สำหรับเก็บภาพถ้าไม่มีอยู่
    if not os.path.exists('captured_frames'):
        os.makedirs('captured_frames')

def receive_and_save_frames():
    # เตรียม ZMQ context และ socket
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://localhost:5555")  # เปลี่ยนเป็น IP และ port ที่เหมาะสม
    socket.setsockopt_string(zmq.SUBSCRIBE, 'Sender_frame')  # สับスクライบเฉพาะ topic 'Sender_frame'
    
    setup_output_folder()
    
    print("เริ่มรับภาพจาก Topic Sender_frame...")
    
    try:
        while True:
            # รับ topic (ส่วนแรกของ multipart message)
            topic = socket.recv_string()
            
            # รับข้อมูล JSON (ส่วนที่สองของ multipart message)
            data_json = socket.recv_string()
            
            # แปลง JSON เป็น dictionary
            data = json.loads(data_json)
            
            # ดึง timestamp และ frame จากข้อมูล
            timestamp = data["timestamp"]
            frame_base64 = data["frame"]
            
            # แปลง base64 กลับเป็น bytes
            frame_bytes = base64.b64decode(frame_base64.encode('utf-8'))
            
            # แปลง bytes เป็น numpy array
            img_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            
            # ถอดรหัสภาพ
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # สร้างชื่อไฟล์จาก timestamp (แทนที่อักขระที่ไม่เหมาะสม)
                safe_timestamp = timestamp.replace(' ', '_').replace(':', '-').replace('.', '-')
                filename = f"captured_frames/frame_{safe_timestamp}.jpg"
                
                # บันทึกภาพ
                cv2.imwrite(filename, frame)
                print(f"บันทึกภาพแล้ว: {filename} (เวลาจริง: {timestamp})")
            else:
                print("ไม่สามารถถอดรหัสภาพได้")
                
    except KeyboardInterrupt:
        print("หยุดการรับภาพโดยผู้ใช้")
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {str(e)}")
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    receive_and_save_frames()