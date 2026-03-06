from flask import Blueprint, render_template, abort
from flask_login import login_required
from .. import models

module = Blueprint("camera", __name__)


@module.route("/camera/<camera_id>")
@login_required
def live_feed(camera_id):
    """Display a dedicated live feed page for a specific camera"""
    from webapp.services.sync_service import sync_parking_area_for_camera, sync_anomaly_events_for_camera
    
    cam = models.Camera.objects(camera_id=camera_id).first()
    
    if not cam:
        abort(404, description="Camera not found")
        
    # Trigger on-demand sync for this specific camera
    sync_parking_area_for_camera(cam)
    sync_anomaly_events_for_camera(cam)
        
    # Attempt to fetch associated parking area for stats
    parking_area = models.ParkingArea.objects(camera_id=camera_id).first()
    
    capacity_percent = 0
    if parking_area and parking_area.total_slots > 0:
        total_occ = parking_area.occupied_car_slots + parking_area.occupied_motorcycle_slots
        capacity_percent = int((total_occ / parking_area.total_slots) * 100)
        
    # Fetch recent anomalies related to this camera
    raw_events = models.AnomalyEvent.objects(camera_id=camera_id).order_by('-timestamp').limit(10)
    
    # แปลง Windows path → HTTP URL
    from urllib.parse import urlparse
    base_url = ""
    if cam and cam.stream_url:
        parsed = urlparse(cam.stream_url)
        if parsed.netloc:
            base_url = f"{parsed.scheme}://{parsed.netloc}"

    def _win_path_to_url(win_path):
        if not win_path:
            return ""
        if win_path.startswith("http://") or win_path.startswith("https://"):
            return win_path
        if not base_url:
            return ""
        norm = win_path.replace("\\", "/")
        if len(norm) > 2 and norm[1] == ":":
            norm = norm[2:].lstrip("/")
        if norm.lower().startswith("locvideo/"):
            return f"{base_url}/{norm}"
        if norm.lower().startswith("smart_parking_violations/"):
            rest = norm[len("smart_parking_violations/"):]
            return f"{base_url}/violations/{rest}"
        return f"{base_url}/{norm}"

    anomaly_events = []
    for ev in raw_events:
        anomaly_events.append({
            "id": str(ev.id),
            "camera_id": ev.camera_id,
            "timestamp": ev.timestamp,
            "event_type": ev.event_type,
            "confidence": ev.confidence,
            "is_reviewed": ev.is_reviewed,
            "media_seek_time_seconds": ev.media_seek_time_seconds,
            "media_snapshot_url": _win_path_to_url(ev.media_snapshot_url),
            "media_video_url": _win_path_to_url(ev.media_video_url),
        })

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
        
    # We use stream_url to find the device's web interface (e.g. removing /video)
    target_url = ""
    if cam.stream_url:
        from urllib.parse import urlparse
        parsed = urlparse(cam.stream_url)
        target_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else cam.stream_url
        
        # Fallback if stream URL did not have a scheme (e.g., just an IP was entered)
        if not target_url.startswith("http"):
            target_url = f"http://{target_url}"
    elif cam.ip_address:
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
