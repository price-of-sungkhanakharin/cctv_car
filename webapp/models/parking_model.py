import mongoengine as me
import datetime


class ParkingSlot(me.EmbeddedDocument):
    """
    เก็บข้อมูลของแต่ละช่องจอดรถที่วาดจาก Template
    """
    # รหัสช่องจอดตาม Template (เช่น "1", "2", "3") อิงตาม <slot_X_id>
    slot_id = me.StringField(required=True)
    
    # พิกัดแกน x และ y ของกรอบช่องจอด (Polygon) เรียงลำดับตามจุดยอดต่างๆ (<slot_X_points>)
    points_x = me.ListField(me.IntField(), required=True)
    points_y = me.ListField(me.IntField(), required=True)
    
    # สถานะปัจจุบันของช่องจอด: True = ว่าง, False = มีรถจอดอยู่
    is_empty = me.BooleanField(default=True)
    
    # เวลาที่โมเดล AI อัพเดตสถานะ (ว่าง/ไม่ว่าง) ล่าสุด
    last_updated = me.DateTimeField(default=datetime.datetime.now)


class ParkingArea(me.Document):
    """
    เก็บข้อมูลโครงสร้างหรือแบนผังของลานจอดรถแต่ละกล้อง (จาก XML)
    พร้อมด้วยสถานะของช่องจอดแต่ละช่องแบบ Real-time
    """
    # ชื่อแม่แบบ (Template) อิงตาม <name> เช่น "ParkingTemplate_1"
    name = me.StringField(required=True, unique=True)
    
    # รายละเอียดพื้นที่ อิงตาม <description> (เอาไว้แสดงผลบนเว็บ)
    description = me.StringField()
    
    # รหัสกล้องที่จับภาพลานจอดนี้ (สำหรับไว้เชื่อมกับกล้อง - วิ่งไปหา Camera model ดูชื่อหรือ stream_url ต่อได้)
    camera_id = me.StringField(required=True)

    # ขนาดของภาพอ้างอิงตอนวาดกรอบ (<imageWidth> และ <imageHeight>)
    image_width = me.IntField(required=True)
    image_height = me.IntField(required=True)
    
    # จำนวนช่องจอดทั้งหมดในพื้นที่นี้ อิงตาม <slotCount>
    slot_count = me.IntField(required=True, min_value=0)
    
    # รายการช่องจอดทั้งหมดที่อยู่ในพื้นที่อ้างอิงนี้
    slots = me.EmbeddedDocumentListField(ParkingSlot)

    meta = {
        "collection": "parking_areas",
        "indexes": [
            "name",
            "camera_id" # เผื่อค้นหาว่ากล้อง ID นี้ใช้ Template ไหนอยู่
        ]
    }
