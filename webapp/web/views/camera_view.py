from flask import Blueprint, render_template, abort
from flask_login import login_required
from .. import models

module = Blueprint("camera", __name__)


@module.route("/camera/<camera_id>")
@login_required
def live_feed(camera_id):
    """Display a dedicated live feed page for a specific camera"""
    cam = models.Camera.objects(camera_id=camera_id).first()
    
    if not cam:
        abort(404, description="Camera not found")
        
    # Attempt to fetch associated parking area for stats
    parking_area = models.ParkingArea.objects(camera_id=camera_id).first()
    
    capacity_percent = 0
    if parking_area and parking_area.total_slots > 0:
        capacity_percent = int((parking_area.occupied_slots / parking_area.total_slots) * 100)
        
    # Fetch recent anomalies related to this camera
    anomaly_events = models.AnomalyEvent.objects(camera_id=camera_id).order_by('-timestamp').limit(10)
    
    return render_template(
        "/camera/live.html", 
        camera=cam, 
        parking_area=parking_area,
        capacity_percent=capacity_percent,
        anomaly_events=anomaly_events
    )
