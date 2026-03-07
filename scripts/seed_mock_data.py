import os
import sys
import datetime
import random
import uuid

# Setup Flask/MongoEngine app context
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'webapp')))
from webapp.web import create_app
from webapp import models

app = create_app()

def clear_existing_data():
    print("Clearing old mock event data...")
    models.AnomalyEvent.objects.delete()
    # We might not need to delete ParkingAreas if we just upsert/update them
    print("Old data cleared.")

def generate_mock_data():
    cameras = [
        {"camera_id": "cam_7d375f3d", "name": "12"},
        {"camera_id": "cam_11a5b4ea", "name": "22"},
        {"camera_id": "cam_ed253f4c", "name": "888"},
        {"camera_id": "cam_f3981204", "name": "55"},
        {"camera_id": "cam_a993f371", "name": "6566565"},
        {"camera_id": "cam_3e73c632", "name": "6566565edger"},
        {"camera_id": "cam_675a66b9", "name": "77777777"}
    ]

    now = datetime.datetime.now()
    yesterday = now - datetime.timedelta(days=1)
    
    event_types = ["wrong_parking", "wrong_vehicle_type", "suspicious_activity"]

    with app.app_context():
        # 1. Generate Parking Areas mapping
        print("Generating ParkingAreas...")
        for cam in cameras:
            total_car = random.randint(30, 80)
            avail_car = random.randint(0, total_car)
            occ_car = total_car - avail_car
            
            total_moto = random.randint(20, 50)
            avail_moto = random.randint(0, total_moto)
            occ_moto = total_moto - avail_moto
            
            violation_count = random.randint(0, 5)
            
            models.ParkingArea.objects(camera_id=cam["camera_id"]).update_one(
                set__name=f"Zone {cam['name']}",
                set__description="Mocked generated parking zone",
                set__total_slots=total_car + total_moto,
                
                set__total_car_slots=total_car,
                set__available_car_slots=avail_car,
                set__occupied_car_slots=occ_car,
                
                set__total_motorcycle_slots=total_moto,
                set__available_motorcycle_slots=avail_moto,
                set__occupied_motorcycle_slots=occ_moto,
                
                set__violation_slots=violation_count,
                set__updated_date=now,
                upsert=True
            )

        # 2. Generate Anomaly Events
        print("Generating Anomaly Events...")
        events_to_insert = []
        
        # We generate some events for "yesterday" and "today" for each camera
        for cam in cameras:
            # Generate 3-8 events per camera
            num_events = random.randint(3, 8)
            for _ in range(num_events):
                is_today = random.choice([True, False])
                base_date = now if is_today else yesterday
                
                # Randomize time within the day
                event_time = base_date.replace(
                    hour=random.randint(0, 23),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                
                ev = models.AnomalyEvent(
                    camera_id=cam["camera_id"],
                    timestamp=event_time,
                    event_type=random.choice(event_types),
                    confidence=round(random.uniform(0.65, 0.99), 2),
                    media_snapshot_url="https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&q=80&w=400",
                    is_reviewed=random.choice([True, False])
                )
                events_to_insert.append(ev)
                
        models.AnomalyEvent.objects.insert(events_to_insert)
        print(f"Inserted {len(events_to_insert)} mock anomaly events.")

if __name__ == "__main__":
    reply = input("This will clear out AnomalyEvent collections and repopulate them. Proceed? (y/n): ")
    if reply.lower() == 'y':
        clear_existing_data()
        generate_mock_data()
        print("Done!")
    else:
        print("Aborted.")
