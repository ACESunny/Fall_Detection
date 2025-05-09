// ========== ระบบสำหรับตรวจจับท่าทางและโซน ========== //
// ระบบนี้ประกอบด้วย 6 โมดูลหลักที่ทำงานร่วมกันผ่าน ZeroMQ

// [1] โมดูลส่งวิดีโอ (Video Sender) ไฟล์ input.py
BEGIN
    // ตั้งค่า ZeroMQ สำหรับส่งเฟรมและ FPS
    สร้าง socket สำหรับส่งเฟรม (port 5555)
    สร้าง socket สำหรับส่ง FPS (port 5558)

    // รับ input จากผู้ใช้
    รับเลือกแหล่งวิดีโอ (กล้อง/ไฟล์)
    รับเลือกการแสดงผล (แสดงวิดีโอ/แสดง FPS)

    // เปิดการเชื่อมต่อกับแหล่งวิดีโอ
    IF เปิดไม่สำเร็จ THEN จบโปรแกรม

    // ลูปหลักสำหรับส่งเฟรม
    WHILE True DO
        อ่านเฟรมจากแหล่งวิดีโอ
        IF อ่านไม่สำเร็จ THEN BREAK

        // ประมวลผลเฟรม
        แปลงเฟรมเป็น base64
        เพิ่ม timestamp
        ส่งข้อมูลผ่าน ZeroMQ (topic "Sender_frame")

        // คำนวณและส่ง FPS
        นับจำนวนเฟรมทุก 1 วินาที
        คำนวณค่า FPS
        ส่งค่า FPS ผ่าน ZeroMQ (topic "FPS")

        // แสดงผล (ถ้าเปิดไว้)
        IF แสดงวิดีโอ THEN แสดงเฟรม
        IF แสดง FPS THEN แสดงค่า FPS ใน console

        // ควบคุมความเร็วเฟรม
        หน่วงเวลาให้ตรงกับ FPS ต้นทาง
        IF กด 'q' THEN BREAK
    END WHILE

    ปิดการเชื่อมต่อทั้งหมด
END

// [2] โมดูลตรวจจับท่าทาง (Pose Detection) ไฟล์ pose_detection.py
BEGIN
    // ตั้งค่า ZeroMQ และ MediaPipe
    เชื่อมต่อกับ socket เฟรม (port 5555)
    สร้าง socket สำหรับส่งท่าทาง (port 5556)
    ตั้งค่า MediaPipe Pose

    // ลูปหลัก
    WHILE True DO
        รับเฟรมจาก Video Sender
        แปลงเฟรมเป็น RGB
        ใช้ MediaPipe ตรวจจับท่าทาง

        IF พบท่าทาง THEN
            // แปลงข้อมูลท่าทาง
            ดึงจุด landmark ทั้ง 33 จุด
            คำนวณขนาดเฟรม
            บันทึก timestamp ปัจจุบัน

            // ส่งข้อมูลท่าทาง
            ส่งข้อมูลผ่าน ZeroMQ (topic "PoseData")
            
            // แสดงผล (ถ้าเปิดไว้)
            IF แสดงวิดีโอ THEN
                วาด landmark บนเฟรม
                แสดงเฟรม
                IF กด 'q' THEN BREAK
        END IF
    END WHILE
END

