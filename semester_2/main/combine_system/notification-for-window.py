import zmq
import json
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
from datetime import datetime
import base64

class FallNotificationApp:
    def __init__(self, root):
        self.root = root
        self.current_alert = None
        self.zone_image = None
        self.graph_image = None  # สำหรับเก็บภาพกราฟ
        self.sound_enabled = True
        
        # Setup ZMQ
        self.context = zmq.Context()
        self.alert_socket = self.context.socket(zmq.SUB)
        self.alert_socket.connect("tcp://localhost:5560")
        self.alert_socket.setsockopt_string(zmq.SUBSCRIBE, "FallAlert")
        
        # Setup image socket
        self.image_socket = self.context.socket(zmq.SUB)
        self.image_socket.connect("tcp://localhost:5561")
        self.image_socket.setsockopt_string(zmq.SUBSCRIBE, "Sender_frame")
        
        # Setup graph image socket
        self.graph_socket = self.context.socket(zmq.SUB)
        self.graph_socket.connect("tcp://localhost:5558")
        self.graph_socket.setsockopt_string(zmq.SUBSCRIBE, "GraphImage")
        
        # เพิ่ม socket สำหรับรับข้อมูลโซน
        self.zone_socket = self.context.socket(zmq.SUB)
        self.zone_socket.connect("tcp://localhost:5557")
        self.zone_socket.setsockopt_string(zmq.SUBSCRIBE, "ZoneData")
        
        # ใช้ Poller
        self.poller = zmq.Poller()
        self.poller.register(self.alert_socket, zmq.POLLIN)
        self.poller.register(self.image_socket, zmq.POLLIN)
        self.poller.register(self.zone_socket, zmq.POLLIN)
        self.poller.register(self.graph_socket, zmq.POLLIN)
        
        self.setup_ui()
        self.check_alerts()
        self.check_graph_images()  # เริ่มตรวจสอบภาพกราฟ
    
    def setup_ui(self):
        self.root.title("Fall Detection Notification System")
        self.root.geometry("1000x800")  # ขยายขนาดหน้าต่าง
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Alert frame
        alert_frame = ttk.LabelFrame(main_frame, text="Fall Alert", padding="10")
        alert_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.alert_label = ttk.Label(
            alert_frame, 
            text="No active alerts", 
            font=('Helvetica', 14), 
            foreground='green'
        )
        self.alert_label.pack(pady=10)
        
        self.zone_label = ttk.Label(
            alert_frame,
            text="Zone: --",
            font=('Helvetica', 12)
        )
        self.zone_label.pack(pady=5)
        
        self.timestamp_label = ttk.Label(
            alert_frame,
            text="Timestamp: --",
            font=('Helvetica', 10)
        )
        self.timestamp_label.pack(pady=5)
        
        # Image frames container
        image_container = ttk.Frame(main_frame)
        image_container.pack(fill=tk.BOTH, expand=True)
        
        # Original image frame
        original_frame = ttk.LabelFrame(image_container, text="Original Image", padding="10")
        original_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.image_label = ttk.Label(original_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # Graph image frame
        graph_frame = ttk.LabelFrame(image_container, text="Zone Graph", padding="10")
        graph_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.graph_label = ttk.Label(graph_frame)
        self.graph_label.pack(fill=tk.BOTH, expand=True)
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Left buttons frame
        left_btn_frame = ttk.Frame(btn_frame)
        left_btn_frame.pack(side=tk.LEFT)
        
        ttk.Button(left_btn_frame, text="Acknowledge", command=self.acknowledge_alert).pack(side=tk.LEFT, padx=5)
        
        self.sound_btn = ttk.Button(
            left_btn_frame, 
            text="Disable Sound", 
            command=self.toggle_sound
        )
        self.sound_btn.pack(side=tk.LEFT, padx=5)
        
        # Right buttons frame
        right_btn_frame = ttk.Frame(btn_frame)
        right_btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(right_btn_frame, text="Emergency Contact", command=self.emergency_contact).pack(side=tk.RIGHT)
    
    def toggle_sound(self):
        """สลับสถานะการเปิด/ปิดเสียง"""
        self.sound_enabled = not self.sound_enabled
        
        if self.sound_enabled:
            self.sound_btn.config(text="Disable Sound")
            messagebox.showinfo("Sound", "Sound alerts enabled")
        else:
            self.sound_btn.config(text="Enable Sound")
            messagebox.showinfo("Sound", "Sound alerts disabled")
    
    def check_alerts(self):
        socks = dict(self.poller.poll(100))
        
        if self.alert_socket in socks:
            # รับข้อความแจ้งเตือน
            topic = self.alert_socket.recv_string()
            alert_data = json.loads(self.alert_socket.recv_string())
            self.handle_alert(alert_data)
        
        if self.zone_socket in socks:
            # รับข้อมูลโซน
            topic = self.zone_socket.recv_string()
            zone_data = json.loads(self.zone_socket.recv_string())
            self.update_zone_display(zone_data)
        
        if self.image_socket in socks:
            # รับภาพ
            topic = self.image_socket.recv_string()
            image_data = json.loads(self.image_socket.recv_string())
            self.process_image(image_data)
        
        if self.graph_socket in socks:
            # รับกราฟ
            topic = self.graph_socket.recv_string()
            graph_data = json.loads(self.graph_socket.recv_string())
            self.process_graph(graph_data)
        
        self.root.after(100, self.check_alerts)
    
    def check_graph_images(self):
        """ตรวจสอบและรับภาพกราฟจากโปรแกรมส่ง"""
        try:
            topic = self.graph_socket.recv_string(flags=zmq.NOBLOCK)
            data_json = self.graph_socket.recv_string(flags=zmq.NOBLOCK)
            data = json.loads(data_json)
            
            jpg_as_text = data["frame"]
            jpg_original = base64.b64decode(jpg_as_text)
            img_array = np.frombuffer(jpg_original, dtype=np.uint8)
            self.graph_image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            self.update_graph_display()
            
        except zmq.Again:
            pass
        except Exception as e:
            print(f"Error receiving graph image: {e}")
        finally:
            self.root.after(100, self.check_graph_images)
    
    def capture_zone_image(self):
        try:
            topic = self.image_socket.recv_string(flags=zmq.NOBLOCK)
            data_json = self.image_socket.recv_string(flags=zmq.NOBLOCK)
            data = json.loads(data_json)
            
            jpg_as_text = data["frame"]
            jpg_original = base64.b64decode(jpg_as_text)
            img_array = np.frombuffer(jpg_original, dtype=np.uint8)
            self.zone_image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            self.update_image_display()
            
        except zmq.Again:
            pass
        except Exception as e:
            print(f"Error capturing zone image: {e}")
    
    def update_alert_display(self):
        if self.current_alert:
            state = self.current_alert['state']
            zone = self.current_alert.get('zone', 'Unknown')
            
            if state == 2:
                self.alert_label.config(
                    text="ALERT: Person has fallen!",
                    foreground='red',
                    font=('Helvetica', 16, 'bold')
                )
                if self.sound_enabled:
                    self.play_alert_sound()
            elif state == 1:
                self.alert_label.config(
                    text="WARNING: Person may fall!",
                    foreground='orange',
                    font=('Helvetica', 14, 'bold')
                )
            else:
                self.alert_label.config(
                    text="Normal: No fall detected",
                    foreground='green',
                    font=('Helvetica', 14)
                )
            
            self.zone_label.config(text=f"Zone: {zone}")
            self.timestamp_label.config(text=f"Time: {self.current_alert['timestamp']}")
    
    def update_image_display(self):
        if self.zone_image is not None:
            self._update_display(self.zone_image, self.image_label)
    
    def update_graph_display(self):
        if self.graph_image is not None:
            self._update_display(self.graph_image, self.graph_label)
    
    def _update_display(self, image, label):
        """อัพเดทการแสดงผลภาพบน Label ที่กำหนด"""
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        height, width = img_rgb.shape[:2]
        max_height = 400
        if height > max_height:
            ratio = max_height / height
            img_rgb = cv2.resize(img_rgb, (int(width * ratio), max_height))
        
        img_pil = Image.fromarray(img_rgb)
        img_tk = ImageTk.PhotoImage(image=img_pil)
        
        label.config(image=img_tk)
        label.image = img_tk
    
    def play_alert_sound(self):
        """เล่นเสียงเตือนเมื่อเปิดเสียงอยู่"""
        if not self.sound_enabled:
            return
            
        try:
            import winsound
            winsound.Beep(1000, 1000)
        except:
            try:
                import os
                os.system('afplay /System/Library/Sounds/Sosumi.aiff')
            except:
                print("Could not play alert sound")
    
    def acknowledge_alert(self):
        self.current_alert = None
        self.alert_label.config(
            text="No active alerts", 
            foreground='green',
            font=('Helvetica', 14)
        )
        self.zone_label.config(text="Zone: --")
        self.timestamp_label.config(text="Timestamp: --")
        self.image_label.config(image='')
        self.image_label.image = None
    
    def emergency_contact(self):
        if self.current_alert and self.current_alert['state'] == 2:
            messagebox.showwarning(
                "Emergency Contact", 
                "Contacting emergency services and designated contacts..."
            )

if __name__ == "__main__":
    root = tk.Tk()
    app = FallNotificationApp(root)
    root.mainloop()