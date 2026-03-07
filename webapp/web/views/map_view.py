from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from .. import models
from urllib.parse import urlparse

module = Blueprint("map", __name__)


@module.route("/map")
@login_required
def map_view():
    """Load map immediately with current MongoDB data. No blocking sync."""
    cameras = models.Camera.objects(latitude__ne=None, longitude__ne=None).order_by("name")
    parking_areas = models.ParkingArea.objects()
    parking_area_map = {pa.camera_id: pa for pa in parking_areas}

    markers = []
    for cam in cameras:
        pa = parking_area_map.get(cam.camera_id)
        # Build base_url for this camera so JS can poll it directly
        base_url = ""
        if cam.stream_url:
            parsed = urlparse(cam.stream_url)
            if parsed.netloc:
                base_url = f"{parsed.scheme}://{parsed.netloc}"

        markers.append({
            "camera_id": cam.camera_id,
            "name": cam.name,
            "ip_address": cam.ip_address or "Unknown",
            "lat": cam.latitude,
            "lng": cam.longitude,
            "status": cam.status,
            "base_url": base_url,
            "stream_url": cam.stream_url,
            # Use DB data as initial values — JS will update these later
            "total_slots": pa.total_slots if pa else None,
            "total_car_slots": pa.total_car_slots if pa else None,
            "available_car_slots": pa.available_car_slots if pa else None,
            "occupied_car_slots": pa.occupied_car_slots if pa else None,
            "total_motorcycle_slots": pa.total_motorcycle_slots if pa else None,
            "available_motorcycle_slots": pa.available_motorcycle_slots if pa else None,
            "occupied_motorcycle_slots": pa.occupied_motorcycle_slots if pa else None,
            "violation_slots": pa.violation_slots if pa else None,
            "capacityPercent": int(((pa.occupied_car_slots + pa.occupied_motorcycle_slots) / pa.total_slots * 100)) if pa and pa.total_slots > 0 else 0
        })

    return render_template("/map/map.html", parking_lots=markers)


@module.route("/api/map/sync_camera/<camera_id>")
@login_required
def sync_camera_api(camera_id):
    """
    ดึงข้อมูลสดจากกล้องเฉพาะตัว แล้วอัปเดต MongoDB และคืน JSON กลับมา
    JS จะเรียก endpoint นี้ per-camera หลัง map โหลดแล้ว (async, max 5s)
    """
    cam = models.Camera.objects(camera_id=camera_id).first()
    if not cam:
        return jsonify({"error": "Camera not found"}), 404

    from webapp.services.sync_service import sync_parking_area_for_camera
    is_data_online = sync_parking_area_for_camera(cam)

    # Bypass browser SSL restrictions by checking the stream directly in Python
    stream_online = False
    if cam.stream_url:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            # We ONLY want to ping it, grab headers, and close immediately to save bandwidth
            res = requests.get(cam.stream_url, stream=True, verify=False, timeout=2.0)
            if res.status_code == 200:
                stream_online = True
            res.close()
        except Exception:
            pass
            
    is_online = is_data_online or stream_online

    # Return latest DB state after sync
    pa = models.ParkingArea.objects(camera_id=camera_id).first()
    if pa:
        total_occ = pa.occupied_car_slots + pa.occupied_motorcycle_slots
        capacity_pct = int((total_occ / pa.total_slots * 100)) if pa.total_slots > 0 else 0
        return jsonify({
            "camera_id": camera_id,
            "online": is_online,
            "total_slots": pa.total_slots,
            "total_car_slots": pa.total_car_slots,
            "available_car_slots": pa.available_car_slots,
            "occupied_car_slots": pa.occupied_car_slots,
            "total_motorcycle_slots": pa.total_motorcycle_slots,
            "available_motorcycle_slots": pa.available_motorcycle_slots,
            "occupied_motorcycle_slots": pa.occupied_motorcycle_slots,
            "violation_slots": pa.violation_slots,
            "capacityPercent": capacity_pct,
        })
    else:
        return jsonify({
            "camera_id": camera_id,
            "online": False,
            "total_slots": None,
            "total_car_slots": None,
            "available_car_slots": None,
            "occupied_car_slots": None,
            "total_motorcycle_slots": None,
            "available_motorcycle_slots": None,
            "occupied_motorcycle_slots": None,
            "violation_slots": None,
            "capacityPercent": 0,
        })
