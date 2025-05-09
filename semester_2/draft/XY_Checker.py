import tkinter as tk
import zmq
import base64
import json
from PIL import Image, ImageTk
import numpy as np

class ImageViewer(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Image Viewer from Sender_frame")
        self.geometry("800x600")

        # ตั้งค่า ZeroMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("tcp://localhost:5555")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "Sender_frame")

        # สร้าง Canvas สำหรับแสดงภาพ
        self.canvas = tk.Canvas(self)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # ผูกเหตุการณ์เมาส์
        self.canvas.bind("<Motion>", self.on_mouse_move)

        # Label สำหรับแสดงตำแหน่ง X, Y
        self.image_label = tk.Label(self, text="Hover over the image to get X, Y position")
        self.image_label.pack()

        # เริ่มการอัปเดตภาพ
        self.update_image()

    def update_image(self):
        try:
            # รับเฟรมจาก ZeroMQ
            topic = self.socket.recv_string(flags=zmq.NOBLOCK)
            data_json = self.socket.recv_string(flags=zmq.NOBLOCK)
            data = json.loads(data_json)

            # แยก timestamp และเฟรม
            jpg_as_text = data["frame"]
            
            # แปลงเฟรมจาก base64 เป็นภาพ
            jpg_original = base64.b64decode(jpg_as_text)
            image = Image.fromarray(cv2.imdecode(np.frombuffer(jpg_original, dtype=np.uint8), cv2.IMREAD_COLOR))

            # แสดงภาพบน Canvas
            self.tk_image = ImageTk.PhotoImage(image)
            self.canvas.create_image(0, 0, image=self.tk_image, anchor=tk.NW)
            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        except zmq.Again:
            pass  # ไม่มีเฟรมใหม่

        # อัปเดตภาพทุกๆ 100 มิลลิวินาที
        self.after(100, self.update_image)

    def on_mouse_move(self, event):
        # แสดงตำแหน่ง X, Y ของเมาส์
        x, y = event.x, event.y
        self.image_label.config(text=f"X: {x}, Y: {y}")

if __name__ == "__main__":
    import cv2
    app = ImageViewer()
    app.mainloop()