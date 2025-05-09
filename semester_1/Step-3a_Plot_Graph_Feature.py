import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog, messagebox
import os

# ฟังก์ชันสำหรับสร้างกราฟ
def plot_graphs():
    # สร้างหน้าต่างให้ผู้ใช้เลือกไฟล์
    Tk().withdraw()  # ซ่อนหน้าต่างหลักของ Tkinter
    file_paths = filedialog.askopenfilenames(
        title="เลือกไฟล์ CSV", 
        filetypes=[("CSV files", "*.csv")],
        initialdir='csv/csv_feature'
    )

    if not file_paths:  # ถ้าไม่ได้เลือกไฟล์
        print("ไม่มีไฟล์ถูกเลือก")
        return

    # สำหรับแต่ละไฟล์ CSV ที่เลือก
    for file_path in file_paths:
        data = pd.read_csv(file_path)

        # กรองข้อมูลเพื่อข้ามค่าที่เป็นศูนย์
        data_filtered = data[(data['Movement_Rate'] != 0) & (data['CoG_Angles'] != 0)]

        # ดึงชื่อไฟล์จาก path แล้วใช้เป็นชื่อโฟลเดอร์
        base_filename = os.path.basename(file_path).replace('.csv', '')
        
        # ดึงชื่อโฟลเดอร์ต้นทาง (ชื่อโฟลเดอร์ที่ไฟล์ CSV อยู่)
        parent_folder = os.path.dirname(file_path)
        parent_folder_name = os.path.basename(parent_folder)

        # สร้างโฟลเดอร์ใหม่ใน pictures/feature โดยใช้ชื่อไฟล์เป็นชื่อโฟลเดอร์หลัก
        target_folder = os.path.join('pictures', 'feature', base_filename, parent_folder_name)

        # สร้างโฟลเดอร์ถ้ายังไม่มี
        os.makedirs(target_folder, exist_ok=True)

        # ตั้งชื่อไฟล์และบันทึกกราฟ
        full_image_path = os.path.join(target_folder, f'{base_filename}_all_graphs.png')
        plt.figure(figsize=(12, 6))

        # กราฟ Movement Rate
        plt.subplot(1, 3, 1)
        plt.plot(data_filtered.index, data_filtered['Movement_Rate'], color='blue', linestyle='-', linewidth=1) 
        plt.title('Movement Rate')
        plt.xlabel('Frame')
        plt.ylabel('Movement Rate')

        # กราฟ Center of Gravity Angles
        plt.subplot(1, 3, 2)
        plt.plot(data_filtered.index, data_filtered['CoG_Angles'], color='red', linestyle='-', linewidth=1) 
        plt.title('Deformation')
        plt.xlabel('Frame')
        plt.ylabel('Angles')

        # กราฟ Scatter Plot
        plt.subplot(1, 3, 3)
        plt.scatter(data_filtered['Movement_Rate'], data_filtered['CoG_Angles'], color='purple', alpha=0.5)
        plt.title('Movement Rate vs Deformation')
        plt.xlabel('Movement Rate')
        plt.ylabel('Angles')

        # บันทึกกราฟทั้งสามในไฟล์เดียว
        plt.tight_layout()
        plt.savefig(full_image_path)

        # บันทึกกราฟแยกแต่ละอัน
        plt.figure(figsize=(6, 6))
        plt.plot(data_filtered.index, data_filtered['Movement_Rate'], color='blue', linestyle='-', linewidth=1)
        plt.title('Movement Rate')
        plt.xlabel('Frame')
        plt.ylabel('Movement Rate')
        plt.savefig(os.path.join(target_folder, f'{base_filename}_Movement_Rate.png'))

        plt.figure(figsize=(6, 6))
        plt.plot(data_filtered.index, data_filtered['CoG_Angles'], color='red', linestyle='-', linewidth=1)
        plt.title('Deformation')
        plt.xlabel('Frame')
        plt.ylabel('Angles')
        plt.savefig(os.path.join(target_folder, f'{base_filename}_CoG_Angles.png'))

        plt.figure(figsize=(6, 6))
        plt.scatter(data_filtered['Movement_Rate'], data_filtered['CoG_Angles'], color='purple', alpha=0.5)
        plt.title('Movement Rate vs Deformation')
        plt.xlabel('Movement Rate')
        plt.ylabel('Angles')
        plt.savefig(os.path.join(target_folder, f'{base_filename}_scatter.png'))

        plt.close('all')  # ปิดกราฟทุกอันหลังบันทึก

    # ถามผู้ใช้ว่าต้องการดูกราฟหรือไม่
    response = messagebox.askyesno("แสดงกราฟ", "คุณต้องการดูกราฟที่สร้างขึ้นหรือไม่?")
    if response:
        # แสดงกราฟทั้งหมด
        for file_path in file_paths:
            data = pd.read_csv(file_path)
            data_filtered = data[(data['Movement_Rate'] != 0) & (data['CoG_Angles'] != 0)]

            # สร้างกราฟและแสดง
            plt.figure(figsize=(12, 6))

            plt.subplot(1, 3, 1)
            plt.plot(data_filtered.index, data_filtered['Movement_Rate'], color='blue', linestyle='-', linewidth=1)
            plt.title('Movement Rate')
            plt.xlabel('Frame')
            plt.ylabel('Movement Rate')

            plt.subplot(1, 3, 2)
            plt.plot(data_filtered.index, data_filtered['CoG_Angles'], color='red', linestyle='-', linewidth=1)
            plt.title('Deformation')
            plt.xlabel('Frame')
            plt.ylabel('Angles')

            plt.subplot(1, 3, 3)
            plt.scatter(data_filtered['Movement_Rate'], data_filtered['CoG_Angles'], color='purple', alpha=0.5)
            plt.title('Movement Rate vs Deformation')
            plt.xlabel('Movement Rate')
            plt.ylabel('Angles')

            plt.tight_layout()
            plt.show()

# เรียกใช้งานฟังก์ชัน
plot_graphs()
