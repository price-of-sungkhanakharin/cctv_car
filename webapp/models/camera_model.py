import mongoengine as me
import datetime


class Camera(me.Document):
    """
    เก็บข้อมูลของกล้องแต่ละตัว เพื่อเป็นตัวกลาง (Single Source of Truth)
    ให้โมเดลอื่น (เช่น ParkingArea หรือ AnomalyEvent) นำ camera_id ไปอ้างอิง
    """
    # รหัสกล้อง (เช่น "cam_01")
    camera_id = me.StringField(required=True, unique=True)
    
    # ชื่อสำหรับแสดงผลให้ผู้ใช้เข้าใจง่าย (เช่น "กล้องทางเข้าหลัก", "กล้องลานจอดโซน A")
    name = me.StringField(required=True)
    
    # IP Address ของกล้อง
    ip_address = me.StringField()
    
    # URL สำหรับดึงสตรีมวิดีโอสด (เช่น "rtsp://192.168.1.100:554/stream1")
    stream_url = me.StringField()
    
    # สถานะปัจจุบันของกล้อง ("online", "offline", "maintenance")
    status = me.StringField(
        required=True, 
        default="online", 
        choices=["online", "offline", "maintenance"]
    )
    
    # พิกัด GPS (ละติจูด, ลองจิจูด) ตำแหน่งติดตั้งกล้อง เพื่อนำไปปักบนแผนที่
    latitude = me.FloatField()
    longitude = me.FloatField()
    
    # บันทึกเวลาที่เปลี่ยนแปลงข้อมูลล่าสุด
    created_date = me.DateTimeField(required=True, default=datetime.datetime.now)
    updated_date = me.DateTimeField(required=True, default=datetime.datetime.now)

    meta = {
        "collection": "cameras",
        "indexes": ["camera_id", "status"]
    }
