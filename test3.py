import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random

# Initialize Firebase app
cred = credentials.Certificate('/home/anirudh/Blood_reaper/blood-reaper-f7580-firebase-adminsdk-dwyff-21dae7f7ea.json')
firebase_admin.initialize_app(cred)

# Get Firestore database instance
db = firestore.client()

# Reference to the hospital
hospital_ref = db.collection('hospitals').document('5OqTT5Jzr8q1krmJVEzJ')

# Function to generate random blood demands
def generate_random_demand():
    blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    demand = {bt: random.randint(5, 30) for bt in random.sample(blood_types, k=random.randint(2, 4))}
    return demand

# Function to create a new requirement document
def create_requirement():
    demand = generate_random_demand()
    now = datetime.now()
    post_date = now.isoformat()
    last_date = (now + timedelta(days=random.randint(3, 7))).isoformat()

    requirement_data = {
        'demand': demand,
        'hospital': hospital_ref,
        'lastDate': last_date,
        'postDate': post_date,
        'respondants': []
    }

    # Add to Firestore
    db.collection('requirements').add(requirement_data)

# Generate and add 3 new requirements
for _ in range(3):
    create_requirement()

print("New requirements generated successfully.")
