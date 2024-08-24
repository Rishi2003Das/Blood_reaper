import firebase_admin
from firebase_admin import credentials, firestore
import math
import networkx as nx
import matplotlib.pyplot as plt

# Initialize Firebase Admin SDK
cred = credentials.Certificate("/home/anirudh/Blood_reaper/blood-reaper-f7580-firebase-adminsdk-dwyff-21dae7f7ea.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Retrieve all hospitals and labs
hospitals = db.collection('hospitals').stream()
labs = db.collection('labs').stream()

# Convert Firestore documents to a list of dictionaries
hospital_nodes = [{**doc.to_dict(), 'id': doc.id} for doc in hospitals]
lab_nodes = [{**doc.to_dict(), 'id': doc.id} for doc in labs]

# Retrieve the requirements
requirements_doc = db.collection('requirements').document('wScZkEs2egfo4bVwu5wP').get()
requirements_data = requirements_doc.to_dict()
required_hospital_ref = requirements_data.get('hospital')
required_hospital_id = required_hospital_ref.id if required_hospital_ref else None
required_blood_types = requirements_data.get('demand', {})

# Define universal blood types
universal_donors = {'O-'}  # Universal donors
universal_acceptors = {'AB+'}  # Universal acceptors

# Function to calculate the distance between two locations (lat-long) using the Haversine formula
def calculate_distance(loc1, loc2):
    R = 6371e3  # Earth radius in meters
    phi1 = math.radians(loc1.latitude)
    phi2 = math.radians(loc2.latitude)
    delta_phi = math.radians(loc2.latitude - loc1.latitude)
    delta_lambda = math.radians(loc2.longitude - loc1.longitude)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # Distance in meters

# Build a graph where each node is connected to every other node with an edge representing distance
graph = {}
nodes = hospital_nodes + lab_nodes

for node in nodes:
    node_id = node['id']
    node_location = node['location']
    graph[node_id] = {}

    for other_node in nodes:
        if node_id != other_node['id']:
            distance = calculate_distance(node_location, other_node['location'])
            graph[node_id][other_node['id']] = distance

# Find the nearest lab to the specified hospital with valid blood inventory
def find_nearest_lab(hospital_id, labs, required_blood_types):
    if hospital_id not in graph:
        raise ValueError(f"Hospital with ID {hospital_id} not found in graph.")

    nearest_lab = None
    min_distance = float('inf')

    for lab in labs:
        lab_id = lab['id']
        lab_inventory = lab.get('blood_inventory', {})

        # Check if the lab has valid blood types required
        has_valid_inventory = False
        for blood_type in required_blood_types:
            if blood_type in universal_donors or blood_type in universal_acceptors:
                has_valid_inventory = True
                break

            # Convert inventory value to integer if it is not already
            inventory_value = lab_inventory.get(blood_type, 0)
            if isinstance(inventory_value, str):
                try:
                    inventory_value = int(inventory_value)
                except ValueError:
                    continue  # Skip invalid inventory values

            if inventory_value > 0:
                has_valid_inventory = True
                break

        if has_valid_inventory and lab_id in graph[hospital_id]:
            distance = graph[hospital_id][lab_id]
            if distance < min_distance:
                min_distance = distance
                nearest_lab = lab

    return nearest_lab, min_distance

# Find the hospital from the requirements
hospital = next((h for h in hospital_nodes if h['id'] == required_hospital_id), None)

if hospital:
    nearest_lab, distance = find_nearest_lab(hospital['id'], lab_nodes, required_blood_types)

    if nearest_lab:
        print(f"Nearest Lab: {nearest_lab['name']}")
        print(f"Distance: {distance / 1000:.2f} km")  # Convert meters to kilometers
        print(f"Inventory: {nearest_lab['blood_inventory']}")
    else:
        print("No lab found with the required blood types.")
else:
    print("Hospital not found.")

# Create a NetworkX graph
G = nx.Graph()

# Add nodes with positions and color attributes
for node in hospital_nodes:
    node_id = node['id']
    node_location = node['location']
    G.add_node(node_id, pos=(node_location.latitude, node_location.longitude), color='blue')

for node in lab_nodes:
    node_id = node['id']
    node_location = node['location']
    G.add_node(node_id, pos=(node_location.latitude, node_location.longitude), color='red')

# Add edges with distances as weights
for node_id, edges in graph.items():
    for other_id, distance in edges.items():
        G.add_edge(node_id, other_id, weight=distance)

# Draw the graph with specific node colors
pos = nx.get_node_attributes(G, 'pos')
node_colors = [G.nodes[node]['color'] for node in G.nodes]
edge_weights = nx.get_edge_attributes(G, 'weight')

plt.figure(figsize=(12, 8))
nx.draw(G, pos, with_labels=True, node_size=2000, node_color=node_colors, font_size=10, font_weight='bold')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_weights)
plt.title('Hospital and Lab Network')
plt.show()
