import zmq
import json
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from datetime import datetime
import pandas as pd

class FeatureDataMonitor:
    def __init__(self):
        # ตั้งค่า ZeroMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("tcp://localhost:5559")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "FeatureData")
        
        # เก็บข้อมูลสำหรับพล็อตกราฟ
        self.timestamps = []
        self.frame_rates = []
        self.cog_angles = []
        self.movement_rates = []
        
        # สร้างกราฟ
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, 1, figsize=(10, 8))
        plt.subplots_adjust(hspace=0.5)
        
    def update_plot(self, frame):
        try:
            # รับข้อมูลจาก Topic FeatureData
            topic = self.socket.recv_string(flags=zmq.NOBLOCK)
            data_json = self.socket.recv_string(flags=zmq.NOBLOCK)
            data = json.loads(data_json)
            
            # บันทึกข้อมูล
            self.timestamps.append(datetime.strptime(data['Feature_Timestamp'], "%Y-%m-%d %H:%M:%S.%f"))
            self.frame_rates.append(data['Frame_Rate'])
            self.cog_angles.append(data['CoG_Angle'])
            self.movement_rates.append(data['Movement_Rate'])
            
            # จำกัดจำนวนข้อมูลที่แสดง (500 ค่าล่าสุด)
            max_points = 500
            if len(self.timestamps) > max_points:
                self.timestamps = self.timestamps[-max_points:]
                self.frame_rates = self.frame_rates[-max_points:]
                self.cog_angles = self.cog_angles[-max_points:]
                self.movement_rates = self.movement_rates[-max_points:]
            
            # ล้างและอัปเดตกราฟ Frame Rate
            self.ax1.clear()
            self.ax1.plot(self.timestamps, self.frame_rates, 'b-')
            self.ax1.set_title('Frame Rate Over Time')
            self.ax1.set_ylabel('FPS')
            self.ax1.grid(True)
            
            # ล้างและอัปเดตกราฟ CoG Angle
            self.ax2.clear()
            self.ax2.plot(self.timestamps, self.cog_angles, 'r-')
            self.ax2.set_title('Center of Gravity Angle Over Time')
            self.ax2.set_ylabel('Angle (degrees)')
            self.ax2.grid(True)
            
            # ล้างและอัปเดตกราฟ Movement Rate
            self.ax3.clear()
            self.ax3.plot(self.timestamps, self.movement_rates, 'g-')
            self.ax3.set_title('Movement Rate Over Time')
            self.ax3.set_ylabel('Movement Rate')
            self.ax3.set_xlabel('Timestamp')
            self.ax3.grid(True)
            
            # แสดงข้อมูลล่าสุดใน Console
            print(f"\n[{self.timestamps[-1].strftime('%H:%M:%S.%f')[:-3]}] "
                  f"Frame Rate: {self.frame_rates[-1]:.2f} fps | "
                  f"CoG Angle: {self.cog_angles[-1]:.2f}° | "
                  f"Movement Rate: {self.movement_rates[-1]:.4f}")
            
        except zmq.Again:
            pass  # ไม่มีข้อมูลใหม่
        except Exception as e:
            print(f"Error updating plot: {e}")

    def start_monitoring(self):
        print("เริ่มการตรวจสอบข้อมูลจาก Topic FeatureData...")
        print("กด Ctrl+C เพื่อหยุดการทำงาน\n")
        
        # สร้าง animation สำหรับอัปเดตกราฟทุก 100 มิลลิวินาที
        self.ani = FuncAnimation(self.fig, self.update_plot, interval=100)
        plt.show()

if __name__ == "__main__":
    monitor = FeatureDataMonitor()
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\nปิดโปรแกรมตรวจสอบข้อมูล...")
        
        # บันทึกข้อมูลลงไฟล์ CSV ก่อนปิดโปรแกรม
        if monitor.timestamps:
            df = pd.DataFrame({
                'Timestamp': [ts.strftime('%Y-%m-%d %H:%M:%S.%f') for ts in monitor.timestamps],
                'Frame_Rate': monitor.frame_rates,
                'CoG_Angle': monitor.cog_angles,
                'Movement_Rate': monitor.movement_rates
            })
            filename = f"feature_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            print(f"บันทึกข้อมูลลงไฟล์ {filename} เรียบร้อย")