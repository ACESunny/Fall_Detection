import zmq
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import time

class FeatureSpaceVisualizer:
    def __init__(self, max_points=200):
        self.context = zmq.Context()
        
        # ตั้งค่าการเชื่อมรับข้อมูล
        self.feature_socket = self.context.socket(zmq.SUB)
        self.feature_socket.connect("tcp://localhost:5559")
        self.feature_socket.setsockopt_string(zmq.SUBSCRIBE, "FeatureData")
        self.feature_socket.setsockopt(zmq.RCVTIMEO, 1000)  # ตั้งค่าเวลา timeout 1 วินาที
        
        # ที่เก็บข้อมูล
        self.max_points = max_points
        self.cog_angles = deque(maxlen=max_points)
        self.movement_rates = deque(maxlen=max_points)
        self.timestamps = deque(maxlen=max_points)
        
        # ตั้งค่ากราฟ
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.setup_plot()
        
        # ตัวแปรสำหรับแสดงข้อมูลล่าสุด
        self.latest_values = {
            "CoG_Angle": "ไม่มีข้อมูล",
            "Movement_Rate": "ไม่มีข้อมูล",
            "Timestamp": "รอรับข้อมูล..."
        }
    
    def setup_plot(self):
        self.ax.clear()
        self.ax.set_title('ความสัมพันธ์ระหว่าง Movement Rate กับ CoG Angle\n(กำลังรอรับข้อมูล...)', 
                         fontname='Tahoma', fontsize=12)
        self.ax.set_xlabel('มุมจุดศูนย์ถ่วง (CoG Angle) [องศา]', fontname='Tahoma')
        self.ax.set_ylabel('อัตราการเคลื่อนไหว (Movement Rate)', fontname='Tahoma')
        
        # ตั้งค่ากราฟพื้นฐาน
        self.ax.grid(True, linestyle='--', alpha=0.6)
        self.ax.set_facecolor('#f5f5f5')
        
        # สร้าง scatter plot ว่างๆ
        self.scatter = self.ax.scatter([], [], color='blue', alpha=0.6, label='ข้อมูลล่าสุด')
        
        # เพิ่ม annotation สำหรับแสดงค่าล่าสุด
        self.text_annotation = self.ax.annotate(
            'กำลังรอรับข้อมูล...',
            xy=(0.5, 0.9),
            xycoords='axes fraction',
            ha='center',
            fontname='Tahoma',
            color='red'
        )
        
        plt.tight_layout()
    
    def update_plot(self, frame):
        try:
            # รับข้อมูลใหม่
            topic = self.feature_socket.recv_string()
            data_json = self.feature_socket.recv_string()
            feature_data = json.loads(data_json)
            
            # บันทึกข้อมูล
            self.cog_angles.append(feature_data["CoG_Angle"])
            self.movement_rates.append(feature_data["Movement_Rate"])
            self.timestamps.append(feature_data["Feature_Timestamp"])
            
            # อัปเดตค่าล่าสุด
            self.latest_values = {
                "CoG_Angle": f"{feature_data['CoG_Angle']:.2f} องศา",
                "Movement_Rate": f"{feature_data['Movement_Rate']:.4f}",
                "Timestamp": feature_data["Feature_Timestamp"]
            }
            
            # อัปเดตกราฟ
            self.ax.clear()
            
            # วาดกราฟใหม่
            self.scatter = self.ax.scatter(
                self.cog_angles, 
                self.movement_rates, 
                color='blue', 
                alpha=0.6,
                label=f'ข้อมูล ({len(self.cog_angles)} จุด)'
            )
            
            # วาดจุดล่าสุดด้วยสีแดง
            if len(self.cog_angles) > 0:
                self.ax.scatter(
                    self.cog_angles[-1], 
                    self.movement_rates[-1], 
                    color='red', 
                    s=100,
                    label='ค่าล่าสุด'
                )
            
            # ตั้งค่ากราฟ
            self.ax.set_title(
                f'ความสัมพันธ์ระหว่าง Movement Rate กับ CoG Angle\n(ข้อมูลล่าสุด: {self.timestamps[-1][11:19]})',
                fontname='Tahoma',
                fontsize=12
            )
            self.ax.set_xlabel('มุมจุดศูนย์ถ่วง (CoG Angle) [องศา]', fontname='Tahoma')
            self.ax.set_ylabel('อัตราการเคลื่อนไหว (Movement Rate)', fontname='Tahoma')
            self.ax.grid(True, linestyle='--', alpha=0.6)
            self.ax.legend(loc='upper right', prop={'family': 'Tahoma'})
            
            # แสดงค่าล่าสุด
            info_text = (
                f"ค่าล่าสุด:\n"
                f"เวลา: {self.timestamps[-1][11:19]}\n"
                f"CoG Angle: {self.cog_angles[-1]:.2f} องศา\n"
                f"Movement Rate: {self.movement_rates[-1]:.4f}"
            )
            self.ax.annotate(
                info_text,
                xy=(0.02, 0.95),
                xycoords='axes fraction',
                ha='left',
                va='top',
                fontname='Tahoma',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
            )
            
        except zmq.Again:
            # ถ้าไม่มีข้อมูลใหม่
            if len(self.cog_angles) > 0:
                # แสดงข้อมูลเดิมถ้ามี
                self.ax.set_title(
                    f'ความสัมพันธ์ระหว่าง Movement Rate กับ CoG Angle\n(ข้อมูลล่าสุด: {self.timestamps[-1][11:19]})',
                    fontname='Tahoma',
                    fontsize=12
                )
            else:
                # ถ้ายังไม่มีข้อมูลเลย
                self.ax.set_title(
                    'ความสัมพันธ์ระหว่าง Movement Rate กับ CoG Angle\n(กำลังรอรับข้อมูล...)',
                    fontname='Tahoma',
                    fontsize=12
                )
                self.text_annotation.set_text('กำลังรอรับข้อมูล...\n(ตรวจสอบการเชื่อมต่อ)')
            
        except Exception as e:
            print(f"เกิดข้อผิดพลาด: {str(e)}")
        
        return self.scatter,
    
    def run(self):
        print("กำลังเริ่มต้นการแสดงผลกราฟ...")
        print("กำลังรอรับข้อมูลจากพอร์ต 5559...")
        ani = FuncAnimation(self.fig, self.update_plot, interval=500, blit=False)
        plt.show()

if __name__ == "__main__":
    visualizer = FeatureSpaceVisualizer(max_points=200)
    visualizer.run()