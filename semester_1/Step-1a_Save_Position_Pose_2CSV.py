import pandas as pd
import cv2
import os
import mediapipe as mp
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk  # นำเข้า ttk สำหรับ Progress Bar

# ตั้งค่า MediaPipe
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5)

# ฟังก์ชันเพื่อสร้าง DataFrame และบันทึกข้อมูลเป็น CSV
def create_csv_from_videos(video_files, video_folder, output_folder, modes, progress_var, progress_bar):
    total_files = len(video_files)  # จำนวนไฟล์ที่ต้องประมวลผล
    for index, video_file in enumerate(video_files):
        video_path = os.path.join(video_folder, video_file)
        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        start_time = time.time()  # เริ่มจับเวลา

        # กำหนดคอลัมน์สำหรับแต่ละโหมด
        for mode in modes:
            if mode == 'XYZ':
                columns = ["Frames", 'Image_Timestamp', 'Pose_Timestamp'] + \
                          ["x0", "y0", "z0", "x1", "y1", "z1", "x2", "y2", "z2", "x3", "y3", "z3", "x4", "y4", "z4", 
                           "x5", "y5", "z5", "x6", "y6", "z6", "x7", "y7", "z7", "x8", "y8", "z8", "x9", "y9", "z9", 
                           "x10", "y10", "z10", "x11", "y11", "z11", "x12", "y12", "z12", "x13", "y13", "z13", "x14", "y14", "z14", 
                           "x15", "y15", "z15", "x16", "y16", "z16", "x17", "y17", "z17", "x18", "y18", "z18", "x19", "y19", "z19", 
                           "x20", "y20", "z20", "x21", "y21", "z21", "x22", "y22", "z22", "x23", "y23", "z23", "x24", "y24", "z24", 
                           "x25", "y25", "z25", "x26", "y26", "z26", "x27", "y27", "z27", "x28", "y28", "z28", "x29", "y29", "z29", 
                           "x30", "y30", "z30", "x31", "y31", "z31", "x32", "y32", "z32"]
            elif mode == 'XY':
                columns = ["Frames", 'Image_Timestamp', 'Pose_Timestamp'] + \
                          ["x0", "y0", "x1", "y1", "x2", "y2", "x3", "y3", "x4", "y4", "x5", "y5", "x6", "y6", "x7", "y7", 
                           "x8", "y8", "x9", "y9", "x10", "y10", "x11", "y11", "x12", "y12", "x13", "y13", "x14", "y14", "x15", 
                           "y15", "x16", "y16", "x17", "y17", "x18", "y18", "x19", "y19", "x20", "y20", "x21", "y21", "x22", 
                           "y22", "x23", "y23", "x24", "y24", "x25", "y25", "x26", "y26", "x27", "y27", "x28", "y28", "x29", 
                           "y29", "x30", "y30", "x31", "y31", "x32", "y32"]

            # สร้าง DataFrame ที่ว่าง
            df = pd.DataFrame(columns=columns)

            # ประมวลผล VDO ที่ผู้ใช้เลือก
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # เปลี่ยนสีจาก BGR เป็น RGB
                rgb_image_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                ih, iw, _ = rgb_image_display.shape  # รับขนาดของภาพจากเฟรมปัจจุบัน

                # บันทึก timestamp เมื่อได้รับเฟรม
                image_timestamp = time.time() - start_time

                # ประมวลผลภาพด้วย MediaPipe Pose
                results = pose.process(rgb_image_display)

                # บันทึก timestamp เมื่อได้ค่า (x, y, z)
                pose_timestamp = time.time() - start_time

                # เตรียมข้อมูลเฟรม
                frame_data = [int(frame_count), image_timestamp, pose_timestamp]

                # เช็คว่ามี landmark ที่ตรวจจับได้
                if results.pose_landmarks:
                    for i, landmark in enumerate(results.pose_landmarks.landmark):
                        if mode == 'XYZ':
                            x = int(landmark.x * iw)  # ปรับค่า x ให้อยู่ในช่วงพิกเซลของภาพ
                            y = int(landmark.y * ih)  # ปรับค่า y ให้อยู่ในช่วงพิกเซลของภาพ
                            z = landmark.z  # z คือค่า depth ของ landmark
                            frame_data.extend([x, y, z])
                        elif mode == 'XY':
                            x = int(landmark.x * iw)  # ปรับค่า x ให้อยู่ในช่วงพิกเซลของภาพ
                            y = int(landmark.y * ih)  # ปรับค่า y ให้อยู่ในช่วงพิกเซลของภาพ
                            frame_data.extend([x, y])

                # ตรวจสอบให้แน่ใจว่าข้อมูลเฟรมมีจำนวนคอลัมน์ตรงตามที่ต้องการ
                if len(frame_data) == len(columns):
                    df.loc[len(df)] = frame_data  # เพิ่มแถวใหม่ใน DataFrame

                frame_count += 1

            cap.release()  # ปิด VideoCapture

            # สร้างชื่อไฟล์ CSV จากชื่อไฟล์วีดีโอ
            csv_filename = os.path.splitext(video_file)[0] + ".csv"  # เปลี่ยนชื่อไฟล์เป็น .csv
            output_csv_folder = os.path.join(output_folder, f"csv_raw/{mode.lower()}")
            os.makedirs(output_csv_folder, exist_ok=True)  # สร้างโฟลเดอร์หากยังไม่มี
            csv_path = os.path.join(output_csv_folder, csv_filename)  # ตั้งที่อยู่ไฟล์ CSV
            df.to_csv(csv_path, index=False)  # บันทึก DataFrame เป็น CSV

        # อัปเดต progress bar หลังจากประมวลผลแต่ละไฟล์
        progress_var.set((index + 1) / total_files * 100)
        progress_bar.update()  # อัปเดตโปรแกรมให้แสดงผลลัพธ์

