import math
import json
import sys
import os
from collections import deque, defaultdict

class LoRaNetworkPlanner:
    def __init__(self, routes_file="lorawan_routes.txt", failed_file="lorawan_failed.txt"):
        self.nodes = {}
        self.gateway = None
        self.available_frequencies = list(range(16, 31))  # 16-30 for node-to-node
        self.failed_connections = set()  # Store failed connections as tuples (node1, node2)
        
        # File paths for saving routes and failed connections
        self.routes_file = routes_file
        self.failed_file = failed_file
        
        # Load existing failed connections from file
        self.load_failed_connections()
    
    def load_failed_connections(self):
        """Load failed connections from file"""
        try:
            if os.path.exists(self.failed_file):
                with open(self.failed_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and ':' in line:
                            node1, node2 = line.split(':')
                            self.failed_connections.add((node1.strip(), node2.strip()))
                print(f"✓ Loaded {len(self.failed_connections)} failed connections from {self.failed_file}")
        except Exception as e:
            print(f"✗ Error loading failed connections: {e}")
    
    def save_failed_connections(self):
        """Save failed connections to file"""
        try:
            with open(self.failed_file, 'w') as f:
                for conn in self.failed_connections:
                    f.write(f"{conn[0]}:{conn[1]}\n")
            print(f"✓ Saved {len(self.failed_connections)} failed connections to {self.failed_file}")
        except Exception as e:
            print(f"✗ Error saving failed connections: {e}")
    
    def save_routes_to_file(self, connection_map, unreachable_nodes):
        """Save current routes to file"""
        try:
            routes_data = {
                'gateway': self.gateway,
                'nodes': self.nodes,
                'connection_map': dict(connection_map),
                'unreachable_nodes': unreachable_nodes,
                'available_frequencies': self.available_frequencies,
                'timestamp': math.floor(sys.maxsize)  # Current timestamp
            }
            
            with open(self.routes_file, 'w') as f:
                json.dump(routes_data, f, indent=2)
            print(f"✓ Saved routes to {self.routes_file}")
        except Exception as e:
            print(f"✗ Error saving routes: {e}")
    
    def load_routes_from_file(self):
        """Load routes from file"""
        try:
            if os.path.exists(self.routes_file):
                with open(self.routes_file, 'r') as f:
                    routes_data = json.load(f)
                return routes_data
            return None
        except Exception as e:
            print(f"✗ Error loading routes: {e}")
            return None
        
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the great-circle distance between two points on Earth in kilometers"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def add_failed_connection(self, node1, node2):
        """Add a failed connection and save to file"""
        connection = tuple(sorted([node1, node2]))  # Store in consistent order
        self.failed_connections.add(connection)
        self.save_failed_connections()
        print(f"✓ Added failed connection: {node1} <-> {node2}")
    
    def remove_failed_connection(self, node1, node2):
        """Remove a failed connection and save to file"""
        connection = tuple(sorted([node1, node2]))
        if connection in self.failed_connections:
            self.failed_connections.remove(connection)
            self.save_failed_connections()
            print(f"✓ Removed failed connection: {node1} <-> {node2}")
            return True
        return False
    
    def update_node_position(self, node_name, lat, lon, direct_to_gw=False):
        """Update or add a node position"""
        self.add_node(node_name, lat, lon, direct_to_gw)
    
    def add_node(self, name, lat, lon, direct_to_gw=False):
        """Add a node to the network"""
        self.nodes[name] = {
            'name': name,
            'lat': lat,
            'lon': lon,
            'direct_to_gw': direct_to_gw,
            'type': 'node',
            'parent': None,
            'children': [],
            'freq_up': None,
            'freq_down': None,
            'visited': False
        }
    
    def set_gateway_position(self, lat, lon):
        """Set gateway position"""
        self.gateway = {
            'name': 'GW',
            'lat': lat,
            'lon': lon,
            'type': 'gateway',
            'children': [],
            'parent': None,
            'freq_down': 3
        }
    
    def build_connection_map(self):
        """Build a map of all possible connections based on distance, direct gateway connections, and failed connections"""
        connection_map = defaultdict(list)
        
        # Check node-to-gateway connections
        if self.gateway:
            for node_name, node in self.nodes.items():
                distance = self.haversine_distance(
                    self.gateway['lat'], self.gateway['lon'],
                    node['lat'], node['lon']
                )
                
                # Check if this connection is manually marked as failed
                connection_pair = tuple(sorted(['gateway', node_name]))
                is_failed = connection_pair in self.failed_connections
                
                if node['direct_to_gw'] and distance <= 5 and not is_failed:
                    connection_map['gateway'].append(node_name)
                    connection_map[node_name].append('gateway')
        
        # Check node-to-node connections
        node_list = list(self.nodes.keys())
        for i in range(len(node_list)):
            for j in range(i + 1, len(node_list)):
                node1 = self.nodes[node_list[i]]
                node2 = self.nodes[node_list[j]]
                
                distance = self.haversine_distance(
                    node1['lat'], node1['lon'],
                    node2['lat'], node2['lon']
                )
                
                # Check if this connection is manually marked as failed
                connection_pair = tuple(sorted([node1['name'], node2['name']]))
                is_failed = connection_pair in self.failed_connections
                
                if distance < 5 and not is_failed:
                    connection_map[node1['name']].append(node2['name'])
                    connection_map[node2['name']].append(node1['name'])
        
        return connection_map
    
    def find_best_tree(self, connection_map):
        """Find the optimal tree using BFS - Gateway can have unlimited children"""
        if not self.gateway:
            return None
        
        # Reset node states
        for node in self.nodes.values():
            node['visited'] = False
            node['parent'] = None
            node['children'] = []
        
        self.gateway['children'] = []
        
        queue = deque(['gateway'])
        visited_count = 0
        
        while queue:
            current = queue.popleft()
            
            if current in connection_map:
                for neighbor in connection_map[current]:
                    if neighbor != 'gateway' and not self.nodes[neighbor]['visited']:
                        # Gateway can have unlimited children
                        if current == 'gateway':
                            self.nodes[neighbor]['parent'] = 'gateway'
                            self.nodes[neighbor]['visited'] = True
                            self.gateway['children'].append(neighbor)
                            queue.append(neighbor)
                            visited_count += 1
                        else:
                            if len(self.nodes[current]['children']) < 4:
                                self.nodes[neighbor]['parent'] = current
                                self.nodes[neighbor]['visited'] = True
                                self.nodes[current]['children'].append(neighbor)
                                queue.append(neighbor)
                                visited_count += 1
        
        # Check for unreachable nodes
        unreachable_nodes = [name for name, node in self.nodes.items() if not node['visited']]
        
        return unreachable_nodes, visited_count
    
    def assign_frequencies(self):
        """Assign frequencies to all nodes in the tree"""
        if not self.gateway:
            return
        
        queue = deque(self.gateway['children'])
        freq_pool = self.available_frequencies.copy()
        
        while queue:
            current_name = queue.popleft()
            current_node = self.nodes[current_name]
            
            # Set frequency UP to match parent's frequency DOWN
            if current_node['parent'] == 'gateway':
                current_node['freq_up'] = self.gateway['freq_down']
            else:
                current_node['freq_up'] = self.nodes[current_node['parent']]['freq_down']
            
            # Assign frequency DOWN for children if needed
            if current_node['children']:
                if freq_pool:
                    current_node['freq_down'] = freq_pool.pop(0)
            
            # Add children to queue
            queue.extend(current_node['children'])
    
    def calculate_direct_to_gw(self, node_lat, node_lon):
        """Calculate if node can connect directly to gateway or any other node"""
        # Check gateway connection
        if self.gateway:
            distance_to_gw = self.haversine_distance(
                self.gateway['lat'], self.gateway['lon'],
                node_lat, node_lon
            )
            connection_pair = tuple(sorted(['gateway', 'any_node']))  # Generic check
            is_failed = any(conn for conn in self.failed_connections if 'gateway' in conn)
            
            if distance_to_gw <= 5 and not is_failed:
                return True
        
        # Check connection to any existing node
        for existing_node_name, existing_node in self.nodes.items():
            distance_to_node = self.haversine_distance(
                existing_node['lat'], existing_node['lon'],
                node_lat, node_lon
            )
            connection_pair = tuple(sorted(['any_node', existing_node_name]))
            is_failed = connection_pair in self.failed_connections
            
            if distance_to_node <= 5 and not is_failed:
                return True
        
        return False

    def calculate_routes_for_node(self, node_name, lat, lon):
        """Calculate routes for a specific node and return configuration"""
        # Calculate directToGateway automatically
        direct_to_gw = self.calculate_direct_to_gw(lat, lon)
        
        # Update node position
        self.update_node_position(node_name, lat, lon, direct_to_gw)
        
        # Build connection map and find best tree
        connection_map = self.build_connection_map()
        unreachable_nodes, connected_count = self.find_best_tree(connection_map)
        
        # Assign frequencies
        self.assign_frequencies()
        
        # Save routes to file
        self.save_routes_to_file(connection_map, unreachable_nodes)
        
        # Generate configuration for the specific node
        if node_name in self.nodes:
            node = self.nodes[node_name]
            if node['parent']:  # Only if node is reachable
                config = {
                    'node_name': node_name,
                    'parent': node['parent'],  # This goes to routes file, not Java
                    'freq_up': node['freq_up'],
                    'freq_down': node.get('freq_down'),
                    'reachable': True,
                    'direct_to_gw': direct_to_gw,  # Calculated value
                    'connected_nodes': connected_count,
                    'unreachable_nodes': len(unreachable_nodes)
                }
                return config
        
        return {
            'node_name': node_name,
            'parent': None,
            'freq_up': None,
            'freq_down': None,
            'reachable': False,
            'direct_to_gw': direct_to_gw,  # Calculated value
            'connected_nodes': connected_count,
            'unreachable_nodes': len(unreachable_nodes)
        }

def main():
    """Standalone mode for testing"""
    planner = LoRaNetworkPlanner()
    
    # Example usage
    planner.set_gateway_position(40.7128, -74.0060)  # New York
    
    # Add some nodes
    planner.add_node("Node1", 40.7128, -74.0060, True)
    planner.add_node("Node2", 40.7129, -74.0061, False)
    
    # Calculate routes
    result = planner.calculate_routes_for_node("Node1", 40.7128, -74.0060, True)
    print("Route calculation result:", result)

if __name__ == "__main__":
    # If called with arguments, run in API mode
    if len(sys.argv) > 1:
        planner = LoRaNetworkPlanner()
        
        if sys.argv[1] == "calculate_route":
            if len(sys.argv) >= 6:
                node_name = sys.argv[2]
                lat = float(sys.argv[3])
                lon = float(sys.argv[4])
                direct_to_gw = planner.calculate_direct_to_gw(lat, lon)
                
                result = planner.calculate_routes_for_node(node_name, lat, lon, direct_to_gw)
                print(json.dumps(result))
            else:
                print("Error: Insufficient arguments for calculate_route")
        
        elif sys.argv[1] == "add_failed":
            if len(sys.argv) >= 4:
                node1 = sys.argv[2]
                node2 = sys.argv[3]
                planner.add_failed_connection(node1, node2)
                print("Success: Failed connection added")
            else:
                print("Error: Insufficient arguments for add_failed")
        
        elif sys.argv[1] == "remove_failed":
            if len(sys.argv) >= 4:
                node1 = sys.argv[2]
                node2 = sys.argv[3]
                success = planner.remove_failed_connection(node1, node2)
                print(f"Success: {success}")
            else:
                print("Error: Insufficient arguments for remove_failed")
    else:
        main()