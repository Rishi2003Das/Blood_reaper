import firebase_admin
from firebase_admin import credentials, firestore
import math
import networkx as nx
import matplotlib.pyplot as plt
import torch
from torch_geometric.data import Data
from torch_geometric.utils import from_networkx
from torch_geometric.nn import GCNConv
import torch.nn.functional as F

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

# Create a feature matrix for nodes
node_features = []
for node in hospital_nodes + lab_nodes:
    lat = node['location'].latitude
    lon = node['location'].longitude
    node_features.append([lat, lon])

node_features = torch.tensor(node_features, dtype=torch.float)

# Convert the NetworkX graph to PyTorch Geometric's format
G = nx.Graph()
for node in hospital_nodes:
    node_id = node['id']
    node_location = node['location']
    G.add_node(node_id, pos=(node_location.latitude, node_location.longitude), color='blue')

for node in lab_nodes:
    node_id = node['id']
    node_location = node['location']
    G.add_node(node_id, pos=(node_location.latitude, node_location.longitude), color='red')

for node_id, edges in graph.items():
    for other_id, distance in edges.items():
        G.add_edge(node_id, other_id, weight=distance)

# Convert to PyTorch Geometric Data object
data = from_networkx(G)
data.x = node_features

# Define the GNN model
class GCN(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super(GCN, self).__init__()
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, output_dim)

    def forward(self, x, edge_index, edge_weight=None):
        x = self.conv1(x, edge_index, edge_weight)
        x = F.relu(x)
        x = self.conv2(x, edge_index, edge_weight)
        return x

# Initialize the GNN model
input_dim = data.num_node_features
hidden_dim = 16
output_dim = 1
model = GCN(input_dim, hidden_dim, output_dim)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

# Define a dummy target (e.g., distance to the nearest lab)
# Replace with actual targets in a real scenario
target = torch.tensor([1.0] * data.num_nodes, dtype=torch.float).unsqueeze(1)  # Replace with actual targets

# Training loop
def train():
    model.train()
    optimizer.zero_grad()
    out = model(data.x, data.edge_index)
    loss = F.mse_loss(out, target)
    loss.backward()
    optimizer.step()
    return loss.item()

# Train the model
for epoch in range(200):
    loss = train()
    if epoch % 10 == 0:
        print(f'Epoch {epoch}, Loss: {loss}')

# Evaluate the model
model.eval()
with torch.no_grad():
    out = model(data.x, data.edge_index)

# Find the nearest lab to the required hospital based on GNN predictions
# This part needs a more concrete implementation based on the GNN output
# For now, we simply print out the node with the minimum predicted value
nearest_lab_index = torch.argmin(out)
nearest_lab_node = nodes[nearest_lab_index]
print(f"Nearest lab (based on GNN prediction): {nearest_lab_node['name']}")

# Create a visualization of the graph
pos = nx.get_node_attributes(G, 'pos')
node_colors = [G.nodes[node]['color'] for node in G.nodes]
edge_weights = nx.get_edge_attributes(G, 'weight')

plt.figure(figsize=(12, 8))
nx.draw(G, pos, with_labels=True, node_size=2000, node_color=node_colors, font_size=10, font_weight='bold')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_weights)
plt.title('Hospital and Lab Network')
plt.show()
