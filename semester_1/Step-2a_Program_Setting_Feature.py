import pandas as pd
import numpy as np
import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
import threading  # เพิ่ม threading

# ฟังก์ชันหลักที่ทำงานตามที่อธิบาย
def calculate_rates(file_path, frame_rate_threshold, use_frame_rate, use_machine_frame_rate, progress_callback):
    # อ่านไฟล์ CSV
    data = pd.read_csv(file_path)
    
    # กำหนดลิสต์เพื่อเก็บค่าผลลัพธ์
    frame_rates = []
    cog_angles = []
    movement_rates = []

    # กำหนดจุดที่เชื่อมต่อสำหรับ Movement Rate
    connections = [(0, 11), (11, 12), (12, 24), (24, 23), (23, 11), 
                   (15, 13), (13, 11), (12, 14), (14, 16), 
                   (23, 25), (25, 27), (24, 26), (26, 28)]

    # คำนวณค่าตามจำนวนเฟรมที่มี n เป็นเฟรมก่อนหน้า n + 1 เฟรมปัจจุบัน
    for n in range(len(data) - 1):  # เฟรมเริ่มจาก 0 ถึง len(data) - 2
        # คำนวณ Frame Rate
        if use_machine_frame_rate: 
            frame_rate = 1  # กำหนด Frame Rate เป็น 1 เมื่อใช้ machine frame rate
        else:
            image_timestamp_n = data['Image_Timestamp'][n]
            pose_timestamp_n = data['Pose_Timestamp'][n]
            if n + 1 < len(data):
                image_timestamp_n1 = data['Image_Timestamp'][n + 1]  # เฟรมปัจจุบัน
                pose_timestamp_n1 = data['Pose_Timestamp'][n + 1]  # เฟรมปัจจุบัน
                
                frame_diff_n = abs(image_timestamp_n - pose_timestamp_n)
                frame_diff_n1 = abs(image_timestamp_n1 - pose_timestamp_n1)  # เฟรมปัจจุบัน
                frame_rate = abs(frame_diff_n - frame_diff_n1)
            else:
                frame_rate = 0  # กำหนดค่าเป็น 0 สำหรับเฟรมสุดท้ายที่ไม่มีการคำนวณ

        # ตรวจสอบ frame_rate น้อยกว่า threshold
        if use_frame_rate and frame_rate < frame_rate_threshold:
            frame_rates.append(0)  # บันทึก 0 แทนเฟรมที่ข้าม
            cog_angles.append(0)  # บันทึก 0 สำหรับมุม COG
            movement_rates.append(0)  # บันทึก 0 สำหรับ Movement Rate
            continue  

        frame_rates.append(frame_rate)

        frame_no = n + 1 # เฟรมปัจจุบัน

        frame_data_left_x = data['x23'][frame_no]
        frame_data_left_y = data['y23'][frame_no]

        frame_data_right_x = data['x24'][frame_no]
        frame_data_right_y = data['y24'][frame_no]

        frame_data_nose_x = data['x0'][frame_no]
        frame_data_nose_y = data['y0'][frame_no]
        
        # คำนวณ Center of Gravity Angle
        cog_x_n1 = (frame_data_right_x + frame_data_left_x) / 2
        cog_y_n1 = (frame_data_right_y + frame_data_left_y) / 2
        
        # Slope 
        dx_n1 = cog_x_n1 - frame_data_nose_x  # x ของตำแหน่งอ้างอิงที่เฟรม ปัจจุบัน
        dy_n1 = cog_y_n1 - frame_data_nose_y  # y ของตำแหน่งอ้างอิงที่เฟรม ปัจจุบัน

        # คำนวณมุม COG ในเฟรม ปัจจุบัน
        angle_n1 = np.arctan2(abs(dy_n1), abs(dx_n1)) * (180 / np.pi)
        # angle_n1 = np.arctan2(dy_n1, dx_n1) * ( 180 / np.pi )


        cog_angles.append(angle_n1)
        
        # คำนวณ Movement Rate
        total_length_n = 0
        total_length_n1 = 0
        
        for connection in connections:
            point_a_n = data[f'x{connection[0]}'][n]
            point_b_n = data[f'x{connection[1]}'][n]
            # point_a_n = data.iloc[n, connection[0]]
            # point_b_n = data.iloc[n, connection[1]]
            total_length_n += np.sqrt(((point_a_n - point_b_n) ** 2) + ((data[f'y{connection[0]}'][n] - (data[f'y{connection[1]}'][n])) ** 2))
            
            # if n + 1 < len(data):
                # point_a_n1 = 
                # point_b_n1 = data[f'y{connection[0]}'][n + 1]
                # point_a_n1 = data.iloc[n + 1, connection[0]]
                # point_b_n1 = data.iloc[n + 1, connection[1]]
                # total_length_n1 += np.sqrt((point_a_n1 - point_b_n1) ** 2 + (data.iloc[n + 1, connection[0] + 1] - data.iloc[n + 1, connection[1] + 1]) ** 2)
            # else:
            #     total_length_n1 += 0  # กำหนดเป็น 0 ถ้าไม่มีเฟรมถัดไป

        movement_rate_n = np.sqrt((((total_length_n - total_length_n1) ** 2) / 1920) + (((total_length_n - total_length_n1) ** 2) / 1080)) / frame_rate

        movement_rates.append(movement_rate_n)

        # อัพเดต progress bar
        progress_callback(n + 1, len(data) - 1)

    # สร้าง DataFrame สำหรับผลลัพธ์
    result_df = pd.DataFrame({
        'Frame_Rate': frame_rates,
        'CoG_Angles': cog_angles,
        'Movement_Rate': movement_rates
    })

    # สร้าง path สำหรับบันทึกผลลัพธ์
    if use_frame_rate:
        folder_name = f"threshold_{str(frame_rate_threshold).replace('.', '_')}"
    elif use_machine_frame_rate:
        folder_name = "without_frame_rate"  # เมื่อเลือก checkbox ที่ 2
    else:
        folder_name = "without_threshold"
        
    output_dir = os.path.join("csv", "csv_feature", folder_name)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_csv_path = os.path.join(output_dir, f"{os.path.basename(file_path)}")
    
    # บันทึกผลลัพธ์ลงใน CSV
    result_df.to_csv(output_csv_path, index=False)

