import networkx as nx
import requests

class BloodSupplyChainOptimizer:
    def __init__(self):
        self.graph = nx.Graph()

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
        self.graph.add_node(name, latitude=latitude, longitude=longitude, is_hospital=is_hospital,
                            blood_inventory=blood_inventory or {})

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
optimizer = BloodSupplyChainOptimizer()

# Fetch and add hospitals and blood banks
latitude = 13.082680
longitude = 80.270721
optimizer.fetch_and_add_locations(latitude, longitude, location_type='hospital')
optimizer.fetch_and_add_locations(latitude, longitude, location_type='blood_bank')

# Print the graph details
optimizer.print_graph()
