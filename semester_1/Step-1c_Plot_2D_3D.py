import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilenames
from tqdm import tqdm  # Import tqdm for the progress bar

# ซ่อนหน้าต่างหลักของ tkinter
Tk().withdraw()

# เปิดหน้าต่างเลือกหลายไฟล์ CSV โดยเริ่มต้นที่โฟลเดอร์ "csv/csv_raw"
file_paths = askopenfilenames(initialdir="csv/csv_raw/xyz", title="Select CSV files", filetypes=[("CSV files", "*.csv")])

# ตรวจสอบว่ามีการเลือกไฟล์อย่างน้อยหนึ่งไฟล์
if file_paths:
    # กำหนดการเชื่อมต่อจุด
    connections = [
        (11, 12), (12, 24), (24, 23), (23, 11),
        (15, 13), (13, 11), (12, 14), (14, 16),
        (23, 25), (25, 27), (24, 26), (26, 28)
    ]
    poin = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

    # ฟังก์ชันวาดกราฟ 2D
    def plot_2d(frame_data, frame_index, output_folder_2D):
        plt.figure(figsize=(10, 8))
        for connection in connections:
            x1, y1 = frame_data[f'x{connection[0]}'], frame_data[f'y{connection[0]}']
            x2, y2 = frame_data[f'x{connection[1]}'], frame_data[f'y{connection[1]}']
            plt.plot([x1, x2], [y1, y2], 'g-', linewidth=2)

        # วาดจุด
        for i in poin:
            x, y = frame_data[f'x{i}'], frame_data[f'y{i}']
            plt.plot(x, y, 'ro', markersize=5)
            
        # คำนวณ Center of Gravity (CoG) ระหว่างจุดที่ 24 และ 23
        x_cog = (frame_data['x24'] + frame_data['x23']) / 2
        y_cog = (frame_data['y24'] + frame_data['y23']) / 2
        
        # วาดเส้นระหว่างจุด 0 กับ CoG
        plt.plot([frame_data['x0'], x_cog], [frame_data['y0'], y_cog], 'bo-', linewidth=2)

        # วาดจุด CoG
        plt.plot(x_cog, y_cog, 'bo', markersize=7)

        # ตั้งค่าขอบเขตแกน x และ y
        plt.xlim(0, 1920)
        plt.ylim(0, 1080)
        plt.gca().invert_yaxis()
        plt.grid(True)
        plt.title(f'2D Pose Plot - Frame {frame_index}')
        plt.xlabel('X')
        plt.ylabel('Y')
        
        # บันทึกภาพ
        plt.savefig(os.path.join(output_folder_2D, f'2D_Pose_Frame_{frame_index}.png'))
        plt.close()

    # ฟังก์ชันวาดกราฟ 3D
    def plot_3d(frame_data, frame_index, output_folder_3D):
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        for connection in connections:
            x1, y1, z1 = frame_data[f'x{connection[0]}'], frame_data[f'z{connection[0]}'], frame_data[f'y{connection[0]}']
            x2, y2, z2 = frame_data[f'x{connection[1]}'], frame_data[f'z{connection[1]}'], frame_data[f'y{connection[1]}']
            ax.plot([x1, x2], [y1, y2], [z1, z2], 'g-', linewidth=2)

        # วาดจุด
        for i in poin:
            x, y, z = frame_data[f'x{i}'], frame_data[f'z{i}'], frame_data[f'y{i}']
            ax.scatter(x, y, z, c='r', s=20)

        # คำนวณ Center of Gravity (CoG) ระหว่างจุดที่ 24 และ 23
        x_cog = (frame_data['x24'] + frame_data['x23']) / 2
        y_cog = (frame_data['y24'] + frame_data['y23']) / 2
        z_cog = (frame_data['z24'] + frame_data['z23']) / 2

        # วาดจุด CoG
        ax.scatter(x_cog, y_cog, z_cog, c='b', s=30)

        # ตั้งค่าขอบเขตของแกน X, Y และ Z
        ax.set_xlim(1920, 0)
        ax.set_ylim(-1, 1)
        ax.set_zlim(1080, 0)

        # ปรับมุมมอง
        ax.view_init(elev=20, azim=60)
        ax.set_title(f'3D Pose Plot - Frame {frame_index}')
        ax.set_xlabel('X')
        ax.set_ylabel('Z (Depth)')
        ax.set_zlabel('Y')
        
        # บันทึกภาพ
        plt.savefig(os.path.join(output_folder_3D, f'3D_Pose_Frame_{frame_index}.png'))
        plt.close()

    # สร้างโฟลเดอร์หลัก pictures/plot2D3D หากยังไม่มี
    main_output_folder = 'pictures/plot2D3D'
    os.makedirs(main_output_folder, exist_ok=True)

    # วนลูปผ่านแต่ละไฟล์ที่เลือก
    for file_path in file_paths:
        # อ่านข้อมูล CSV
        data = pd.read_csv(file_path)

        # สร้างโฟลเดอร์สำหรับบันทึกภาพ 2D และ 3D สำหรับไฟล์แต่ละไฟล์
        base_output_folder = os.path.join(main_output_folder, f'{os.path.basename(file_path).replace(".csv", "")}')
        output_folder_2D = os.path.join(base_output_folder, '2D')
        output_folder_3D = os.path.join(base_output_folder, '3D')
        os.makedirs(output_folder_2D, exist_ok=True)
        os.makedirs(output_folder_3D, exist_ok=True)

        # วนลูปผ่านเฟรมทั้งหมดใน DataFrame และบันทึกภาพ
        for frame_index in tqdm(range(len(data)), desc=f"Processing {os.path.basename(file_path)}"):
            frame_data = data.iloc[frame_index]
            plot_2d(frame_data, frame_index, output_folder_2D)
            plot_3d(frame_data, frame_index, output_folder_3D)

    print("All frames have been saved successfully.")
else:
    print("No files selected.")
