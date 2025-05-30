import cv2
import zmq
import base64
import json
import numpy as np
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from typing import List, Dict, Any  # เพิ่ม type hints

class ZoneDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Zone Detector")
        self.root.geometry("1200x800")
        
        # กำหนดค่าเริ่มต้น
        self.current_frame = None
        self.after_id = None
        self.zones_data = self.load_zones_data()
        self.show_video = tk.BooleanVar(value=True)
        
        # เริ่มต้น ZMQ
        self.init_zmq()
        
        # สร้าง UI
        self.init_ui()
        
        # เริ่มการประมวลผล
        self.process_frames()
    
    def load_zones_data(self) -> Dict[str, Any]:
        """โหลดข้อมูลโซนจากไฟล์"""
        try:
            with open('zones.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load zones.json: {str(e)}")
            self.root.destroy()
            raise
    
    def init_zmq(self):
        """ตั้งค่า ZMQ Sockets"""
        self.context = zmq.Context()
        
        # Socket สำหรับรับภาพ
        self.frame_socket = self.context.socket(zmq.SUB)
        self.frame_socket.connect("tcp://localhost:5555")
        self.frame_socket.setsockopt_string(zmq.SUBSCRIBE, "Sender_frame")
        
        # Socket สำหรับรับข้อมูลท่าทาง
        self.pose_socket = self.context.socket(zmq.SUB)
        self.pose_socket.connect("tcp://localhost:5556")
        self.pose_socket.setsockopt_string(zmq.SUBSCRIBE, "PoseData")
        
        # Socket สำหรับส่งข้อมูลโซน
        self.zone_socket = self.context.socket(zmq.PUB)
        self.zone_socket.bind("tcp://*:5557")
        
        # Socket สำหรับส่งภาพที่มีการวาดโซน
        self.annotated_img_socket = self.context.socket(zmq.PUB)
        self.annotated_img_socket.bind("tcp://*:5561")  # เปลี่ยนพอร์ตเป็น 5561
    
    def init_ui(self):
        """สร้างส่วนติดต่อผู้ใช้"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ส่วนแสดงผลวิดีโอ
        self.video_frame = ttk.LabelFrame(main_frame, text="Video Feed")
        self.video_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # ส่วนควบคุม
        control_frame = ttk.LabelFrame(main_frame, text="Controls", width=300)
        control_frame.pack(fill=tk.Y, side=tk.RIGHT, padx=5)
        
        # ปุ่มแสดง/ซ่อนวิดีโอ
        ttk.Checkbutton(
            control_frame, 
            text="Show Video", 
            variable=self.show_video,
            command=self.toggle_video_display
        ).pack(pady=5, anchor=tk.W)
        
        # สถานะระบบ
        self.status_label = ttk.Label(control_frame, text="Status: Ready")
        self.status_label.pack(pady=5, anchor=tk.W)
        
        # สถานะโซน
        zone_status_frame = ttk.LabelFrame(control_frame, text="Zone Status")
        zone_status_frame.pack(fill=tk.X, pady=5)
        
        self.zone_status_text = tk.Text(
            zone_status_frame, 
            height=10, 
            width=30,
            state=tk.DISABLED
        )
        self.zone_status_text.pack(fill=tk.BOTH, expand=True)
        
        # ปุ่มปิดโปรแกรม
        ttk.Button(control_frame, text="Quit", command=self.cleanup_and_quit).pack(pady=10)
    
    def toggle_video_display(self):
        """สลับการแสดงผลวิดีโอ"""
        if not self.show_video.get() and self.current_frame is not None:
            self.video_label.config(image='')
    
    def update_zone_status(self, status: List[Dict[str, Any]]):
        """อัพเดทสถานะโซนใน UI"""
        self.zone_status_text.config(state=tk.NORMAL)
        self.zone_status_text.delete(1.0, tk.END)
        
        for zone in status:
            status_text = f"{zone['name']}: {'Occupied' if zone['occupied'] else 'Empty'}\n"
            self.zone_status_text.insert(tk.END, status_text)
        
        self.zone_status_text.config(state=tk.DISABLED)
    
    def draw_zones(self, frame: np.ndarray, zones: List[Dict[str, Any]]) -> np.ndarray:
        """วาดโซนบนภาพ"""
        annotated_frame = frame.copy()
        for zone in zones:
            points = np.array([[point['x'], point['y']] for point in zone['points']], np.int32)
            points = points.reshape((-1, 1, 2))
            color = (0, 255, 0) if not zone.get('occupied', False) else (0, 0, 255)
            cv2.polylines(annotated_frame, [points], isClosed=True, color=color, thickness=2)
            cv2.putText(
                annotated_frame, 
                zone['name'], 
                (points[0][0][0], points[0][0][1] - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, 
                color, 
                2
            )
        return annotated_frame
    
    def is_point_in_zone(self, x: int, y: int, zone: Dict[str, Any]) -> bool:
        """ตรวจสอบว่าจุดอยู่ในโซนหรือไม่"""
        points = np.array([[point['x'], point['y']] for point in zone['points']])
        return cv2.pointPolygonTest(points, (x, y), False) >= 0
    
    def calculate_center(self, landmarks: List[float], width: int, height: int) -> tuple:
        """คำนวณจุดศูนย์กลางจาก landmarks"""
        x_coords = landmarks[::2]
        y_coords = landmarks[1::2]
        return int(np.mean(x_coords) * width), int(np.mean(y_coords) * height)
    
    def send_annotated_image(self, frame: np.ndarray):
        """ส่งภาพที่มีการวาดโซน"""
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            
            msg = {
                "frame": jpg_as_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.annotated_img_socket.send_string("AnnotatedFrame", zmq.SNDMORE)
            self.annotated_img_socket.send_string(json.dumps(msg))
        except Exception as e:
            print(f"Error sending annotated image: {e}")
    
    def process_frames(self):
        """ประมวลผลภาพหลัก"""
        try:
            # ค่าเริ่มต้น
            zone_status = [{"name": zone['name'], "occupied": False} 
                         for zone in self.zones_data['zones']]
            occupied_zones = []
            width, height = 0, 0
            
            # รับภาพ
            frame = self.receive_frame()
            
            # รับข้อมูลท่าทาง
            landmarks, width, height = self.receive_pose_data()
            
            if frame is not None and landmarks is not None:
                center_x, center_y = self.calculate_center(landmarks, width, height)
                
                # ตรวจสอบโซน
                zone_status, occupied_zones = self.check_zones(
                    center_x, center_y, 
                    zone_status, 
                    frame, 
                    width, 
                    height
                )
                
                # วาดโซนบนภาพ
                annotated_frame = self.draw_zones(frame, zone_status)
                
                # ส่งภาพหากมีคนอยู่ในโซน
                if occupied_zones:
                    self.send_annotated_image(annotated_frame)
            
            # ส่งข้อมูลโซน
            self.send_zone_data(zone_status, occupied_zones, width, height)
            
            # อัพเดท UI
            self.update_ui(zone_status, frame)
            
            # จัดการเฟรมถัดไป
            self.after_id = self.root.after(30, self.process_frames)
            
        except Exception as e:
            self.handle_error(e)
    
    def receive_frame(self) -> np.ndarray:
        """รับภาพจาก ZMQ"""
        try:
            frame_topic = self.frame_socket.recv_string(flags=zmq.NOBLOCK)
            frame_data_json = self.frame_socket.recv_string(flags=zmq.NOBLOCK)
            frame_data = json.loads(frame_data_json)
            jpg_as_text = frame_data["frame"]
            jpg_original = base64.b64decode(jpg_as_text)
            return cv2.imdecode(np.frombuffer(jpg_original, dtype=np.uint8), cv2.IMREAD_COLOR)
        except zmq.Again:
            return None
    
    def receive_pose_data(self) -> tuple:
        """รับข้อมูลท่าทางจาก ZMQ"""
        try:
            pose_topic = self.pose_socket.recv_string(flags=zmq.NOBLOCK)
            pose_data_json = self.pose_socket.recv_string(flags=zmq.NOBLOCK)
            pose_data = json.loads(pose_data_json)
            return (
                pose_data["Landmarks"],
                pose_data["MAX_Width"],
                pose_data["MAX_Height"]
            )
        except zmq.Again:
            return None, 0, 0
    
    def check_zones(self, x: int, y: int, zones: List[Dict[str, Any]], 
                   frame: np.ndarray, width: int, height: int) -> tuple:
        """ตรวจสอบการครอบครองโซน"""
        occupied_zones = []
        for zone in zones:
            if self.is_point_in_zone(x, y, zone):
                zone['occupied'] = True
                occupied_zones.append(zone['name'])
                if self.show_video.get():
                    cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)
                    cv2.putText(
                        frame, 
                        f"Person in {zone['name']}", 
                        (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, 
                        (0, 0, 255), 
                        2
                    )
            else:
                zone['occupied'] = False
        return zones, occupied_zones
    
    def send_zone_data(self, zones: List[Dict[str, Any]], occupied: List[str], 
                      width: int, height: int):
        """ส่งข้อมูลโซน"""
        self.zone_socket.send_string("ZoneData", zmq.SNDMORE)
        self.zone_socket.send_string(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "zones": zones,
            "occupied_zones": occupied,
            "image_size": {"width": width, "height": height}
        }))
    
    def update_ui(self, zones: List[Dict[str, Any]], frame: np.ndarray):
        """อัพเดทส่วนติดต่อผู้ใช้"""
        self.update_zone_status(zones)
        
        if frame is not None and self.show_video.get():
            display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(display_frame)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            self.current_frame = imgtk
    
    def handle_error(self, error: Exception):
        """จัดการข้อผิดพลาด"""
        messagebox.showerror("Error", f"An error occurred: {str(error)}")
        self.cleanup_and_quit()
    
    def cleanup_and_quit(self):
        """ทำความสะอาดและปิดโปรแกรม"""
        if self.after_id:
            self.root.after_cancel(self.after_id)
        
        self.frame_socket.close()
        self.pose_socket.close()
        self.zone_socket.close()
        self.annotated_img_socket.close()
        self.context.term()
        
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ZoneDetectorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.cleanup_and_quit)
    root.mainloop()