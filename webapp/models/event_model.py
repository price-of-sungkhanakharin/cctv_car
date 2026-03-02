import mongoengine as me
import datetime


class AnomalyEvent(me.Document):
    # รหัสกล้องที่จับภาพได้ (สามารถไป join กับ Camera model ดึงชื่อกล้องหรือสตรีมวิดีโอสดต่อได้)
    camera_id = me.StringField(required=True)
    
    # เก็บเป็น Date Object เสมอ (อย่าเก็บเป็น String) เพราะจะทำให้ค้นหาช่วงเวลา (เช่น ดึงข้อมูลของเมื่อวาน) และทำระบบลบอัตโนมัติ (TTL) ได้ง่าย
    timestamp = me.DateTimeField(required=True, default=datetime.datetime.now)
    
    # ประเภทของความผิดปกติที่ AI ตรวจเจอ เช่น "person_detected", "fire", "weapon"
    event_type = me.StringField(required=True)
    
    # ความมั่นใจของโมเดล (0.0 - 1.0) เอาไว้ทำฟิลเตอร์บนเว็บ เช่น "แสดงเฉพาะที่มั่นใจเกิน 80%"
    confidence = me.FloatField(required=True, min_value=0.0, max_value=1.0)
    
    # ลิงก์รูปภาพช็อตแรกที่เกิดเหตุ เว็บสามารถเอา URL นี้ไปใส่แท็ก <img src="..."> ได้เลย
    media_snapshot_url = me.StringField(required=True)
    
    # ลิงก์ไฟล์วิดีโอก้อนนั้น
    media_video_url = me.StringField(required=True)
    
    # ทริคสำคัญ: เก็บวินาทีที่เกิดเหตุการณ์ในคลิป เพื่อใช้ javascript DOM `videoElement.currentTime` กระโดดไปดูช็อตนั้นทันที
    media_seek_time_seconds = me.IntField(required=True, min_value=0)
    
    # (ออปชันเสริม) เอาไว้ให้แอดมินกดเครื่องหมายติ๊กถูกในเว็บว่า "ตรวจสอบเคสนี้แล้ว"
    is_reviewed = me.BooleanField(default=False)

    meta = {
        "collection": "anomaly_events",
        "indexes": [
            "camera_id",
            "-timestamp",   # index แบบ descending เพื่อดึงข้อมูลล่าสุดได้เร็ว และรองรับค้นหาตามช่วงเวลา
            "event_type",
            "is_reviewed",
            {"fields": ["timestamp"], "expireAfterSeconds": 2592000} # ตัวอย่าง: ลบอัตโนมัติเมื่อครบ 30 วัน (optional TTL index)
        ]
    }
