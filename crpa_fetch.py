import firebase_admin
from firebase_admin import credentials, db
import networkx as nx
import requests
import random
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BloodSupplyChainOptimizer:
    def __init__(self, ors_api_key):
        self.graph = nx.Graph()
        self.ors_api_key = ors_api_key

        # Initialize Firebase
        cred = credentials.Certificate('path/to/your/serviceAccountKey.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': "https://blood-reaper-f7580-default-rtdb.firebaseio.com"
        })

    def fetch_and_add_locations(self, location_type='hospital'):
        """
        Fetch locations of a specific type (e.g., hospitals or blood banks) from Firebase and add them to the graph.
        """
        ref_path = f'/{location_type}s'
        ref = db.reference(ref_path)
        locations = ref.get()

        if locations:
            logging.info(f"Fetched {len(locations)} {location_type}s from Firebase.")
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(self.process_location, loc_id, loc_data, location_type) for loc_id, loc_data in locations.items()]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logging.error(f"Error processing location: {e}")

    def process_location(self, loc_id, loc_data, location_type):
        """
        Process individual location data and add it to the graph.
        """
        try:
            name = loc_data.get('name', 'Unknown')
            latitude = loc_data.get('location', {}).get('lat')
            longitude = loc_data.get('location', {}).get('lng')
            blood_inventory = loc_data.get('blood_inventory', None)
            if not name or latitude is None or longitude is None:
                raise ValueError("Invalid location data")

            self.add_location(name, latitude, longitude, is_hospital=(location_type == 'hospitals'), blood_inventory=blood_inventory)
        except ValueError as ve:
            logging.warning(f"Skipping location due to validation error: {ve}")
        except Exception as e:
            logging.error(f"Error in processing location: {e}")

    def add_location(self, name, latitude, longitude, is_hospital=False, blood_inventory=None):
        """
        Add a location to the graph.
        """
        if blood_inventory is None:
            blood_types = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
            blood_inventory = {bt: random.randint(0, 20) for bt in blood_types}

        self.graph.add_node(name, latitude=latitude, longitude=longitude, is_hospital=is_hospital, blood_inventory=blood_inventory)
        logging.info(f"Added location: {name}")

    def add_edges_between_nodes(self):
        """
        Add edges between nodes using real distances obtained from the OpenRouteService API.
        """
        nodes = list(self.graph.nodes)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.process_edge, u, v) for u in nodes for v in nodes if u != v]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error processing edge: {e}")

    def process_edge(self, u, v):
        """
        Calculate the distance between two nodes and add an edge to the graph.
        """
        try:
            distance = self.calculate_real_distance(
                self.graph.nodes[u]['latitude'],
                self.graph.nodes[u]['longitude'],
                self.graph.nodes[v]['latitude'],
                self.graph.nodes[v]['longitude']
            )
            if distance is not None:
                self.graph.add_edge(u, v, base_travel_time=distance / 1000)  # Example conversion to travel time
                logging.info(f"Added edge between {u} and {v} with distance {distance} meters")
        except Exception as e:
            logging.error(f"Error adding edge between {u} and {v}: {e}")

    def calculate_real_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate the real distance between two points using the OpenRouteService API.
        """
        try:
            url = f"https://api.openrouteservice.org/v2/directions/driving-car?api_key={self.ors_api_key}"
            payload = {
                "coordinates": [[lon1, lat1], [lon2, lat2]],
                "units": "m"
            }
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            distance = data['routes'][0]['summary']['distance']
            return distance
        except (IndexError, KeyError, requests.RequestException) as e:
            logging.error(f"Error fetching distance between coordinates ({lat1}, {lon1}) and ({lat2}, {lon2}): {e}")
            return None

    def visualize_graph(self):
        """
        Visualize the graph using matplotlib.
        """
        pos = nx.spring_layout(self.graph, seed=42)  # Position nodes using a layout algorithm

        # Draw nodes
        node_colors = ['lightgreen' if data['is_hospital'] else 'lightblue' for _, data in self.graph.nodes(data=True)]
        nx.draw_networkx_nodes(self.graph, pos, node_color=node_colors, node_size=500, alpha=0.7)

        # Draw edges
        nx.draw_networkx_edges(self.graph, pos, alpha=0.5)

        # Draw labels
        labels = {node: f"{node}\n{data['blood_inventory']}" for node, data in self.graph.nodes(data=True)}
        nx.draw_networkx_labels(self.graph, pos, labels=labels, font_size=8, verticalalignment='bottom')

        plt.title("Blood Supply Chain Network")
        plt.show()

    def print_graph(self):
        """
        Print the nodes and edges of the graph with their attributes.
        """
        logging.info("Nodes:")
        for node, data in self.graph.nodes(data=True):
            logging.info(f"Node: {node}, Data: {data}")

        logging.info("\nEdges:")
        for u, v, data in self.graph.edges(data=True):
            logging.info(f"Edge: ({u}, {v}), Data: {data}")

# Example usage
ors_api_key = "5b3ce3597851110001cf62484c8507e38f224cfb97cfd5794311eadd"  # Replace with your OpenRouteService API key
optimizer = BloodSupplyChainOptimizer(ors_api_key)

# Fetch and add hospitals and blood banks
optimizer.fetch_and_add_locations(location_type='hospital')
optimizer.fetch_and_add_locations(location_type='blood_bank')

# Add edges between nodes using real distances
optimizer.add_edges_between_nodes()

# Print the graph details
optimizer.print_graph()

# Visualize the graph
optimizer.visualize_graph()