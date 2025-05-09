import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports
import serial
import time

# แสดง Serial Ports
def get_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

# ฟังก์ชันส่ง SMS
def send_sms():
    port = port_combobox.get()
    baud_rate = baud_rate_combobox.get()
    phone_number = phone_entry.get()
    message = message_text.get("1.0", tk.END).strip()

    if not port or not baud_rate or not phone_number or not message:
        messagebox.showerror("Error", "กรุณากรอกข้อมูลให้ครบถ้วน")
        return

    try:
        # ตั้งค่า serial connection
        ser = serial.Serial(port, int(baud_rate), timeout=5)
        
        # ส่งคำสั่ง AT สำหรับ SMS text mode
        ser.write(b'AT+CMGF=1\r')
        time.sleep(1)
        
        # ตั้งค่าเบอร์ปลายทาง
        ser.write(b'AT+CMGS="' + phone_number.encode() + b'"\r')
        time.sleep(1)
        
        # ส่งข้อความ
        ser.write(message.encode() + b'\r')
        time.sleep(1)
        
        # ส่ง Ctrl+Z เพื่อสิ้นสุดการส่งข้อความ
        ser.write(bytes([26]))
        time.sleep(1)
        
        # อ่านการตอบกลับจากโมดูล
        response = ser.read(ser.in_waiting)
        print(response.decode())
        
        # ปิด serial connection
        ser.close()
        
        messagebox.showinfo("Success", "ส่งข้อความสำเร็จ!")
    except Exception as e:
        messagebox.showerror("Error", f"เกิดข้อผิดพลาด: {e}")

# ฟังก์ชันโทรออก
def make_call():
    port = port_combobox.get()
    baud_rate = baud_rate_combobox.get()
    phone_number = phone_entry.get()

    if not port or not baud_rate or not phone_number:
        messagebox.showerror("Error", "กรุณากรอกข้อมูลให้ครบถ้วน")
        return

    try:
        # ตั้งค่า serial connection
        ser = serial.Serial(port, int(baud_rate), timeout=5)
        
        # ส่งคำสั่ง AT สำหรับโทรออก
        ser.write(b'ATD' + phone_number.encode() + b';\r')
        time.sleep(1)
        
        # อ่านการตอบกลับจากโมดูล
        response = ser.read(ser.in_waiting)
        print(response.decode())
        
        # ปิด serial connection
        ser.close()
        
        messagebox.showinfo("Success", "กำลังโทรออก...")
    except Exception as e:
        messagebox.showerror("Error", f"เกิดข้อผิดพลาด: {e}")

# สร้างหน้าต่างหลัก
root = tk.Tk()
root.title("ส่ง SMS และโทรออกด้วย SIM800C")

# สร้าง Widgets
tk.Label(root, text="เลือก Serial Port:").grid(row=0, column=0, padx=10, pady=10)
port_combobox = ttk.Combobox(root, values=get_serial_ports())
port_combobox.grid(row=0, column=1, padx=10, pady=10)

tk.Label(root, text="เลือก Baud Rate:").grid(row=1, column=0, padx=10, pady=10)
baud_rate_combobox = ttk.Combobox(root, values=["9600", "19200", "38400", "57600", "115200"])
baud_rate_combobox.set("9600")  # ตั้งค่าเริ่มต้นเป็น 9600
baud_rate_combobox.grid(row=1, column=1, padx=10, pady=10)

tk.Label(root, text="เบอร์ปลายทาง:").grid(row=2, column=0, padx=10, pady=10)
phone_entry = tk.Entry(root)
phone_entry.grid(row=2, column=1, padx=10, pady=10)

tk.Label(root, text="ข้อความ:").grid(row=3, column=0, padx=10, pady=10)
message_text = tk.Text(root, height=5, width=30)
message_text.grid(row=3, column=1, padx=10, pady=10)

# ปุ่มส่งข้อความ
send_button = tk.Button(root, text="ส่งข้อความ", command=send_sms)
send_button.grid(row=4, column=0, padx=10, pady=10)

# ปุ่มโทรออก
call_button = tk.Button(root, text="โทรออก", command=make_call)
call_button.grid(row=4, column=1, padx=10, pady=10)

# เริ่มการทำงานของ GUI
root.mainloop()