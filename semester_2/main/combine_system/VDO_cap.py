import cv2

i = 0  # ตัวแปร global สำหรับการนับชื่อไฟล์

def capture_image():
    global i  # ทำให้ i เป็นตัวแปร global
    # เปิดกล้อง (0 คือค่าเริ่มต้นสำหรับกล้องหลัก)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("ไม่สามารถเปิดกล้องได้")
        return
    
    print("กด 'SPACE' เพื่อถ่ายภาพ, กด 'ESC' เพื่อออก")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("ไม่สามารถอ่านภาพจากกล้องได้")
            break
        
        cv2.imshow("Camera", frame)
        key = cv2.waitKey(1) & 0xFF
        
        if key == 32:  # กด SPACE เพื่อถ่ายภาพ
            filename = f"captured_image{i}.jpg"
            cv2.imwrite(filename, frame)
            print(f"บันทึกภาพไปที่ {filename}")
            i += 1  # เพิ่มค่า i เพื่อให้ไฟล์มีชื่อที่ไม่ซ้ำกัน
        elif key == 27:  # กด ESC เพื่อออก
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    capture_image()
