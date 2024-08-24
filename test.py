import firebase_admin
from firebase_admin import credentials, firestore
import random
from faker import Faker

# Initialize Firebase
cred = credentials.Certificate("/home/anirudh/Blood_reaper/blood-reaper-f7580-firebase-adminsdk-dwyff-21dae7f7ea.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize Faker for generating fake data
fake = Faker()

# Function to generate random GeoPoint coordinates near Kolkata
def random_location():
    base_lat = 22.5726
    base_lon = 88.3639
    lat_variation = random.uniform(-0.1, 0.1)
    lon_variation = random.uniform(-0.1, 0.1)
    return firestore.GeoPoint(base_lat + lat_variation, base_lon + lon_variation)

# Function to generate a random lab entry
def generate_lab_entry():
    return {
        "name": fake.company(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "location": random_location(),
        "blood_inventory": {
            "AB+": str(random.randint(0, 100)),
            "AB-": str(random.randint(0, 100)),
            "A+": str(random.randint(0, 100)),
            "A-": str(random.randint(0, 100)),
            "B+": str(random.randint(0, 100)),
            "B-": str(random.randint(0, 100)),
            "O+": str(random.randint(0, 100)),
            "O-": str(random.randint(0, 100))
        }
    }

# Generate and add multiple lab entries
num_entries = 10  # Number of lab entries to generate
for _ in range(num_entries):
    lab_entry = generate_lab_entry()
    db.collection("labs").add(lab_entry)

print(f"Added {num_entries} lab entries to Firestore.")
