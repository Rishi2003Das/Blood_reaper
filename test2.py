import firebase_admin
from firebase_admin import credentials, firestore

# Path to your service account key file
cred = credentials.Certificate("/home/anirudh/Blood_reaper/blood-reaper-f7580-firebase-adminsdk-dwyff-21dae7f7ea.json")

# Initialize the Firebase app with the service account
firebase_admin.initialize_app(cred)

# Initialize Firestore client
db = firestore.client()

# Specify the collection you want to retrieve data from
collection_name = 'hospitals'

# Sample data to add, including a GeoPoint location
sample_hospital_data = {
    'name': 'City Hospital',
    'location': firestore.GeoPoint(12.9715987, 77.594566),  # Replace with your latitude and longitude
    'blood_inventory': {'A+': 10, 'O-': 5},
    'type': 'hospital',
    'watchers': ['user1', 'user2'],
    'phone': '+1234567890',
    'email': 'cityhospital@example.com'
}

# Add the sample data to the collection
db.collection(collection_name).add(sample_hospital_data)

# Get all documents in the collection
docs = db.collection(collection_name).stream()

# Print all documents and their fields
for doc in docs:
    print(f'Document ID: {doc.id} => Data: {doc.to_dict()}')

    # Example: Printing individual fields, including the GeoPoint
    data = doc.to_dict()
    print(f"Name: {data.get('name')}")
    location = data.get('location')
    if isinstance(location, firestore.GeoPoint):
        print(f"Location: Lat: {location.latitude}, Lng: {location.longitude}")
    print(f"Blood Inventory: {data.get('blood_inventory')}")
    print(f"Type: {data.get('type')}")
    print(f"Watchers: {data.get('watchers')}")
    print(f"Phone: {data.get('phone')}")
    print(f"Email: {data.get('email')}")
    print("-------------------------")
