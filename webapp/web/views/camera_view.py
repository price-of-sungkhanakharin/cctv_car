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
    try:
        sync_parking_area_for_camera(cam)
        sync_anomaly_events_for_camera(cam)
    except Exception as e:
        print(f"Warning: Failed to sync camera {camera_id}: {e}")
        
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
    """Display the camera's configuration interface and management options."""
    cam = models.Camera.objects(camera_id=camera_id).first()
    
    if not cam:
        flash("Camera not found.", "error")
        return redirect(url_for("camera.manage"))
        
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

    # Find available dashboard slots (1-20)
    used_slots = set()
    for c in models.Camera.objects():
        if c.dashboard_slot is not None:
            used_slots.add(c.dashboard_slot)
            
    available_slots = [i for i in range(1, 21) if i not in used_slots or i == cam.dashboard_slot]

    return render_template(
        "/camera/setting.html",
        camera=cam,
        target_url=target_url,
        available_slots=available_slots
    )

@module.route("/cameras/manage")
@login_required
def manage():
    """Camera management page. Queries all cameras only when this page is visited."""
    cameras = models.Camera.objects().order_by('name')
    
    # Check which cameras are currently active on grid or map
    assigned_camera_ids = []
    # Currently assigned on dashboard grid
    for cam in models.Camera.objects():
        if getattr(cam, 'dashboard_slot', None):
            assigned_camera_ids.append(cam.camera_id)
            
    # Currently assigned to active parking mapping
    mapped_camera_ids = []
    for pa in models.ParkingArea.objects():
        if pa.camera_id:
            mapped_camera_ids.append(pa.camera_id)
            
    # Find all currently used slots, so manage.html can render the slot picker correctly
    used_slots = set()
    for cam in cameras:
        if cam.dashboard_slot is not None:
            used_slots.add(cam.dashboard_slot)
    # All slots 1-20 are available (the per-camera edit modal will re-include the camera's current slot)
    all_slots = list(range(1, 21))
    # available_slots = slots not taken by any OTHER camera
    # We pass all 1-20, and per-row the button already knows which one is taken by itself
    available_slots = all_slots
            
    return render_template(
        "/camera/manage.html",
        cameras=cameras,
        assigned_camera_ids=assigned_camera_ids,
        mapped_camera_ids=mapped_camera_ids,
        available_slots=available_slots
    )

import uuid
from flask import request, redirect, url_for, flash

@module.route("/cameras/api/add", methods=["POST"])
@login_required
def add_camera():
    name = request.form.get("name", "").strip()
    stream_url = request.form.get("stream_url", "").strip()
    
    if name and stream_url:
        camera_id = f"cam_{uuid.uuid4().hex[:8]}"
        new_cam = models.Camera(
            camera_id=camera_id,
            name=name,
            stream_url=stream_url
        )
        new_cam.save()
        flash(f"Camera '{name}' successfully added.", "success")
    else:
        flash("Name and Stream URL are required.", "error")
        
    return redirect(url_for("camera.manage"))

@module.route("/cameras/api/edit", methods=["POST"])
@login_required
def edit_camera():
    camera_id = request.form.get("camera_id")
    name = request.form.get("name", "").strip()
    return_to = request.form.get("return_to", "manage")  # 'manage' or 'setting'
    
    cam = models.Camera.objects(camera_id=camera_id).first()
    if cam:
        if name:
            cam.name = name
            cam.save()
            flash(f"Camera name updated successfully.", "success")
        else:
            flash("Camera name cannot be empty.", "error")
    else:
        flash("Camera not found.", "error")
        
    if return_to == "setting":
        return redirect(url_for("camera.camera_setting", camera_id=camera_id))
    return redirect(url_for("camera.manage"))

@module.route("/cameras/api/assign_slot", methods=["POST"])
@login_required
def assign_slot():
    camera_id = request.form.get("camera_id")
    slot = request.form.get("dashboard_slot")
    
    cam = models.Camera.objects(camera_id=camera_id).first()
    if cam:
        if slot == "unassign" or not slot:
            cam.dashboard_slot = None
            cam.save()
            flash("Camera unassigned from dashboard.", "success")
        else:
            try:
                slot_int = int(slot)
                # Check if slot is already taken
                existing = models.Camera.objects(dashboard_slot=slot_int).first()
                if existing and existing.camera_id != cam.camera_id:
                    flash(f"Slot {slot_int} is already assigned to another camera.", "error")
                else:
                    cam.dashboard_slot = slot_int
                    cam.save()
                    flash(f"Camera assigned to Slot {slot_int}.", "success")
            except ValueError:
                flash("Invalid slot number.", "error")
            except Exception as e:
                flash(f"Error updating slot: {e}", "error")
    else:
        flash("Camera not found.", "error")
        
    return redirect(url_for("camera.camera_setting", camera_id=camera_id))

@module.route("/cameras/api/delete", methods=["POST"])
@login_required
def delete_camera():
    camera_id = request.form.get("camera_id")
    cam = models.Camera.objects(camera_id=camera_id).first()
    
    if cam:
        # Delete the camera (this also removes its dashboard_slot assignment)
        cam.delete()
        flash("Camera deleted successfully.", "success")
    else:
        flash("Camera not found.", "error")
        
    return redirect(url_for("camera.manage"))
