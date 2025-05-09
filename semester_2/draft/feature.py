import zmq
import json
import numpy as np
from datetime import datetime
import time
import csv
import os

# ตั้งค่า ZeroMQ
context = zmq.Context()

# Socket สำหรับรับข้อมูล Pose
pose_socket = context.socket(zmq.SUB)
pose_socket.connect("tcp://localhost:5556")
pose_socket.setsockopt_string(zmq.SUBSCRIBE, "PoseData")

# Socket สำหรับส่งข้อมูล Feature
feature_socket = context.socket(zmq.PUB)
feature_socket.bind("tcp://*:5559")

# กำหนดจุดเชื่อมต่อสำหรับคำนวณ Movement Rate
CONNECTIONS = [(0, 11), (11, 12), (12, 24), (24, 23), (23, 11),
               (15, 13), (13, 11), (12, 14), (14, 16),
               (23, 25), (25, 27), (24, 26), (26, 28)]

class FeatureCalculator:
    def __init__(self, use_real_scale=False):
        self.prev_frame = None
        self.prev_timestamp = None
        self.use_real_scale = use_real_scale

    def denormalize(self, x, y, max_width, max_height):
        """แปลงค่าจาก normalized เป็นขนาดจริง"""
        real_x = x * max_width
        real_y = y * max_height
        return real_x, real_y

    def calculate_features(self, current_data):
        if self.prev_frame is None:
            self.prev_frame = current_data
            self.prev_timestamp = current_data["Image_Timestamp"]
            return None
        
        try:
            max_width = current_data["MAX_Width"]
            max_height = current_data["MAX_Height"]
            
            # คำนวณ Frame Rate
            current_time = datetime.strptime(current_data["Image_Timestamp"], "%Y-%m-%d %H:%M:%S.%f")
            prev_time = datetime.strptime(self.prev_timestamp, "%Y-%m-%d %H:%M:%S.%f")
            time_diff = (current_time - prev_time).total_seconds()
            frame_rate = 1 / time_diff if time_diff > 0 else 0
            
            # ดึงค่าจาก Landmarks
            landmarks = current_data["Landmarks"]
            prev_landmarks = self.prev_frame["Landmarks"]
            
            # Center of Gravity Angle
            left_x, left_y = landmarks[23*2], landmarks[23*2+1]
            right_x, right_y = landmarks[24*2], landmarks[24*2+1]
            nose_x, nose_y = landmarks[0], landmarks[1]
            
            if self.use_real_scale:
                left_x, left_y = self.denormalize(left_x, left_y, max_width, max_height)
                right_x, right_y = self.denormalize(right_x, right_y, max_width, max_height)
                nose_x, nose_y = self.denormalize(nose_x, nose_y, max_width, max_height)
            
            cog_x = (right_x + left_x) / 2
            cog_y = (right_y + left_y) / 2
            dx = cog_x - nose_x
            dy = cog_y - nose_y
            cog_angle = np.arctan2(abs(dy), abs(dx)) * (180 / np.pi)
            
            # คำนวณ Movement Rate
            total_distance = 0.0
            num_connections = len(CONNECTIONS)
            
            for conn in CONNECTIONS:
                x1, y1 = landmarks[conn[0]*2], landmarks[conn[0]*2+1]
                x2, y2 = landmarks[conn[1]*2], landmarks[conn[1]*2+1]
                x1_prev, y1_prev = prev_landmarks[conn[0]*2], prev_landmarks[conn[0]*2+1]
                x2_prev, y2_prev = prev_landmarks[conn[1]*2], prev_landmarks[conn[1]*2+1]
                
                if self.use_real_scale:
                    x1, y1 = self.denormalize(x1, y1, max_width, max_height)
                    x2, y2 = self.denormalize(x2, y2, max_width, max_height)
                    x1_prev, y1_prev = self.denormalize(x1_prev, y1_prev, max_width, max_height)
                    x2_prev, y2_prev = self.denormalize(x2_prev, y2_prev, max_width, max_height)
                
                start_point_diff = np.sqrt((x1 - x1_prev)**2 + (y1 - y1_prev)**2)
                end_point_diff = np.sqrt((x2 - x2_prev)**2 + (y2 - y2_prev)**2)
                total_distance += (start_point_diff + end_point_diff) / 2
            
            avg_distance = total_distance / num_connections
            movement_rate = avg_distance / time_diff if time_diff > 0 else 0.0
            
            # อัปเดตเฟรมก่อนหน้า
            self.prev_frame = current_data
            self.prev_timestamp = current_data["Image_Timestamp"]
            
            return {
                "Feature_Timestamp": current_data["Image_Timestamp"],
                "Frame_Rate": frame_rate,
                "CoG_Angle": cog_angle,
                "Movement_Rate": movement_rate
            }
            
        except Exception as e:
            print(f"Error calculating features: {e}")
            return None

