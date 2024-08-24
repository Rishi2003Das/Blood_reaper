import networkx as nx
import requests
import random


class BloodSupplyChainOptimizer:
    def __init__(self, ors_api_key):
        self.graph = nx.Graph()
        self.ors_api_key = ors_api_key

    def fetch_and_add_locations(self, latitude, longitude, radius=5000, location_type='hospital'):
        """
        Fetch locations of a specific type (e.g., hospitals) and add them to the graph using Nominatim.
        """
        locations = self.search_nearby_locations(latitude, longitude, radius, location_type)
        for loc in locations:
            self.add_location(loc['name'], loc['latitude'], loc['longitude'], is_hospital=(location_type == 'hospital'))

    def search_nearby_locations(self, latitude, longitude, radius=5000, location_type='hospital'):
        """
        Search for nearby locations of a specific type using the OpenStreetMap Nominatim API.
        """
        try:
            url = f"https://nominatim.openstreetmap.org/search?format=json&limit=50&q={location_type}&lat={latitude}&lon={longitude}&radius={radius}"
            response = requests.get(url)
            response.raise_for_status()
            results = response.json()
            locations = []

            for place in results:
                name = place.get('display_name', 'Unknown')
                lat = place.get('lat')
                lon = place.get('lon')
                if lat and lon:
                    locations.append({'name': name, 'latitude': lat, 'longitude': lon})

            return locations

        except requests.RequestException as e:
            print(f"Error fetching locations: {e}")
            return []

    def add_location(self, name, latitude, longitude, is_hospital=False, blood_inventory=None):
        """
        Add a location to the graph.
        """
        # Generate a realistic but arbitrary blood inventory
        blood_types = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
        if not blood_inventory:
            blood_inventory = {bt: random.randint(0, 20) for bt in blood_types}

        self.graph.add_node(name, latitude=latitude, longitude=longitude, is_hospital=is_hospital,
                            blood_inventory=blood_inventory)

    def add_edges_between_nodes(self):
        """
        Add edges between nodes using real distances obtained from the OpenRouteService API.
        """
        for u in self.graph.nodes:
            for v in self.graph.nodes:
                if u != v:
                    distance = self.calculate_real_distance(
                        self.graph.nodes[u]['latitude'],
                        self.graph.nodes[u]['longitude'],
                        self.graph.nodes[v]['latitude'],
                        self.graph.nodes[v]['longitude']
                    )
                    if distance:
                        self.graph.add_edge(u, v, base_travel_time=distance / 1000)  # Example conversion to travel time

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
            print(f"Error fetching distance between coordinates ({lat1}, {lon1}) and ({lat2}, {lon2}): {e}")
            return None

    def print_graph(self):
        """
        Print the nodes and edges of the graph with their attributes.
        """
        print("Nodes:")
        for node, data in self.graph.nodes(data=True):
            print(f"Node: {node}, Data: {data}")

        print("\nEdges:")
        for u, v, data in self.graph.edges(data=True):
            print(f"Edge: ({u}, {v}), Data: {data}")


# Example usage
ors_api_key = "5b3ce3597851110001cf62484c8507e38f224cfb97cfd5794311eadd"  # Replace with your OpenRouteService API key
optimizer = BloodSupplyChainOptimizer(ors_api_key)

# Fetch and add hospitals and blood banks
latitude = 13.082680
longitude = 80.270721
optimizer.fetch_and_add_locations(latitude, longitude, location_type='hospital')
optimizer.fetch_and_add_locations(latitude, longitude, location_type='blood_bank')

# Add edges between nodes using real distances
optimizer.add_edges_between_nodes()

# Print the graph details
optimizer.print_graph()
