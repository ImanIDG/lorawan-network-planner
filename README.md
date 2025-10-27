# LoRaWAN Network Planner

A Python-based routing algorithm for optimizing LoRaWAN mesh network topologies. Calculates optimal parent-child relationships and frequency assignments for sensor nodes communicating with gateways.

## Key Features

- **Dynamic Route Calculation**: Finds optimal paths using BFS algorithm
- **Distance-based Connectivity**: Uses Haversine formula for geographical distance calculations
- **Frequency Management**: Assigns uplink/downlink frequencies (16-30 range)
- **Failed Connection Handling**: Supports manual override of unavailable routes
- **Multi-hop Support**: Nodes can relay through other nodes (max 4 children per node)
- **Gateway Optimization**: Unlimited direct gateway connections when possible

## Use Cases

- IoT sensor network deployment planning
- LoRaWAN mesh network optimization
- Academic research on wireless sensor networks
- Network simulation and capacity planning

## Integration

Designed to work with Java-based LoRaWAN handlers via command-line interface. Returns JSON-formatted routing configurations for immediate downlink queuing.

## File Outputs

- `lorawan_routes.txt`: Current network topology and assignments
- `lorawan_failed.txt`: Manually managed connection blacklist## Quick Start

```python
from Routing import LoRaNetworkPlanner

planner = LoRaNetworkPlanner()
planner.set_gateway_position(40.7128, -74.0060)
result = planner.calculate_routes_for_node("Sensor01", 40.7129, -74.0061)

# Calculate routes for a node
python Routing.py calculate_route Node1 40.7128 -74.0060

# Add failed connection
python Routing.py add_failed Node1 Node2

# Remove failed connection  
python Routing.py remove_failed Node1 Node2
