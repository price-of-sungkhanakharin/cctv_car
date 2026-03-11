import requests
import datetime
from urllib.parse import urlparse
from webapp.models.event_model import AnomalyEvent
from webapp.models.parking_model import ParkingArea

def _get_api_url_for_camera(cam):
    if not cam.stream_url:
        return None
    parsed = urlparse(cam.stream_url)
    if not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"

def sync_parking_area_for_camera(cam):
    """Hits the target camera's API to fetch and upsert its ParkingArea."""
    api_url = _get_api_url_for_camera(cam)
    if not api_url:
        return False
        
    try:
        parking_res = requests.get(f"{api_url}/api/parking_areas", timeout=0.5, verify=False)
        if parking_res.status_code == 200:
            parking_data = parking_res.json()
            if isinstance(parking_data, dict):
                parking_data = [parking_data]

            if not parking_data:
                return True
                
            # Sort descending by created_date to ensure we get the absolute newest state
            parking_data.sort(key=lambda x: x.get('created_date', ''), reverse=True)
            p = parking_data[0] # The latest state

            ParkingArea.objects(camera_id=cam.camera_id).update_one(
                set__name=p.get('name') or cam.name or cam.camera_id,
                set__total_slots=int(p.get('total_slots', 0)),
                
                set__total_car_slots=int(p.get('total_car_slots', 0)),
                set__available_car_slots=int(p.get('available_car_slots', 0)),
                set__occupied_car_slots=int(p.get('occupied_car_slots', 0)),
                
                set__total_motorcycle_slots=int(p.get('total_motorcycle_slots', 0)),
                set__available_motorcycle_slots=int(p.get('available_motorcycle_slots', 0)),
                set__occupied_motorcycle_slots=int(p.get('occupied_motorcycle_slots', 0)),
                
                set__violation_slots=int(p.get('violation_slots', 0)),
                set__description=p.get('description', ''),
                set__updated_date=datetime.datetime.now(),
                upsert=True
            )
            return True
        return False
    except Exception:
        return False  # Timeout, network error, or any DB error — silently ignore


def sync_anomaly_events_for_camera(cam):
    """Hits the target camera's API using a timestamp to delta-sync its AnomalyEvents."""
    api_url = _get_api_url_for_camera(cam)
    if not api_url:
        return
        
    try:
        latest_event = AnomalyEvent.objects(camera_id=cam.camera_id).order_by('-timestamp').first()
        
        params = {}
        if latest_event and latest_event.timestamp:
            since_ts = int(latest_event.timestamp.timestamp())
            params['since'] = since_ts
            
        events_res = requests.get(f"{api_url}/api/anomaly_events", params=params, timeout=0.5, verify=False)
        if events_res.status_code == 200:
            events_data = events_res.json()
            
            new_events_count = 0
            for ev in events_data:
                ev_ts_raw = ev.get('timestamp')
                if not ev_ts_raw:
                    continue
                
                # C++ ส่ง timestamp เป็น ISO string เช่น "2026-03-05T05:25:17"
                # ไม่ใช่ Unix epoch ดังนั้นต้องใช้ fromisoformat()
                try:
                    if isinstance(ev_ts_raw, (int, float)):
                        ev_dt = datetime.datetime.fromtimestamp(float(ev_ts_raw))
                    else:
                        ev_dt = datetime.datetime.fromisoformat(str(ev_ts_raw))
                except (ValueError, TypeError):
                    continue
                
                # ต้อง check ด้วย cam.camera_id เสมอ
                # ห้ามใช้ ev.get('camera_id') เพราะ C++ เก็บเป็น "Stream: http://..."
                # ซึ่งไม่ตรงกับที่เรา save (cam_xxx) ทำให้ duplicate check ล้มเหลวทุกครั้ง
                exists = AnomalyEvent.objects(
                    camera_id=cam.camera_id,
                    timestamp=ev_dt
                ).first()
                
                if not exists:
                    new_event = AnomalyEvent(
                        # ใช้ camera_id ของเราเสมอ ไม่ใช่ field camera_id จาก API
                        # เพราะ C++ เก็บเป็น "Stream: http://..." ไม่ใช่ cam_xxx
                        camera_id=cam.camera_id,
                        timestamp=ev_dt,
                        event_type=ev.get('event_type', 'unknown'),
                        confidence=float(ev.get('confidence', 0.0)),
                        media_snapshot_url=ev.get('media_snapshot_url', ''),
                        media_video_url=ev.get('media_video_url', ''),
                        media_seek_time_seconds=int(ev.get('media_seek_time_seconds', 0)),
                        is_reviewed=ev.get('is_reviewed', False)
                    )
                    try:
                        new_event.save()
                        new_events_count += 1
                    except Exception:
                        pass  # Skip if duplicate or DB error

            if new_events_count > 0:
                print(f"[SyncService] Inserted {new_events_count} new anomaly events for {cam.camera_id}.")

    except Exception:
        pass  # Timeout, network error, or any unexpected error
