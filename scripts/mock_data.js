use cctv_car_kim; // เปลี่ยนเป็นชื่อ Database ใน MongoDB คุุณนะครับ

// --- 1. สุ่มข้อมูลลานจอดรถ (Parking Areas) ---
db.parking_areas.deleteMany({}); // ล้างข้อมูลเก่า
db.parking_areas.insertMany([
    {
        "camera_id": "cam_7d375f3d", "name": "Zone 12", "description": "Mocked generated parking zone",
        "total_slots": 100, "total_car_slots": 70, "available_car_slots": 15, "occupied_car_slots": 55,
        "total_motorcycle_slots": 30, "available_motorcycle_slots": 5, "occupied_motorcycle_slots": 25,
        "violation_slots": 3, "created_date": new Date(), "updated_date": new Date()
    },
    {
        "camera_id": "cam_11a5b4ea", "name": "Zone 22", "description": "Mocked generated parking zone",
        "total_slots": 80, "total_car_slots": 50, "available_car_slots": 40, "occupied_car_slots": 10,
        "total_motorcycle_slots": 30, "available_motorcycle_slots": 20, "occupied_motorcycle_slots": 10,
        "violation_slots": 1, "created_date": new Date(), "updated_date": new Date()
    },
    {
        "camera_id": "cam_ed253f4c", "name": "Zone 888", "description": "Mocked generated parking zone",
        "total_slots": 150, "total_car_slots": 100, "available_car_slots": 5, "occupied_car_slots": 95, // ใกล้เต็ม
        "total_motorcycle_slots": 50, "available_motorcycle_slots": 2, "occupied_motorcycle_slots": 48,
        "violation_slots": 8, "created_date": new Date(), "updated_date": new Date()
    },
    {
        "camera_id": "cam_f3981204", "name": "Zone 55", "description": "Mocked generated parking zone",
        "total_slots": 50, "total_car_slots": 30, "available_car_slots": 30, "occupied_car_slots": 0,    // ว่างจัด
        "total_motorcycle_slots": 20, "available_motorcycle_slots": 20, "occupied_motorcycle_slots": 0,
        "violation_slots": 0, "created_date": new Date(), "updated_date": new Date()
    },
    {
        "camera_id": "cam_a993f371", "name": "Zone 6566565", "description": "Mocked generated parking zone",
        "total_slots": 120, "total_car_slots": 80, "available_car_slots": 50, "occupied_car_slots": 30,
        "total_motorcycle_slots": 40, "available_motorcycle_slots": 20, "occupied_motorcycle_slots": 20,
        "violation_slots": 2, "created_date": new Date(), "updated_date": new Date()
    },
    {
        "camera_id": "cam_3e73c632", "name": "Zone 6566565edger", "description": "Mocked generated parking zone",
        "total_slots": 90, "total_car_slots": 60, "available_car_slots": 0, "occupied_car_slots": 60,   // เต็ม 100%
        "total_motorcycle_slots": 30, "available_motorcycle_slots": 0, "occupied_motorcycle_slots": 30,
        "violation_slots": 5, "created_date": new Date(), "updated_date": new Date()
    },
    {
        "camera_id": "cam_675a66b9", "name": "Zone 77777777", "description": "Mocked generated parking zone",
        "total_slots": 200, "total_car_slots": 150, "available_car_slots": 100, "occupied_car_slots": 50,
        "total_motorcycle_slots": 50, "available_motorcycle_slots": 40, "occupied_motorcycle_slots": 10,
        "violation_slots": 0, "created_date": new Date(), "updated_date": new Date()
    }
]);


// --- 2. สุ่มข้อมูลประวัติรถผิดกฎ (Anomaly Events) ---
db.anomaly_events.deleteMany({}); // ล้างข้อมูลเก่า
let yesterday = new Date(); yesterday.setDate(yesterday.getDate() - 1);
let today = new Date();

let cameras = ["cam_7d375f3d", "cam_11a5b4ea", "cam_ed253f4c", "cam_f3981204", "cam_a993f371", "cam_3e73c632", "cam_675a66b9"];
let types = ["wrong_parking", "wrong_vehicle_type", "suspicious_activity"];
let mock_events = [];

cameras.forEach(cam => {
    // สุ่มเพิ่มประมาณกล้องละ 3-5 รายการ (รวมของวันนี้และเมื่อวาน)
    for (let i = 0; i < 4; i++) {
        let isToday = Math.random() > 0.5;
        let eventDate = isToday ? new Date() : new Date(yesterday);
        eventDate.setHours(Math.floor(Math.random() * 24), Math.floor(Math.random() * 60)); // สุ่มเวลา

        mock_events.push({
            "camera_id": cam,
            "timestamp": eventDate,
            "event_type": types[Math.floor(Math.random() * types.length)],
            "confidence": Math.random() * (0.99 - 0.70) + 0.70, // มั่นใจ 70-99%
            "media_snapshot_url": "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&q=80&w=400",
            "media_video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
            "media_seek_time_seconds": 0,
            "is_reviewed": Math.random() > 0.5
        });
    }
});

db.anomaly_events.insertMany(mock_events);
print("Mock Data Inserted Successfully!");
