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

@module.route("/camera/setting/<camera_id>")
@login_required
def camera_setting(camera_id):
    """Display the camera's configuration interface embedded in an iframe"""
    cam = models.Camera.objects(camera_id=camera_id).first()
    
    if not cam:
        abort(404, description="Camera not found")
        
    # We use a mock URL if we just want to test iframe embedding without an actual IP.
    # We will use the IP address if it looks like a valid URL or just mock it.
    target_url = ""
    if cam.ip_address:
        if cam.ip_address.startswith("http"):
            target_url = cam.ip_address
        else:
            target_url = f"http://{cam.ip_address}"
    else:
        target_url = "https://example.com"

    return render_template(
        "/camera/setting.html",
        camera=cam,
        target_url=target_url
    )
