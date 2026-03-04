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
    # Fetch the 20 most recent anomaly events
    anomaly_logs = models.AnomalyEvent.objects().order_by("-timestamp").limit(20)
            
    return render_template(
        "/index/index.html", 
        assigned_cameras=assigned_cameras,
        unassigned_cameras=unassigned_cameras,
        anomaly_logs=anomaly_logs
    )

@module.route("/anomaly/<event_id>")
@login_required
def anomaly_detail(event_id):
    from flask import abort
    event = models.AnomalyEvent.objects(id=event_id).first()
    if not event:
        abort(404, description="Anomaly event not found")
        
    camera = models.Camera.objects(camera_id=event.camera_id).first()
    
    return render_template(
        "/index/anomaly_detail.html",
        event=event,
        camera=camera
    )

@module.route("/log")
@login_required
def log_view():
    import datetime
    
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
    events = query.order_by("-timestamp")
    
    # Calculate previous and next dates for navigation
    prev_date = (selected_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    next_date = (selected_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    selected_date_display = selected_date.strftime("%B %d, %Y")
    
    return render_template(
        "/index/log.html",
        events=events,
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
