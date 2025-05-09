import zmq
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import time
from datetime import datetime
import os
import base64
import cv2
import glob

class EnhancedFeatureVisualizer:
    def __init__(self, max_points=5000):
        self.context = zmq.Context()
        
        # ตั้งค่าการเชื่อมต่อ ZMQ
        self.feature_socket = self.context.socket(zmq.SUB)
        self.feature_socket.connect("tcp://localhost:5559")
        self.feature_socket.setsockopt_string(zmq.SUBSCRIBE, "FeatureData")
        self.feature_socket.setsockopt(zmq.RCVHWM, 100)  # High water mark
        self.feature_socket.setsockopt(zmq.RCVTIMEO, 100)
        
        # ตั้งค่าสำหรับเก็บข้อมูล
        self.max_points = max_points
        self.cog_angles = deque(maxlen=max_points)
        self.movement_rates = deque(maxlen=max_points)
        self.timestamps = deque(maxlen=max_points)
        self.frame_data = deque(maxlen=max_points)  # สำหรับเก็บข้อมูลเฟรม
        
        # ตัวแปรสำหรับแสดงข้อมูลล่าสุด
        self.latest_values = {
            "CoG_Angle": "ไม่มีข้อมูล",
            "Movement_Rate": "ไม่มีข้อมูล",
            "Timestamp": "รอรับข้อมูล..."
        }
        
        # ตั้งค่ากราฟ
        self.fig, (self.ax, self.ax2) = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw={'width_ratios': [3, 1]})
        self.setup_plot()
        
        # ตัวแปรสำหรับการโต้ตอบ
        self.selected_point = None
        self.cid = self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        
        # สำหรับเก็บรูปภาพที่แสดง
        self.current_image = None
        
    def setup_plot(self):
        """เตรียมการตั้งค่าพล็อตเริ่มต้น"""
        # Main scatter plot
        self.ax.clear()
        self.ax.set_title('Feature Space Visualization', fontsize=12)
        self.ax.set_xlabel('CoG Angle [degrees]')
        self.ax.set_ylabel('Movement Rate')
        self.ax.grid(True, linestyle='--', alpha=0.6)
        self.scatter = self.ax.scatter([], [], c=[], cmap='viridis', alpha=0.6, picker=True, pickradius=5)
        
        # Colorbar
        self.colorbar = self.fig.colorbar(self.scatter, ax=self.ax)
        
        # Image display area
        self.ax2.clear()
        self.ax2.set_title('Selected Frame')
        self.ax2.axis('off')
        self.image_display = self.ax2.imshow(np.zeros((100,100,3)), interpolation='nearest')
        
        # Information text
        self.info_text = self.ax.text(0.02, 0.98, 'Waiting for data...', 
                                    transform=self.ax.transAxes, 
                                    verticalalignment='top',
                                    bbox=dict(facecolor='white', alpha=0.8))
        
        plt.tight_layout()
    
    def update_plot(self, frame):
        """อัปเดตพล็อตด้วยข้อมูลใหม่"""
        try:
            # รับข้อมูลหลายๆ เฟรมในแต่ละการอัปเดตเพื่อเพิ่มประสิทธิภาพ
            for _ in range(10):  # รับข้อมูลสูงสุด 10 ครั้งต่อการอัปเดต
                try:
                    topic = self.feature_socket.recv_string()
                    data_json = self.feature_socket.recv_string()
                    feature_data = json.loads(data_json)
                    
                    # บันทึกข้อมูล
                    self.cog_angles.append(feature_data["CoG_Angle"])
                    self.movement_rates.append(feature_data["Movement_Rate"])
                    self.timestamps.append(feature_data["Feature_Timestamp"])
                    
                    # บันทึกข้อมูลเฟรมถ้ามี
                    if "FrameData" in feature_data:
                        self.frame_data.append(feature_data["FrameData"])
                    else:
                        self.frame_data.append(None)
                    
                    # อัปเดตค่าล่าสุด
                    self.latest_values = {
                        "CoG_Angle": feature_data["CoG_Angle"],
                        "Movement_Rate": feature_data["Movement_Rate"],
                        "Timestamp": feature_data["Feature_Timestamp"]
                    }
                    
                except zmq.Again:
                    break  # ไม่มีข้อมูลเพิ่มเติม
        
            if len(self.cog_angles) > 0:
                # สร้างอาร์เรย์สำหรับสีตามเวลา
                colors = np.linspace(0, 1, len(self.cog_angles))
                
                # อัปเดต scatter plot
                self.scatter.set_offsets(np.column_stack([self.cog_angles, self.movement_rates]))
                self.scatter.set_array(colors)
                
                # ตั้งค่าขอบเขตแกน
                self.ax.relim()
                self.ax.autoscale_view()
                
                # อัปเดตข้อมูล
                info_str = f"Total Points: {len(self.cog_angles)}\n"
                info_str += f"Latest:\nTime: {self.timestamps[-1][11:19]}\n"
                info_str += f"CoG Angle: {self.cog_angles[-1]:.2f}°\n"
                info_str += f"Movement Rate: {self.movement_rates[-1]:.4f}"
                self.info_text.set_text(info_str)
                
                # แสดงจุดล่าสุดด้วยเครื่องหมายพิเศษ
                if len(self.cog_angles) > 10:
                    self.ax.plot(self.cog_angles[-1], self.movement_rates[-1], 'ro', markersize=8)
        
        except Exception as e:
            print(f"Error in update: {str(e)}")
        
        return self.scatter,
    
    def on_click(self, event):
        """จัดการเหตุการณ์เมื่อคลิกที่จุดข้อมูล"""
        if event.inaxes != self.ax:
            return
            
        # ค้นหาจุดที่ใกล้ที่สุดกับตำแหน่งที่คลิก
        if len(self.cog_angles) == 0:
            return
            
        # คำนวณระยะทางทั้งหมด
        x_data = np.array(self.cog_angles)
        y_data = np.array(self.movement_rates)
        distances = np.sqrt((x_data - event.xdata)**2 + (y_data - event.ydata)**2)
        idx = np.argmin(distances)
        
        # แสดงข้อมูลจุดที่เลือก
        self.selected_point = idx
        self.show_selected_point()
    
    def show_selected_point(self):
        """แสดงข้อมูลและรูปภาพของจุดที่เลือก"""
        if self.selected_point is None or self.selected_point >= len(self.cog_angles):
            return
            
        # แสดงข้อมูลจุดที่เลือก
        sel_time = self.timestamps[self.selected_point]
        sel_cog = self.cog_angles[self.selected_point]
        sel_mov = self.movement_rates[self.selected_point]
        
        # แปลงรูปแบบ timestamp ให้ตรงกับชื่อไฟล์
        try:
            dt = datetime.strptime(sel_time, "%Y-%m-%d %H:%M:%S.%f")
            file_pattern = f"frame_{dt.strftime('%Y-%m-%d_%H-%M-%S')}*"
            matching_files = glob.glob(os.path.join("captured_frames", file_pattern))
            
            if matching_files:
                # ถ้ามีไฟล์ที่ตรงกับ pattern
                image_path = matching_files[0]
                frame = cv2.imread(image_path)
                if frame is not None:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.image_display.set_data(frame_rgb)
                    self.ax2.set_title(f"Frame at {sel_time[11:19]}")
                    self.ax2.axis('off')
                else:
                    raise ValueError("Could not read image file")
            else:
                raise FileNotFoundError("No matching image found")
                
        except Exception as e:
            print(f"Error loading image: {str(e)}")
            # สร้างภาพว่างเปล่า
            self.ax2.clear()
            self.ax2.set_title(f"Image not found\n{sel_time[11:19]}")
            self.ax2.axis('off')
        
        # ไฮไลต์จุดที่เลือกบนกราฟ
        self.ax.plot(sel_cog, sel_mov, 'yo', markersize=10, markeredgecolor='red')
        
        # อัปเดตข้อความข้อมูล
        current_text = self.info_text.get_text()
        new_text = current_text + f"\n\nSelected Point:\nTime: {sel_time[11:19]}\n"
        new_text += f"CoG: {sel_cog:.2f}°\nMov: {sel_mov:.4f}"
        self.info_text.set_text(new_text)
        
        self.fig.canvas.draw_idle()
    
    def run(self):
        """เรียกใช้การแสดงภาพแบบแอนิเมชัน"""
        print("Starting visualization...")
        print(f"Maximum points to display: {self.max_points}")
        print("Click on any point to view its details and associated frame")
        
        # ใช้ blit=True และ interval สั้นลงเพื่อประสิทธิภาพที่ดีขึ้น
        self.ani = FuncAnimation(
            self.fig, 
            self.update_plot, 
            interval=100,  # อัปเดตทุก 100ms
            blit=True, 
            cache_frame_data=False
        )
        
        plt.show()

if __name__ == "__main__":
    visualizer = EnhancedFeatureVisualizer(max_points=5000)
    visualizer.run()