class CSVWriter:
    def __init__(self, filename="feature_data.csv"):
        self.filename = filename
        self.file = None
        self.writer = None
        self.is_first_write = True
        
    def open(self):
        # ตรวจสอบว่าไฟล์มีอยู่แล้วหรือไม่
        file_exists = os.path.isfile(self.filename)
        
        # เปิดไฟล์ในโหมด append
        self.file = open(self.filename, mode='a', newline='')
        self.writer = csv.writer(self.file)
        
        # ถ้าไฟล์ยังไม่มีอยู่หรือว่างเปล่า ให้เขียน header
        if not file_exists or os.stat(self.filename).st_size == 0:
            self.writer.writerow(["Timestamp", "Frame_Rate", "CoG_Angle", "Movement_Rate"])
            self.is_first_write = False
    
    def write(self, feature_data):
        if self.writer is None:
            self.open()
        
        try:
            self.writer.writerow([
                feature_data["Feature_Timestamp"],
                feature_data["Frame_Rate"],
                feature_data["CoG_Angle"],
                feature_data["Movement_Rate"]
            ])
            self.file.flush()  # บังคับเขียนข้อมูลลงไฟล์ทันที
        except Exception as e:
            print(f"Error writing to CSV: {e}")
    
    def close(self):
        if self.file is not None:
            self.file.close()

def main():
    user_input = input("use_real_scale? (Y/N): ")
    use_real_scale = True if user_input.upper() == 'Y' else False
    
    save_csv = input("Save to CSV file? (Y/N): ").upper() == 'Y'
    csv_writer = None
    
    if save_csv:
        csv_filename = input("Enter CSV filename (default: feature_data.csv): ") or "feature_data.csv"
        csv_writer = CSVWriter(csv_filename)
        print(f"Feature data will be saved to {csv_filename}")
    
    calculator = FeatureCalculator(use_real_scale=use_real_scale)
    print("กำลังรอรับข้อมูลจาก Topic PoseData...")
    
    try:
        while True:
            try:
                topic = pose_socket.recv_string()
                data_json = pose_socket.recv_string()
                pose_data = json.loads(data_json)
                
                features = calculator.calculate_features(pose_data)
                
                if features:
                    feature_socket.send_string("FeatureData", zmq.SNDMORE)
                    feature_socket.send_string(json.dumps(features))
                    
                    print(f"\n⏱️ Timestamp: {features['Feature_Timestamp']}")
                    print(f"📊 Frame Rate: {features['Frame_Rate']:.2f} fps")
                    print(f"📐 CoG Angle: {features['CoG_Angle']:.2f} degrees")
                    print(f"🏃 Movement Rate: {features['Movement_Rate']:.4f}")
                    
                    if save_csv and csv_writer:
                        csv_writer.write(features)
                        
            except zmq.Again:
                time.sleep(0.01)
            except Exception as e:
                print(f"เกิดข้อผิดพลาด: {e}")
                time.sleep(1)
    finally:
        if csv_writer:
            csv_writer.close()

if __name__ == "__main__":
    main()