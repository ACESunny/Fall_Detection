import cv2
import os
from tkinter import Tk, filedialog, messagebox

# ตั้งค่าให้ tkinter ไม่แสดงหน้าต่างหลัก
Tk().withdraw()

# แสดงหน้าต่างให้ผู้ใช้เลือกโฟลเดอร์ที่จะบันทึก
folder_choice = messagebox.askquestion("Select Folder", "Do you want to save frames in the 'raw' folder? Click 'Yes' for raw, 'No' for pose.")

# กำหนดโฟลเดอร์หลักตามการเลือก
if folder_choice == 'yes':
    output_folder = 'pictures/raw'
    video_folder = 'vdo/vdo_raw'  # โฟลเดอร์ต้นทางสำหรับ raw
else:
    output_folder = 'pictures/pose'
    video_folder = 'vdo/vdo_pose'  # โฟลเดอร์ต้นทางสำหรับ pose

# ตรวจสอบว่าโฟลเดอร์ต้นทางมีอยู่หรือไม่
if not os.path.exists(video_folder):
    print(f"Error: Source folder '{video_folder}' does not exist.")
else:
    # สร้างโฟลเดอร์หลักที่ต้องการบันทึกรูป
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # ให้ผู้ใช้เลือกไฟล์วีดีโอจากโฟลเดอร์ต้นทาง
    video_files = filedialog.askopenfilenames(
        title="Select video files",
        initialdir=video_folder,
        filetypes=[("MP4 files", "*.mp4")]
    )

    # ตรวจสอบว่าได้เลือกไฟล์อย่างน้อย 1 ไฟล์
    if not video_files:
        print("No files selected.")
    else:
        # ประมวลผลวีดีโอแต่ละไฟล์ที่เลือก
        for video_file in video_files:
            # สร้างชื่อโฟลเดอร์ย่อยตามชื่อวีดีโอ
            video_name = os.path.splitext(os.path.basename(video_file))[0]
            video_output_folder = os.path.join(output_folder, f'{video_name}')
            
            # สร้างโฟลเดอร์ย่อยถ้ายังไม่มี
            if not os.path.exists(video_output_folder):
                os.makedirs(video_output_folder)
            
            # เปิดวีดีโอ
            cap = cv2.VideoCapture(video_file)
            frame_count = 0

            # ตรวจสอบว่าสามารถเปิดวีดีโอได้หรือไม่
            if not cap.isOpened():
                print(f"Error: Cannot open video {video_file}")
                continue
            
            # ดึงเฟรมจากวีดีโอและบันทึก
            while True:
                ret, frame = cap.read()
                if not ret:  # ถ้าไม่มีเฟรมอีกแล้ว
                    break
                
                # สร้างชื่อไฟล์รูปภาพ
                frame_filename = os.path.join(video_output_folder, f'frame_{frame_count:04d}.jpg')
                
                # บันทึกรูปภาพ
                cv2.imwrite(frame_filename, frame)
                frame_count += 1

            print(f"Saved {frame_count} frames to {video_output_folder}")
            
            # ปิดวีดีโอ
            cap.release()