// [3] โมดูลตรวจจับโซน (Zone Detection) ไฟล์ zone_detection.py
BEGIN
    // ตั้งค่า ZeroMQ และโหลดข้อมูลโซน
    เชื่อมต่อกับ socket เฟรม (port 5555)
    เชื่อมต่อกับ socket ท่าทาง (port 5556)
    สร้าง socket สำหรับส่งโซน (port 5557)
    โหลดข้อมูลโซนจากไฟล์ JSON

    // ลูปหลัก
    WHILE True DO
        // รับข้อมูลแบบ non-blocking
        รับเฟรมจาก Video Sender (ถ้ามี)
        รับท่าทางจาก Pose Detection (ถ้ามี)

        IF ได้รับทั้งเฟรมและท่าทาง THEN
            // คำนวณจุดศูนย์กลางคน
            หาจุดกึ่งกลางจาก landmark

            // ตรวจสอบโซน
            FOR แต่ละโซน DO
                IF จุดศูนย์กลางอยู่ในโซน THEN
                    บันทึกว่าโซนนี้มีคนอยู่
                    วาดจุดบนเฟรม (ถ้าแสดงผล)
                ELSE
                    บันทึกว่าโซนนี้ว่าง
                END IF
            END FOR

            // ส่งสถานะโซน
            ส่งข้อมูลผ่าน ZeroMQ (topic "ZoneDetector")

            // แสดงผล (ถ้าเปิดไว้)
            IF แสดงวิดีโอ THEN
                วาดโซนทั้งหมดบนเฟรม
                แสดงเฟรม
                IF กด 'q' THEN BREAK
        END IF
    END WHILE
END

// [4] โมดูลแสดงผล FPS (FPS Monitor) ไฟล์ check_fpshistogram.py
BEGIN
    // ตั้งค่า ZeroMQ และกราฟ
    เชื่อมต่อกับ socket FPS (port 5558)
    สร้างกราฟ histogram

    // ลูปอัปเดตกราฟ
    FUNCTION อัปเดตกราฟ
        TRY รับค่า FPS จาก Video Sender
        IF ได้รับ THEN
            บันทึกค่า FPS
            อัปเดตกราฟ histogram
            แสดงค่า FPS ใน console
        END IF
    END FUNCTION

    // ตั้งค่า animation
    เรียกฟังก์ชันอัปเดตทุก 1 วินาที
    แสดงกราฟ
END

// [5] โมดูลวิเคราะห์ความล่าช้า (Latency Analyzer) ไฟล์ check_framerateprocess.py
BEGIN
    // ตั้งค่า ZeroMQ และ DataFrame
    เชื่อมต่อกับ socket ท่าทาง (port 5556)
    สร้างตารางเก็บข้อมูล timestamp

    // ลูปหลัก
    WHILE True DO
        รับข้อมูลท่าทางจาก Pose Detection
        แยก timestamp ของเฟรมและท่าทาง
        คำนวณความต่างเวลา
        บันทึกลง DataFrame
        แสดงผลใน console
    END WHILE
END

// [6] โมดูลแสดงผลโซน (Zone Viewer) ไฟล์ check_zonedata.py
BEGIN
    // ตั้งค่า ZeroMQ
    เชื่อมต่อกับ socket โซน (port 5557)

    // ลูปหลัก
    WHILE True DO
        รับข้อมูลโซนจาก Zone Detection
        แสดงสถานะแต่ละโซนใน console
        // ตัวอย่างผลลัพธ์:
        // Zone: Entrance, สถานะ: มีคนอยู่
        // Zone: Exit, สถานะ: ไม่มีคนอยู่
    END WHILE
END

// [7] โมดูลแสดงภาพ (Image Viewer - GUI) ไฟล์ XY_Checker.py
BEGIN
    // ตั้งค่า GUI และ ZeroMQ
    สร้างหน้าต่าง Tkinter
    สร้าง canvas สำหรับแสดงภาพ
    เชื่อมต่อกับ socket เฟรม (port 5555)

    // ฟังก์ชันอัปเดตภาพ
    FUNCTION อัปเดตภาพ
        TRY รับเฟรมจาก Video Sender
        IF ได้รับ THEN
            แปลงเฟรมเป็นรูปแบบแสดงผล
            แสดงภาพบน canvas
        END IF
        เรียกตัวเองอีกครั้งใน 100ms
    END FUNCTION

    // ฟังก์ชันติดตามเมาส์
    FUNCTION ติดตามเมาส์
        แสดงตำแหน่ง X,Y บน GUI
    END FUNCTION

    // เริ่มการทำงาน
    เรียกฟังก์ชันอัปเดตภาพ
    เริ่มลูปหลักของ GUI
END