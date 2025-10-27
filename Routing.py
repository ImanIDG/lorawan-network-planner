import math
from collections import deque, defaultdict

class LoRaNetworkPlanner:
    def __init__(self):
        self.nodes = {}
        self.gateway = None
        self.available_frequencies = list(range(16, 31))  # 16-30 for node-to-node
        self.failed_connections = set()  # Store failed connections as tuples (node1, node2)
        
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
    
    def get_gateway_data(self):
        """Get gateway information from user"""
        print("\n=== GATEWAY SETUP ===")
        name = "GW"  # Default name
        lat = float(input("Enter gateway latitude: "))
        lon = float(input("Enter gateway longitude: "))
        
        self.gateway = {
            'name': name,
            'lat': lat,
            'lon': lon,
            'type': 'gateway',
            'children': [],
            'parent': None,
            'freq_down': None
        }
    
    def get_nodes_data(self):
        """Get nodes information from user"""
        print("\n=== NODES SETUP ===")
        num_nodes = int(input("How many nodes do you want to add? "))
        
        for i in range(num_nodes):
            print(f"\n--- Node {i+1} ---")
            name = input("Enter node name: ")
            lat = float(input("Enter node latitude: "))
            lon = float(input("Enter node longitude: "))
            direct_to_gw = input("Can connect directly to gateway? (y/n): ").lower() == 'y'
            
            self.add_node(name, lat, lon, direct_to_gw)
    
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
    
    def add_failed_connection(self):
        """Manually add a failed connection"""
        print("\n=== ADD FAILED CONNECTION ===")
        print("Available nodes:", list(self.nodes.keys()))
        
        node1 = input("Enter first node name (or 'gateway' for gateway): ")
        node2 = input("Enter second node name: ")
        
        # Validate inputs
        if node1 != 'gateway' and node1 not in self.nodes:
            print(f"Error: {node1} is not a valid node name")
            return
        
        if node2 not in self.nodes:
            print(f"Error: {node2} is not a valid node name")
            return
        
        connection = tuple(sorted([node1, node2]))  # Store in consistent order
        self.failed_connections.add(connection)
        print(f"✓ Added failed connection: {node1} <-> {node2}")
    
    def remove_failed_connection(self):
        """Remove a failed connection"""
        if not self.failed_connections:
            print("No failed connections to remove")
            return
            
        print("\n=== REMOVE FAILED CONNECTION ===")
        print("Current failed connections:")
        for i, conn in enumerate(self.failed_connections, 1):
            print(f"  {i}. {conn[0]} <-> {conn[1]}")
        
        try:
            choice = int(input("Enter the number of connection to remove: ")) - 1
            if 0 <= choice < len(self.failed_connections):
                removed = list(self.failed_connections)[choice]
                self.failed_connections.remove(removed)
                print(f"✓ Removed failed connection: {removed[0]} <-> {removed[1]}")
            else:
                print("Invalid choice")
        except ValueError:
            print("Please enter a valid number")
    
    def build_connection_map(self):
        """Build a map of all possible connections based on distance, direct gateway connections, and failed connections"""
        connection_map = defaultdict(list)
        unavailable_connections = []
        
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
                    print(f"✓ {node_name} can connect directly to gateway (distance: {distance:.2f}km)")
                else:
                    if is_failed:
                        reason = "Manually marked as failed connection"
                    elif not node['direct_to_gw']:
                        reason = "No direct gateway connection allowed"
                    else:
                        reason = f"Distance too far: {distance:.2f}km"
                    unavailable_connections.append(('gateway', node_name, reason))
                    print(f"✗ {node_name} cannot connect directly to gateway ({reason})")
        
        # Check node-to-node connections
        print("\n--- Node-to-Node Connections ---")
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
                    print(f"✓ {node1['name']} <-> {node2['name']}: {distance:.2f}km - CONNECTION AVAILABLE")
                else:
                    if is_failed:
                        reason = "Manually marked as failed connection"
                    else:
                        reason = f"Distance: {distance:.2f}km"
                    unavailable_connections.append((node1['name'], node2['name'], reason))
                    print(f"✗ {node1['name']} <-> {node2['name']}: {distance:.2f}km - {reason.upper()}")
        
        return connection_map, unavailable_connections
    
    def find_best_tree(self, connection_map):
        """Find the optimal tree using BFS with capacity constraints"""
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
                        # Check if current node can accept more children
                        if current == 'gateway':
                            if len(self.gateway['children']) < 4:
                                self.nodes[neighbor]['parent'] = 'gateway'
                                self.nodes[neighbor]['visited'] = True
                                self.gateway['children'].append(neighbor)
                                queue.append(neighbor)
                                visited_count += 1
                                print(f"  Tree: Gateway → {neighbor}")
                        else:
                            if len(self.nodes[current]['children']) < 4:
                                self.nodes[neighbor]['parent'] = current
                                self.nodes[neighbor]['visited'] = True
                                self.nodes[current]['children'].append(neighbor)
                                queue.append(neighbor)
                                visited_count += 1
                                print(f"  Tree: {current} → {neighbor}")
        
        # Check for unreachable nodes
        unreachable_nodes = [name for name, node in self.nodes.items() if not node['visited']]
        
        print(f"\n📊 Network Statistics:")
        print(f"   - Connected nodes: {visited_count}")
        print(f"   - Unreachable nodes: {len(unreachable_nodes)}")
        print(f"   - Failed connections: {len(self.failed_connections)}")
        
        return unreachable_nodes
    
    def assign_frequencies(self):
        """Assign frequencies to all nodes in the tree"""
        if not self.gateway:
            return
        
        # Assign gateway frequency (0-7)
        self.gateway['freq_down'] = 3  # Can be any from 0-7
        
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
                else:
                    raise Exception("No more frequencies available in pool 16-30")
            
            # Add children to queue
            queue.extend(current_node['children'])
    
    def generate_configuration_commands(self):
        """Generate commands to change node frequencies"""
        commands = []
        
        for node_name, node in self.nodes.items():
            if node['parent']:  # Only configured nodes
                cmd = f"CONFIG_NODE {node_name}: PARENT={node['parent']}, FREQ_UP={node['freq_up']}"
                if node['freq_down']:
                    cmd += f", FREQ_DOWN={node['freq_down']}"
                commands.append(cmd)
        
        return commands
    
    def print_network_tree(self):
        """Print the network tree structure"""
        print("\n" + "="*60)
        print("FINAL NETWORK TREE STRUCTURE")
        print("="*60)
        
        def print_node(name, level=0):
            indent = "    " * level
            if name == 'gateway':
                node = self.gateway
                print(f"{indent}🏠 Gateway (Freq DOWN: {node['freq_down']})")
            else:
                node = self.nodes[name]
                freq_info = f"Freq UP: {node['freq_up']}"
                if node['freq_down']:
                    freq_info += f", Freq DOWN: {node['freq_down']}"
                parent_info = f"Parent: {node['parent']}"
                print(f"{indent}└── 📍 {node['name']}")
                print(f"{indent}    ├── {parent_info}")
                print(f"{indent}    └── {freq_info}")
            
            for child in node.get('children', []):
                print_node(child, level + 1)
        
        print_node('gateway')
    
    def print_unreachable_nodes(self, unreachable_nodes):
        """Print information about unreachable nodes"""
        if unreachable_nodes:
            print(f"\n⚠️  WARNING: {len(unreachable_nodes)} nodes are unreachable!")
            for node_name in unreachable_nodes:
                node = self.nodes[node_name]
                print(f"   - {node_name} at ({node['lat']}, {node['lon']})")
            print("  These nodes cannot connect to the gateway through any path.")
        else:
            print(f"\n✅ All nodes are reachable!")
    
    def print_failed_connections(self):
        """Print all manually failed connections"""
        if self.failed_connections:
            print("\n🔴 MANUALLY FAILED CONNECTIONS:")
            for conn in self.failed_connections:
                print(f"   - {conn[0]} <-> {conn[1]}")
        else:
            print("\n✅ No manually failed connections")
    
    def edit_network_menu(self):
        """Menu for editing the network"""
        while True:
            print("\n" + "="*50)
            print("NETWORK EDITING MENU")
            print("="*50)
            print("1. Add failed connection")
            print("2. Remove failed connection")
            print("3. View current failed connections")
            print("4. Rebuild network with current settings")
            print("5. Return to main menu")
            
            choice = input("\nEnter your choice (1-5): ")
            
            if choice == '1':
                self.add_failed_connection()
            elif choice == '2':
                self.remove_failed_connection()
            elif choice == '3':
                self.print_failed_connections()
            elif choice == '4':
                return True  # Signal to rebuild
            elif choice == '5':
                return False  # Signal to exit
            else:
                print("Invalid choice. Please try again.")
    
    def plan_network(self):
        """Main function to plan the entire network"""
        print("\n" + "="*50)
        print("LoRa NETWORK PLANNING SYSTEM")
        print("="*50)
        
        # Get data from user
        self.get_gateway_data()
        self.get_nodes_data()
        
        rebuild_needed = True
        
        while rebuild_needed:
            print("\n" + "="*50)
            print("BUILDING NETWORK...")
            print("="*50)
            
            # Build connection map
            connection_map, unavailable_connections = self.build_connection_map()
            
            # Show failed connections
            self.print_failed_connections()
            
            # Find optimal tree
            print("\n--- Building Network Tree ---")
            unreachable_nodes = self.find_best_tree(connection_map)
            
            # Print unreachable nodes info
            self.print_unreachable_nodes(unreachable_nodes)
            
            # Assign frequencies
            self.assign_frequencies()
            
            # Print results
            self.print_network_tree()
            
            # Generate configuration commands
            commands = self.generate_configuration_commands()
            
            print("\n" + "="*50)
            print("CONFIGURATION COMMANDS")
            print("="*50)
            for cmd in commands:
                print(f"  {cmd}")
            
            print(f"\n🎯 Configuration complete! Send {len(commands)} commands to configure your network.")
            
            # Ask if user wants to edit the network
            edit_choice = input("\nDo you want to edit the network (add/remove failed connections)? (y/n): ").lower()
            if edit_choice == 'y':
                rebuild_needed = self.edit_network_menu()
            else:
                rebuild_needed = False

def main():
    """Main function to run the network planner"""
    planner = LoRaNetworkPlanner()
    planner.plan_network()

if __name__ == "__main__":
    main()