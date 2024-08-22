import networkx as nx
import requests
from copy import deepcopy

class BloodSupplyChainOptimizer:
    def __init__(self, traffic_api_key, weather_api_key):
        self.graph = nx.Graph()
        self.traffic_api_key = traffic_api_key
        self.weather_api_key = weather_api_key

    def add_location(self, name, latitude, longitude, is_hospital=False, blood_inventory=None):
        """
        Add a location to the graph. If it's a hospital, set is_hospital=True.
        If it's a blood bank, provide a blood_inventory dictionary.
        """
        self.graph.add_node(name, latitude=latitude, longitude=longitude, is_hospital=is_hospital, blood_inventory=blood_inventory or {})

    def add_route(self, loc1, loc2, base_travel_time):
        """
        Add a route between two locations with a base travel time.
        """
        self.graph.add_edge(loc1, loc2, base_travel_time=base_travel_time)

    def update_edge_weights(self):
        """
        Update edge weights dynamically based on real-time traffic and weather data.
        """
        for u, v, data in self.graph.edges(data=True):
            base_time = data['base_travel_time']
            traffic_factor = self.get_real_time_traffic(u, v)
            weather_factor = self.get_real_time_weather(u, v)
            data['weight'] = base_time * (1 + traffic_factor + weather_factor)

    def get_real_time_traffic(self, loc1, loc2):
        """
        Fetch real-time traffic data between two locations.
        """
        traffic_data = requests.get(f"https://api.traffic.com/traffic?origin={self.graph.nodes[loc1]['latitude']},{self.graph.nodes[loc1]['longitude']}&destination={self.graph.nodes[loc2]['latitude']},{self.graph.nodes[loc2]['longitude']}&key={self.traffic_api_key}").json()
        return traffic_data.get('traffic_factor', 0)  # Default to 0 if no data available

    def get_real_time_weather(self, loc1, loc2):
        """
        Fetch real-time weather data for a location.
        """
        weather_data = requests.get(f"https://api.weather.com/weather?lat={self.graph.nodes[loc1]['latitude']}&lon={self.graph.nodes[loc1]['longitude']}&key={self.weather_api_key}").json()
        return weather_data.get('weather_factor', 0)  # Default to 0 if no data available

    def find_optimal_route(self, hospital_name, blood_type, required_units, urgency='regular'):
        """
        Find the optimal route to fulfill a hospital's blood request.
        """
        self.update_edge_weights()

        best_time = float('inf')
        best_path = None
        backup_paths = []

        for blood_bank in self.graph.nodes():
            if not self.graph.nodes[blood_bank]['is_hospital']:
                inventory = self.graph.nodes[blood_bank]['blood_inventory']
                if inventory.get(blood_type, 0) >= required_units:
                    try:
                        path_length = nx.dijkstra_path_length(self.graph, hospital_name, blood_bank, weight='weight')
                        if urgency == 'immediate':
                            path_length *= 1.0  # Higher priority
                        else:
                            path_length *= 1.2  # Normal priority
                        if path_length < best_time:
                            if best_path:
                                backup_paths.append((best_path, best_time))  # Save the previous best path as a backup
                            best_time = path_length
                            best_path = nx.dijkstra_path(self.graph, hospital_name, blood_bank, weight='weight')
                        else:
                            backup_paths.append((nx.dijkstra_path(self.graph, hospital_name, blood_bank, weight='weight'), path_length))
                    except nx.NetworkXNoPath:
                        continue

        return best_path, best_time, backup_paths

    def process_immediate_request(self, hospital_name, blood_type, required_units):
        """
        Handle an immediate request from a hospital.
        """
        best_path, best_time, backup_paths = self.find_optimal_route(hospital_name, blood_type, required_units, urgency='immediate')
        
        if best_path:
            # Deduct the required units from the blood bank's inventory
            blood_bank = best_path[-1]
            if self.graph.nodes[blood_bank]['blood_inventory'][blood_type] >= required_units:
                self.graph.nodes[blood_bank]['blood_inventory'][blood_type] -= required_units
                return best_path, best_time
            else:
                # If inventory is insufficient, try backup paths
                for backup_path, _ in backup_paths:
                    blood_bank_backup = backup_path[-1]
                    if self.graph.nodes[blood_bank_backup]['blood_inventory'][blood_type] >= required_units:
                        self.graph.nodes[blood_bank_backup]['blood_inventory'][blood_type] -= required_units
                        return backup_path, _
        return None, None  # No suitable blood bank found

    def restock_blood_bank(self, blood_bank_name, blood_type, units):
        """
        Restock a blood bank with specific units of a blood type.
        """
        if not self.graph.nodes[blood_bank_name]['is_hospital']:
            if blood_type in self.graph.nodes[blood_bank_name]['blood_inventory']:
                self.graph.nodes[blood_bank_name]['blood_inventory'][blood_type] += units
            else:
                self.graph.nodes[blood_bank_name]['blood_inventory'][blood_type] = units

    def scalable_add_locations(self, locations):
        """
        Add multiple locations (hospitals or blood banks) at once.
        """
        for loc in locations:
            self.add_location(**loc)

    def scalable_add_routes(self, routes):
        """
        Add multiple routes between locations at once.
        """
        for route in routes:
            self.add_route(**route)

# Example usage:
traffic_api_key = 'YOUR_TRAFFIC_API_KEY'
weather_api_key = 'YOUR_WEATHER_API_KEY'

optimizer = BloodSupplyChainOptimizer(traffic_api_key, weather_api_key)

# Add hospitals and blood banks with detailed inventory
optimizer.add_location('Hospital A', 28.6139, 77.2090, is_hospital=True)
optimizer.add_location('Blood Bank 1', 28.7041, 77.1025, blood_inventory={'A+': 10, 'O+': 5, 'B+': 8})
optimizer.add_location('Blood Bank 2', 28.5355, 77.3910, blood_inventory={'A+': 3, 'O+': 2, 'B+': 4})

# Add routes
optimizer.add_route('Hospital A', 'Blood Bank 1', base_travel_time=30)
optimizer.add_route('Hospital A', 'Blood Bank 2', base_travel_time=45)
optimizer.add_route('Blood Bank 1', 'Blood Bank 2', base_travel_time=20)

# Process an immediate request from a hospital
path, time = optimizer.process_immediate_request('Hospital A', 'A+', 5)
if path:
    print(f'Optimal path: {path} with travel time: {time} minutes')
else:
    print('No suitable blood bank found.')

# Restock a blood bank
optimizer.restock_blood_bank('Blood Bank 1', 'A+', 5)

