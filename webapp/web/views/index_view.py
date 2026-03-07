from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
import uuid
from .. import models
import mongoengine as me

module = Blueprint("index", __name__)


@module.route("/")
@login_required
def index():
    cameras = models.Camera.objects().order_by("name")
    
    assigned_cameras = {}
    unassigned_cameras = []
    
    for cam in cameras:
        if cam.dashboard_slot:
            assigned_cameras[cam.dashboard_slot] = cam
        else:
            unassigned_cameras.append(cam)
            
    parking_areas = models.ParkingArea.objects()
    parking_dict = {pa.camera_id: pa for pa in parking_areas}

    # Fetch the 20 most recent anomaly events for initial render
    anomaly_logs = models.AnomalyEvent.objects().order_by("-timestamp").limit(20)
            
    return render_template(
        "/index/index.html", 
        assigned_cameras=assigned_cameras,
        unassigned_cameras=unassigned_cameras,
        anomaly_logs=anomaly_logs,
        parking_dict=parking_dict
    )

@module.route("/api/components/dashboard_logs")
@login_required
def api_dashboard_logs():
    """HTMX endpoint to poll the latest 20 anomaly logs for the dashboard footer"""
    anomaly_logs = models.AnomalyEvent.objects().order_by("-timestamp").limit(20)
    return render_template(
        "/components/dashboard_logs.html", 
        anomaly_logs=anomaly_logs
    )

@module.route("/anomaly/<event_id>")
@login_required
def anomaly_detail(event_id):
    from flask import abort
    from urllib.parse import urlparse

    event = models.AnomalyEvent.objects(id=event_id).first()
    if not event:
        abort(404, description="Anomaly event not found")

    camera = models.Camera.objects(camera_id=event.camera_id).first()

    # แปลง Windows path → HTTP URL (เหมือนที่ log_view ทำ)
    base_url = ""
    if camera and camera.stream_url:
        parsed = urlparse(camera.stream_url)
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

    event_data = {
        "id": str(event.id),
        "camera_id": event.camera_id,
        "timestamp": event.timestamp,
        "event_type": event.event_type,
        "confidence": event.confidence,
        "is_reviewed": event.is_reviewed,
        "media_seek_time_seconds": event.media_seek_time_seconds,
        "media_snapshot_url": _win_path_to_url(event.media_snapshot_url),
        "media_video_url": _win_path_to_url(event.media_video_url),
    }

    return render_template(
        "/index/anomaly_detail.html",
        event=event_data,
        camera=camera
    )

@module.route("/api/anomaly/<event_id>/toggle_review", methods=["POST"])
@login_required
def toggle_anomaly_review(event_id):
    event = models.AnomalyEvent.objects(id=event_id).first()
    if not event:
        return "Anomaly event not found", 404
        
    event.is_reviewed = not event.is_reviewed
    event.save()
    
    checked_attr = "checked" if event.is_reviewed else ""
    post_url = url_for('index.toggle_anomaly_review', event_id=event.id)
    
    return f'<input {checked_attr} class="h-4 w-4 rounded border-white/20 bg-black/50 text-primary focus:ring-primary focus:ring-offset-0 focus:ring-offset-[#1e2329]" type="checkbox" onclick="event.stopPropagation();" hx-post="{post_url}" hx-swap="outerHTML" />'

