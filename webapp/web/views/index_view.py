from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
import uuid
from .. import models

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
            
    return render_template(
        "/index/index.html", 
        assigned_cameras=assigned_cameras,
        unassigned_cameras=unassigned_cameras
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
