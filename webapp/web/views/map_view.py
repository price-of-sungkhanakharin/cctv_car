from flask import Blueprint, render_template
from flask_login import login_required
from .. import models

module = Blueprint("map", __name__)


@module.route("/map")
@login_required
def map_view():
    """Display the university parking map with real camera locations"""
    # Fetch all cameras that have GPS coordinates
    cameras = models.Camera.objects(latitude__ne=None, longitude__ne=None).order_by("name")
    
    # Also fetch parking areas to possibly link info (like slots)
    parking_areas = models.ParkingArea.objects()
    parking_area_map = {pa.camera_id: pa for pa in parking_areas}
    
    # Prepare markers data
    markers = []
    for cam in cameras:
        pa = parking_area_map.get(cam.camera_id)
        markers.append({
            "name": cam.name,
            "ip_address": cam.ip_address or "Unknown",
            "lat": cam.latitude,
            "lng": cam.longitude,
            "status": cam.status,
            "total_slots": pa.total_slots if pa else None,
            "available_slots": pa.available_slots if pa else None,
            "capacityPercent": int((pa.occupied_slots / pa.total_slots * 100)) if pa and pa.total_slots > 0 else 0
        })
        
    return render_template("/map/map.html", parking_lots=markers)