# ฟังก์ชันสำหรับเปิดหน้าต่างให้ผู้ใช้เลือกไฟล์ VDO
def open_file_dialog():
    video_folder = "vdo/vdo_raw"  # โฟลเดอร์ที่เก็บไฟล์วีดีโอ
    video_files = [f for f in os.listdir(video_folder) if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    
    if not video_files:
        messagebox.showerror("ข้อผิดพลาด", "ไม่พบไฟล์ VDO ในโฟลเดอร์")
        return []
    
    file_dialog = filedialog.askopenfilenames(title="เลือกไฟล์ VDO", filetypes=[("Video Files", "*.mp4;*.avi;*.mov;*.mkv")])
    return [os.path.basename(f) for f in file_dialog]  # คืนค่ารายการไฟล์ที่เลือก

# ฟังก์ชันที่ใช้สร้างหน้าต่าง GUI
def create_gui():
    # สร้างหน้าต่างหลัก
    root = tk.Tk()
    root.title("VDO Pose Processing")

    # ฟังก์ชันสำหรับการเลือกโหมด
    def on_mode_select():
        modes = []
        if xyz_var.get():
            modes.append('XYZ')
        if xy_var.get():
            modes.append('XY')

        if not modes:
            messagebox.showwarning("การเลือกโหมด", "กรุณาเลือกโหมด")
        else:
            # เปิดหน้าต่างให้เลือกไฟล์ VDO
            selected_videos = open_file_dialog()
            if selected_videos:
                # สร้างโฟลเดอร์และบันทึกไฟล์ CSV ตามโหมด
                output_folder = "csv"
                
                # สร้าง progress bar
                progress_var = tk.DoubleVar(value=0)
                progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
                progress_bar.pack(pady=10, fill="x")

                create_csv_from_videos(selected_videos, "vdo/vdo_raw", output_folder, modes, progress_var, progress_bar)
                messagebox.showinfo("สำเร็จ", f"สร้างไฟล์ CSV เรียบร้อยแล้วในโฟลเดอร์: {output_folder}/csv_raw/{', '.join(modes).lower()}")

    # เพิ่มปุ่มและตัวเลือกโหมด
    xyz_var = tk.BooleanVar(value=False)
    xy_var = tk.BooleanVar(value=False)

    mode_label = tk.Label(root, text="เลือกโหมดการทำงาน:")
    mode_label.pack(pady=10)

    mode_frame = tk.Frame(root)
    mode_frame.pack(pady=5)

    xyz_check = tk.Checkbutton(mode_frame, text="XYZ", variable=xyz_var)
    xyz_check.grid(row=0, column=0, padx=10)

    xy_check = tk.Checkbutton(mode_frame, text="XY", variable=xy_var)
    xy_check.grid(row=0, column=1, padx=10)

    # เพิ่มปุ่มสำหรับเริ่มการประมวลผล
    process_button = tk.Button(root, text="เริ่มการประมวลผล", command=on_mode_select)
    process_button.pack(pady=20)

    root.mainloop()  # เริ่มต้นโปรแกรม GUI

# เรียกใช้ฟังก์ชันเพื่อสร้างหน้าต่าง GUI
create_gui()
