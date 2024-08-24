import networkx as nx
import requests
from copy import deepcopy
import os

class BloodSupplyChainOptimizer:
    def __init__(self, traffic_api_key, weather_api_key, google_places_api_key):
        self.graph = nx.Graph()
        self.traffic_api_key = traffic_api_key
        self.weather_api_key = weather_api_key
        self.google_places_api_key = google_places_api_key

    def search_nearby_hospitals(self, latitude, longitude, radius=5000):
        """
        Search for hospitals near a specific location using the Google Places API.
        """
        try:
            url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={latitude},{longitude}&radius={radius}&type=hospital&key={self.google_places_api_key}"
            response = requests.get(url)
            response.raise_for_status()
            results = response.json().get('results', [])
            hospitals = []

            for place in results:
                name = place['name']
                lat = place['geometry']['location']['lat']
                lng = place['geometry']['location']['lng']
                hospitals.append({'name': name, 'latitude': lat, 'longitude': lng, 'is_hospital': True})

            return hospitals

        except requests.RequestException as e:
            print(f"Error fetching hospitals: {e}")
            return []

    def add_location(self, name, latitude, longitude, is_hospital=False, blood_inventory=None):
        """
        Add a location to the graph.
        """
        self.graph.add_node(name, latitude=latitude, longitude=longitude, is_hospital=is_hospital,
                            blood_inventory=blood_inventory or {})

    def add_route(self, loc1, loc2, base_travel_time):
        """
        Add a route between two locations with a base travel time.
        """
        if loc1 in self.graph.nodes and loc2 in self.graph.nodes:
            self.graph.add_edge(loc1, loc2, base_travel_time=base_travel_time)
        else:
            raise ValueError(f"One or both locations {loc1} and {loc2} are not in the graph.")

    def update_edge_weights(self):
        """
        Update edge weights dynamically based on real-time traffic and weather data.
        """
        for u, v, data in self.graph.edges(data=True):
            if 'latitude' in self.graph.nodes[u] and 'latitude' in self.graph.nodes[v]:
                base_time = data['base_travel_time']
                traffic_factor = self.get_real_time_traffic(u, v)
                weather_factor = self.get_real_time_weather(u, v)
                data['weight'] = base_time * (1 + traffic_factor + weather_factor)
            else:
                print(f"Skipping edge ({u}, {v}) due to missing latitude/longitude data.")

    def get_real_time_traffic(self, loc1, loc2):
        """
        Fetch real-time traffic data between two locations.
        """
        try:
            origin = f"{self.graph.nodes[loc1]['latitude']},{self.graph.nodes[loc1]['longitude']}"
            destination = f"{self.graph.nodes[loc2]['latitude']},{self.graph.nodes[loc2]['longitude']}"
            traffic_data = requests.get(
                f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={destination}&key={self.traffic_api_key}"
            ).json()
            duration = traffic_data['rows'][0]['elements'][0]['duration']['value']
            return duration / 60.0  # Convert to minutes
        except (IndexError, KeyError, requests.RequestException) as e:
            print(f"Error fetching traffic data between {loc1} and {loc2}: {e}")
            return 0

    def get_real_time_weather(self, loc1, loc2):
        """
        Fetch real-time weather data for a location.
        """
        try:
            latitude = self.graph.nodes[loc1]['latitude']
            longitude = self.graph.nodes[loc1]['longitude']
            weather_data = requests.get(
                f"https://api.weather.com/weather?lat={latitude}&lon={longitude}&key={self.weather_api_key}"
            ).json()
            return weather_data.get('weather_factor', 0)  # Default to 0 if no data available
        except (KeyError, IndexError, requests.RequestException) as e:
            print(f"Error fetching weather data for {loc1}: {e}")
            return 0

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
                            backup_paths.append(
                                (nx.dijkstra_path(self.graph, hospital_name, blood_bank, weight='weight'), path_length))
                    except nx.NetworkXNoPath:
                        continue

        return best_path, best_time, backup_paths

    def process_immediate_request(self, hospital_name, blood_type, required_units):
        """
        Handle an immediate request from a hospital.
        """
        best_path, best_time, backup_paths = self.find_optimal_route(hospital_name, blood_type, required_units,
                                                                     urgency='immediate')

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

