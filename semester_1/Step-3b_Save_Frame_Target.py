# โปรแกรมบันทึกภาพในเฟรมที่กำหนด

import cv2
import os

vdo_name = str(input('Enter Name VDO: '))
# video_path = f'vdo_pose/pose_{vdo_name}.mp4'  # กำหนดพาธของไฟล์วิดีโอที่ต้องการ
# vdo_name = 'fall_1l'
video_path = f'vdo_pose/pose_{vdo_name}.mp4'  # กำหนดพาธของไฟล์วิดีโอที่ต้องการ
# target_frame = 200 # กำหนดเฟรมที่ต้องการจับ
before_frame = 10
after_frame = 10
target_frame = int(input('Target frame: '))

def capture_frames(video_path, target_frame):
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    save_dir = os.path.join("picture", f"Cap_{video_name}")

    # สร้างโฟลเดอร์ Cap_ชื่อของคลิป ในโฟลเดอร์ picture
    os.makedirs(save_dir, exist_ok=True)
    
    # เปิดไฟล์วิดีโอ
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Cannot open video")
        return
    
    # คำนวณเฟรมที่ต้องการ (n - before_frame, n, n + after_frame)
    frames_to_capture = [target_frame - before_frame, target_frame, target_frame + after_frame]
    
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for frame_num in frames_to_capture:
        # ตรวจสอบว่าเฟรมอยู่ในช่วงที่วิดีโอมีอยู่หรือไม่
        if 0 <= frame_num < frame_count:
            # ตั้งค่าไปที่เฟรมที่ต้องการ
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if ret:
                # บันทึกภาพในโฟลเดอร์ที่สร้างไว้
                frame_filename = os.path.join(save_dir, f"frame_{frame_num}.jpg")
                cv2.imwrite(frame_filename, frame)
                print(f"Saved {frame_filename}")
            else:
                print(f"Could not read frame {frame_num}")
    
    # ปิดการอ่านไฟล์วิดีโอ
    cap.release()


capture_frames(video_path, target_frame)