# ฟังก์ชันใน GUI ที่จะทำงานใน thread แยก
def process_files_in_thread(file_paths, threshold_value, use_threshold, use_machine_frame_rate, progress_bar, root):
    for idx, file_path in enumerate(file_paths):
        # อัพเดต progress bar
        progress_bar['maximum'] = len(file_paths)
        progress_bar['value'] = idx + 1
        root.update_idletasks()  # อัพเดต UI
        calculate_rates(file_path, threshold_value, use_threshold, use_machine_frame_rate, lambda x, total: progress_bar.config(value=(x/total)*100))
    
    messagebox.showinfo("Success", "Data processed and saved successfully for selected files!")

# GUI ส่วนประกอบ
def open_gui():
    # สร้างหน้าต่าง GUI
    root = tk.Tk()
    root.title("Feature Settings")

    # กำหนดขนาดหน้าต่าง
    window_width = 400
    window_height = 300
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # คำนวณตำแหน่งให้หน้าต่างอยู่กลางหน้าจอ
    position_top = int(screen_height / 2 - window_height / 2)
    position_left = int(screen_width / 2 - window_width / 2)

    # ตั้งค่าตำแหน่งและขนาดหน้าต่าง
    root.geometry(f'{window_width}x{window_height}+{position_left}+{position_top}')

    # สร้าง Frame เพื่อรวมทั้งหมดให้อยู่กลาง
    frame = ttk.Frame(root)
    frame.place(relx=0.5, rely=0.5, anchor='center')

    # กรอกค่า Frame Rate Threshold
    label = ttk.Label(frame, text="Set Frame Rate Threshold")
    label.grid(row=0, column=0, pady=10)

    frame_rate_threshold_var = tk.DoubleVar(value=0.0039)
    entry = ttk.Entry(frame, textvariable=frame_rate_threshold_var)
    entry.grid(row=1, column=0, pady=10)

    # Checkbox สำหรับเลือกใช้งาน threshold
    use_threshold_var = tk.BooleanVar(value=True)
    checkbox = ttk.Checkbutton(frame, text="Use Frame Rate Threshold", variable=use_threshold_var)
    checkbox.grid(row=2, column=0, pady=10)

    # Checkbox สำหรับเลือกว่าจะใช้ frame rate จากเครื่องหรือไม่
    use_machine_frame_rate_var = tk.BooleanVar(value=False)
    checkbox_machine_frame_rate = ttk.Checkbutton(frame, text="ไม่ใช้งานเฟรมเรดจากเครื่อง (frame rate = 1)", variable=use_machine_frame_rate_var)
    checkbox_machine_frame_rate.grid(row=3, column=0, pady=10)

    # ฟังก์ชัน Apply
    def on_apply():
        threshold_value = frame_rate_threshold_var.get()
        use_threshold = use_threshold_var.get()
        use_machine_frame_rate = use_machine_frame_rate_var.get()

        # เลือกไฟล์จากโฟล์เดอร์ csv/csv_raw
        file_paths = filedialog.askopenfilenames(
            initialdir="csv/csv_raw",
            title="Select CSV Files",
            filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*"))
        )
        if not file_paths:
            messagebox.showwarning("Error", "Please select at least one file.")
            return
        
        # สร้าง Progress Bar
        progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        progress_bar.grid(row=5, column=0, pady=20)
        
        # เรียกใช้ฟังก์ชัน process ใน thread ใหม่
        thread = threading.Thread(target=process_files_in_thread, args=(file_paths, threshold_value, use_threshold, use_machine_frame_rate, progress_bar, root))
        thread.start()

    # ปุ่ม Apply
    apply_button = ttk.Button(frame, text="Apply", command=on_apply)
    apply_button.grid(row=4, column=0, pady=10)

    root.mainloop()

# เรียกใช้งาน GUI
open_gui()
