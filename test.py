import firebase_admin
from firebase_admin import credentials, db
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Firebase
try:
    cred = credentials.Certificate('/home/anirudh/Blood_reaper/blood-reaper-f7580-firebase-adminsdk-dwyff-21dae7f7ea.json')
    firebase_admin.initialize_app(cred, {
        'databaseURL': "https://blood-reaper-f7580-default-rtdb.firebaseio.com"
    })
    logging.info("Firebase initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Firebase: {e}")
    exit(1)

def load_and_print_all_data():
    """
    Load all data from the Firebase Realtime Database and print it.
    """
    try:
        ref = db.reference('/')
        logging.debug("Fetching data from Firebase.")
        data = ref.get()

        if data is None:
            logging.error("Failed to fetch data or no data found in Firebase.")
        else:
            logging.info("Full Firebase data:")
            logging.info(data)
            print("Fetched Data:", data)  # Print the data to verify its structure

        return data
    except Exception as e:
        logging.error(f"Error fetching data from Firebase: {e}")
        return None

# Call the function to load and print all data
load_and_print_all_data()