@module.route("/log")
@login_required
def log_view():
    import datetime
    from webapp.services.sync_service import sync_anomaly_events_for_camera
    
    # Sync all anomalies for all cameras on demand before fetching
    for cam in models.Camera.objects():
        sync_anomaly_events_for_camera(cam)
    
    # Get parameters
    date_str = request.args.get("date", "")
    search_query = request.args.get("q", "").strip()
    
    # Try parsing date, default to today
    try:
        if date_str:
            selected_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            selected_date = datetime.date.today()
    except ValueError:
        selected_date = datetime.date.today()
        
    start_of_day = datetime.datetime.combine(selected_date, datetime.time.min)
    end_of_day = datetime.datetime.combine(selected_date, datetime.time.max)
    
    # Base query for the selected day
    query = models.AnomalyEvent.objects(
        timestamp__gte=start_of_day,
        timestamp__lte=end_of_day
    )
    
    # Fetch all parking areas to map camera_id to location name
    parking_areas = models.ParkingArea.objects()
    camera_names = {p.camera_id: p.name for p in parking_areas}
    
    # Apply search filter if present
    if search_query:
        # Check if the search matches a location name
        matching_cameras = [
            cam_id for cam_id, name in camera_names.items()
            if search_query.lower() in name.lower()
        ]
        
        # Search camera_id, event_type, or matched location names
        query = query.filter(
            me.Q(camera_id__icontains=search_query) | 
            me.Q(event_type__icontains=search_query) |
            me.Q(camera_id__in=matching_cameras)
        )
        
    # Order by newest first
    events = list(query.order_by("-timestamp"))
    
    # แปลง Windows local path → HTTP URL
    # C++ server เก็บเป็น path เช่น "C:/locvideo/20260305/052511.webm"
    # แต่เราต้องโหลดผ่าน HTTP endpoint ของกล้องแต่ละตัวแทน
    from urllib.parse import urlparse
    
    # สร้าง map camera_id → base_url ของกล้อง
    cameras_all = models.Camera.objects()
    camera_base_urls = {}
    for cam in cameras_all:
        if cam.stream_url:
            parsed = urlparse(cam.stream_url)
            if parsed.netloc:
                camera_base_urls[cam.camera_id] = f"{parsed.scheme}://{parsed.netloc}"
    
    def _win_path_to_url(win_path: str, base_url: str) -> str:
        """แปลง Windows path เป็น HTTP URL
        C:/locvideo/20260305/file.webm   → base_url/locvideo/20260305/file.webm
        C:/smart_parking_violations/...  → base_url/violations/...
        ถ้าเป็น HTTP URL อยู่แล้วให้คืนเหมือนเดิม
        """
        if not win_path:
            return ""
        if win_path.startswith("http://") or win_path.startswith("https://"):
            return win_path
        # Normalize backslash to forward slash
        norm = win_path.replace("\\", "/")
        # Strip drive letter e.g. "C:/"
        if len(norm) > 2 and norm[1] == ":":
            norm = norm[2:].lstrip("/")
        # Map folder prefixes
        if norm.lower().startswith("locvideo/"):
            return f"{base_url}/{norm}"
        if norm.lower().startswith("smart_parking_violations/"):
            rest = norm[len("smart_parking_violations/"):]
            return f"{base_url}/violations/{rest}"
        # Fallback: ต่อท้าย base URL เลย
        return f"{base_url}/{norm}"
    
    # แปลง URL ใน event แต่ละตัว — สร้าง dict แทน object เพื่อไม่ให้แก้ DB
    enriched_events = []
    for ev in events:
        base_url = camera_base_urls.get(ev.camera_id, "")
        enriched_events.append({
            "id": str(ev.id),
            "camera_id": ev.camera_id,
            "timestamp": ev.timestamp,
            "event_type": ev.event_type,
            "confidence": ev.confidence,
            "is_reviewed": ev.is_reviewed,
            "media_seek_time_seconds": ev.media_seek_time_seconds,
            "media_snapshot_url": _win_path_to_url(ev.media_snapshot_url, base_url) if base_url else ev.media_snapshot_url,
            "media_video_url": _win_path_to_url(ev.media_video_url, base_url) if base_url else ev.media_video_url,
        })
    
    # Calculate previous and next dates for navigation
    prev_date = (selected_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    next_date = (selected_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    selected_date_display = selected_date.strftime("%B %d, %Y")
    
    return render_template(
        "/index/log.html",
        events=enriched_events,
        selected_date=selected_date_str,
        selected_date_display=selected_date_display,
        prev_date=prev_date,
        next_date=next_date,
        search_query=search_query,
        camera_names=camera_names
    )


@module.route("/api/cameras/assign", methods=["POST"])
@login_required
def assign_camera():
    data = request.json
    slot_id = data.get("slot_id")
    
    if not slot_id:
        return jsonify({"error": "slot_id is required"}), 400
        
    try:
        slot_id = int(slot_id)
    except ValueError:
        return jsonify({"error": "slot_id must be an integer"}), 400
    
    # First, if any camera already occupies this slot, unset it
    existing_in_slot = models.Camera.objects(dashboard_slot=slot_id).first()
    if existing_in_slot:
        existing_in_slot.dashboard_slot = None
        existing_in_slot.save()
        
    camera_id = data.get("camera_id")
    
    if camera_id:
        # User selected an existing camera
        cam = models.Camera.objects(camera_id=camera_id).first()
        if not cam:
            return jsonify({"error": "Camera not found"}), 404
        
        cam.dashboard_slot = slot_id
        cam.save()
        return jsonify({
            "success": True, 
            "message": "Camera assigned", 
            "camera": {"name": cam.name, "stream_url": cam.stream_url}
        })
    else:
        # Creating a new camera
        name = data.get("name")
        stream_url = data.get("stream_url")
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        
        if not name or not stream_url:
            return jsonify({"error": "name and stream_url are required for new cameras"}), 400
            
        new_cam_id = f"cam_{uuid.uuid4().hex[:8]}"
        cam = models.Camera(
            camera_id=new_cam_id,
            name=name,
            stream_url=stream_url,
            latitude=latitude,
            longitude=longitude,
            dashboard_slot=slot_id
        )
        cam.save()
        return jsonify({
            "success": True, 
            "message": "New camera created and assigned", 
            "camera": {"name": cam.name, "stream_url": cam.stream_url}
        })


@module.route("/api/cameras/assign/<int:slot_id>", methods=["DELETE"])
@login_required
def remove_camera(slot_id):
    cam = models.Camera.objects(dashboard_slot=slot_id).first()
    if cam:
        cam.dashboard_slot = None
        cam.save()
        return jsonify({"success": True, "message": "Camera removed from slot"})
    return jsonify({"success": True, "message": "No camera in this slot"})
