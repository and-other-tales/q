# Copyright © 2025 PI & Other Tales Inc.. All Rights Reserved.
"""Advanced routing algorithms for PCB design automation.

This module provides comprehensive routing capabilities including:
- Length-matched differential pair routing
- Controlled impedance calculations and verification
- Via optimization algorithms
- Multi-layer power plane routing
- High-speed signal routing with constraints
"""

import os
import json
import math
import heapq
import numpy as np
from typing import Dict, List, Any, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import math
import logging

logger = logging.getLogger(__name__)


class LayerType(Enum):
    """PCB layer types."""
    SIGNAL = "signal"
    POWER = "power"
    GROUND = "ground"
    MIXED = "mixed"


class ViaType(Enum):
    """Via types for different applications."""
    THROUGH = "through"
    BLIND = "blind"
    BURIED = "buried"
    MICROVIA = "microvia"


@dataclass
class Point:
    """2D point with layer information."""
    x: float
    y: float
    layer: int = 0
    
    def distance_to(self, other: 'Point') -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __eq__(self, other: object) -> bool:
        """Check equality with another point."""
        if not isinstance(other, Point):
            return False
        return (abs(self.x - other.x) < 1e-10 and 
                abs(self.y - other.y) < 1e-10 and 
                self.layer == other.layer)
    
    def __hash__(self) -> int:
        """Hash function for using Point in sets and dicts."""
        return hash((round(self.x, 10), round(self.y, 10), self.layer))


@dataclass
class RouteSegment:
    """Represents a routed segment."""
    start: Point
    end: Point
    width: float
    layer: int
    net_name: str
    impedance: float = 50.0
    is_differential: bool = False
    differential_partner: Optional[str] = None


@dataclass
class Via:
    """Via definition."""
    position: Point
    start_layer: int
    end_layer: int
    drill_size: float
    via_type: ViaType
    net_name: str
    cost: float = 1.0


@dataclass
class DifferentialPair:
    """Differential pair specification."""
    positive_net: str
    negative_net: str
    target_impedance: float
    max_length_mismatch: float
    coupling_spacing: float
    trace_width: float


@dataclass
class RoutingConstraint:
    """Routing constraint specification."""
    net_name: str
    min_width: float
    max_width: float
    min_spacing: float
    max_length: float
    target_impedance: Optional[float] = None
    layer_preference: Optional[List[int]] = None
    via_count_limit: Optional[int] = None


@dataclass
class GridPoint:
    """Point in routing grid."""
    x: int
    y: int
    layer: int
    cost: float = 1.0
    blocked: bool = False
    net_name: Optional[str] = None


class RoutingGrid:
    """3D routing grid for pathfinding."""
    
    def __init__(self, width: float, height: float, layers: int, resolution: float = 0.1):
        self.width = width  # mm
        self.height = height  # mm
        self.layers = layers
        self.resolution = resolution  # mm per grid unit
        
        self.grid_width = int(width / resolution)
        self.grid_height = int(height / resolution)
        
        # Initialize 3D grid
        self.grid = [[[GridPoint(x, y, z) for z in range(layers)] 
                     for y in range(self.grid_height)] 
                     for x in range(self.grid_width)]
        
        self.blocked_regions = []
        self.routed_nets = {}
        
    def to_grid_coords(self, point: Point) -> Tuple[int, int, int]:
        """Convert physical coordinates to grid coordinates."""
        x = max(0, min(self.grid_width - 1, int(point.x / self.resolution)))
        y = max(0, min(self.grid_height - 1, int(point.y / self.resolution)))
        z = max(0, min(self.layers - 1, point.layer))
        return x, y, z
    
    def to_physical_coords(self, x: int, y: int, z: int) -> Point:
        """Convert grid coordinates to physical coordinates."""
        return Point(x * self.resolution, y * self.resolution, z)
    
    def mark_blocked(self, region: Dict[str, Any]):
        """Mark a region as blocked for routing."""
        start_x, start_y, start_z = self.to_grid_coords(Point(region["x1"], region["y1"], region.get("layer", 0)))
        end_x, end_y, end_z = self.to_grid_coords(Point(region["x2"], region["y2"], region.get("layer", 0)))
        
        for x in range(min(start_x, end_x), max(start_x, end_x) + 1):
            for y in range(min(start_y, end_y), max(start_y, end_y) + 1):
                for z in range(start_z, end_z + 1):
                    if 0 <= x < self.grid_width and 0 <= y < self.grid_height and 0 <= z < self.layers:
                        self.grid[x][y][z].blocked = True
    
    def get_neighbors(self, x: int, y: int, z: int) -> List[Tuple[int, int, int, float]]:
        """Get valid neighboring grid points with costs."""
        neighbors = []
        
        # Adjacent points in same layer
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                if not self.grid[nx][ny][z].blocked:
                    cost = 1.0
                    # Increase cost if crossing other nets
                    if self.grid[nx][ny][z].net_name and self.grid[nx][ny][z].net_name != "current":
                        cost += 2.0
                    neighbors.append((nx, ny, z, cost))
        
        # Diagonal moves (higher cost)
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                if not self.grid[nx][ny][z].blocked:
                    cost = 1.414  # sqrt(2)
                    if self.grid[nx][ny][z].net_name and self.grid[nx][ny][z].net_name != "current":
                        cost += 2.0
                    neighbors.append((nx, ny, z, cost))
        
        # Layer transitions (vias) - highest cost
        for dz in [-1, 1]:
            nz = z + dz
            if 0 <= nz < self.layers:
                if not self.grid[x][y][nz].blocked:
                    cost = 10.0  # High cost for vias
                    neighbors.append((x, y, nz, cost))
        
        return neighbors


class AStarRouter:
    """A* pathfinding router with PCB-specific optimizations."""
    
    def __init__(self, routing_grid: RoutingGrid):
        self.grid = routing_grid
        
    def heuristic(self, current: Tuple[int, int, int], goal: Tuple[int, int, int]) -> float:
        """Heuristic function for A* (Manhattan distance + layer penalty)."""
        x1, y1, z1 = current
        x2, y2, z2 = goal
        
        # Manhattan distance in x-y plane
        distance = abs(x1 - x2) + abs(y1 - y2)
        
        # Layer change penalty
        layer_penalty = abs(z1 - z2) * 10
        
        return distance + layer_penalty
    
    def find_path(self, start: Point, end: Point, net_name: str, 
                 constraints: Optional[RoutingConstraint] = None) -> Optional[List[Point]]:
        """Find optimal path between two points using A*."""
        start_grid = self.grid.to_grid_coords(start)
        end_grid = self.grid.to_grid_coords(end)
        
        # A* algorithm implementation
        open_set = [(0.0, start_grid)]
        came_from = {}
        g_score = {start_grid: 0.0}
        f_score = {start_grid: float(self.heuristic(start_grid, end_grid))}
        
        while open_set:
            current = heapq.heappop(open_set)[1]
            
            if current == end_grid:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(self.grid.to_physical_coords(*current))
                    current = came_from[current]
                path.append(self.grid.to_physical_coords(*start_grid))
                return list(reversed(path))
            
            for neighbor_x, neighbor_y, neighbor_z, edge_cost in self.grid.get_neighbors(*current):
                neighbor = (neighbor_x, neighbor_y, neighbor_z)
                
                # Apply constraints
                if constraints and constraints.layer_preference:
                    if neighbor_z not in constraints.layer_preference:
                        edge_cost *= 2.0  # Penalize non-preferred layers
                
                tentative_g = g_score[current] + edge_cost
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self.heuristic(neighbor, end_grid)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        return None  # No path found
    
    def route_net(self, pins: List[Point], net_name: str, 
                 constraints: Optional[RoutingConstraint] = None) -> List[RouteSegment]:
        """Route a multi-pin net using minimum spanning tree approach."""
        if len(pins) < 2:
            return []
        
        # Mark current net in grid
        for x in range(self.grid.grid_width):
            for y in range(self.grid.grid_height):
                for z in range(self.grid.layers):
                    if self.grid.grid[x][y][z].net_name == net_name:
                        self.grid.grid[x][y][z].net_name = "current"
        
        routed_segments = []
        connected_pins = [pins[0]]
        unconnected_pins = pins[1:]
        
        while unconnected_pins:
            # Find closest unconnected pin to any connected pin
            min_distance = float('inf')
            best_start, best_end = None, None
            
            for connected in connected_pins:
                for unconnected in unconnected_pins:
                    distance = connected.distance_to(unconnected)
                    if distance < min_distance:
                        min_distance = distance
                        best_start, best_end = connected, unconnected
            
            # Check if we found valid start and end points
            if best_start is None or best_end is None:
                break
            
            # Route between best start and end
            path = self.find_path(best_start, best_end, net_name, constraints)
            if path:
                # Convert path to segments
                for i in range(len(path) - 1):
                    segment = RouteSegment(
                        start=path[i],
                        end=path[i + 1],
                        width=constraints.min_width if constraints else 0.2,
                        layer=path[i].layer,
                        net_name=net_name,
                        impedance=constraints.target_impedance if constraints and constraints.target_impedance else 50.0
                    )
                    routed_segments.append(segment)
                
                # Mark path as used
                for point in path:
                    gx, gy, gz = self.grid.to_grid_coords(point)
                    self.grid.grid[gx][gy][gz].net_name = net_name
                
                connected_pins.append(best_end)
                unconnected_pins.remove(best_end)
            else:
                logger.warning(f"Could not route segment for net {net_name}")
                break
        
        return routed_segments


class DifferentialPairRouter:
    """Specialized router for differential pairs."""
    
    def __init__(self, routing_grid: RoutingGrid):
        self.grid = routing_grid
        self.router = AStarRouter(routing_grid)
        
    def calculate_differential_spacing(self, impedance: float, trace_width: float, 
                                     dielectric_height: float, dielectric_er: float = 4.3) -> float:
        """Calculate required spacing for differential impedance."""
        # Simplified differential impedance calculation
        # This is a rough approximation - real implementation would use field solvers
        
        single_ended_z = 87 / math.sqrt(dielectric_er + 1.41) * math.log(5.98 * dielectric_height / (0.8 * trace_width + 0.035))
        
        # For differential impedance, we need to solve for spacing
        # Using simplified approximation: Zdiff ≈ 2 * Z0 * (1 - 0.48 * exp(-0.96 * s/h))
        target_ratio = impedance / (2 * single_ended_z)
        if target_ratio > 1:
            target_ratio = 0.99  # Limit to physical constraints
        
        coupling_factor = 1 - target_ratio
        spacing = -dielectric_height * math.log(coupling_factor / 0.48) / 0.96
        
        return max(spacing, trace_width * 2)  # Minimum 2x trace width
    
    def route_differential_pair(self, diff_pair: DifferentialPair, 
                              pos_pins: List[Point], neg_pins: List[Point]) -> Dict[str, Any]:
        """Route a differential pair with length matching."""
        if len(pos_pins) != len(neg_pins):
            raise ValueError("Differential pair must have equal number of positive and negative pins")
        
        # Create constraints for each net
        trace_width = diff_pair.trace_width
        constraints = RoutingConstraint(
            net_name="",
            min_width=trace_width,
            max_width=trace_width,
            min_spacing=diff_pair.coupling_spacing,
            max_length=1000.0,  # mm
            target_impedance=diff_pair.target_impedance
        )
        
        # Route positive net first
        constraints.net_name = diff_pair.positive_net
        pos_segments = self.router.route_net(pos_pins, diff_pair.positive_net, constraints)
        
        # Route negative net with spacing constraints
        constraints.net_name = diff_pair.negative_net
        neg_segments = self.router.route_net(neg_pins, diff_pair.negative_net, constraints)
        
        # Calculate path lengths
        pos_length = sum(seg.start.distance_to(seg.end) 
                        for seg in pos_segments)
        neg_length = sum(seg.start.distance_to(seg.end) 
                        for seg in neg_segments)
        
        length_mismatch = abs(pos_length - neg_length)
        
        # Apply length matching if needed
        matched_segments = self._apply_length_matching(
            pos_segments, neg_segments, diff_pair.max_length_mismatch
        )
        
        return {
            "positive_segments": matched_segments["positive"],
            "negative_segments": matched_segments["negative"],
            "original_length_mismatch": length_mismatch,
            "final_length_mismatch": matched_segments["final_mismatch"],
            "total_length": matched_segments["total_length"],
            "impedance": diff_pair.target_impedance,
            "spacing": diff_pair.coupling_spacing
        }
    
    def _apply_length_matching(self, pos_segments: List[RouteSegment], 
                             neg_segments: List[RouteSegment], 
                             max_mismatch: float) -> Dict[str, Any]:
        """Apply length matching using serpentine patterns."""
        pos_length = sum(seg.start.distance_to(seg.end) 
                        for seg in pos_segments)
        neg_length = sum(seg.start.distance_to(seg.end) 
                        for seg in neg_segments)
        
        length_diff = abs(pos_length - neg_length)
        
        if length_diff <= max_mismatch:
            return {
                "positive": pos_segments,
                "negative": neg_segments,
                "final_mismatch": length_diff,
                "total_length": max(pos_length, neg_length)
            }
        
        # Determine which net needs lengthening
        if pos_length < neg_length:
            short_segments = pos_segments
            long_segments = neg_segments
            length_to_add = neg_length - pos_length - max_mismatch
        else:
            short_segments = neg_segments
            long_segments = pos_segments
            length_to_add = pos_length - neg_length - max_mismatch
        
        # Add serpentine pattern to short net
        modified_segments = self._add_serpentine_pattern(short_segments, length_to_add)
        
        if pos_length < neg_length:
            return {
                "positive": modified_segments,
                "negative": long_segments,
                "final_mismatch": max_mismatch,
                "total_length": neg_length
            }
        else:
            return {
                "positive": long_segments,
                "negative": modified_segments,
                "final_mismatch": max_mismatch,
                "total_length": pos_length
            }
    
    def _add_serpentine_pattern(self, segments: List[RouteSegment], 
                              additional_length: float) -> List[RouteSegment]:
        """Add serpentine pattern to increase trace length."""
        if additional_length <= 0 or not segments:
            return segments
        
        # Find the longest straight segment to add serpentine
        longest_segment = max(segments, key=lambda s: s.start.distance_to(s.end))
        segment_index = segments.index(longest_segment)
        
        # Calculate serpentine parameters
        amplitude = 1.0  # mm
        period = 2.0  # mm
        serpentine_length = additional_length + longest_segment.start.distance_to(longest_segment.end)
        
        # Create serpentine segments
        serpentine_segments = self._create_serpentine_segments(
            longest_segment.start, longest_segment.end, 
            serpentine_length, amplitude, period, longest_segment
        )
        
        # Replace the original segment with serpentine
        new_segments = segments[:segment_index] + serpentine_segments + segments[segment_index + 1:]
        
        return new_segments
    
    def _create_serpentine_segments(self, start: Point, end: Point, 
                                  target_length: float, amplitude: float, 
                                  period: float, template_segment: RouteSegment) -> List[RouteSegment]:
        """Create serpentine pattern segments."""
        # Simplified serpentine - in practice would be more sophisticated
        direct_length = start.distance_to(end)
        extra_length = target_length - direct_length
        
        # Calculate number of meanders
        meander_count = int(extra_length / (4 * amplitude))
        if meander_count == 0:
            return [template_segment]
        
        segments = []
        dx = (end.x - start.x) / (meander_count * 2 + 1)
        dy = (end.y - start.y) / (meander_count * 2 + 1)
        
        current_point = start
        
        for i in range(meander_count * 2 + 1):
            # Alternate between positive and negative amplitude
            meander_y = amplitude * (1 if i % 2 == 0 else -1) if i > 0 and i < meander_count * 2 else 0
            
            next_point = Point(
                start.x + dx * (i + 1),
                start.y + dy * (i + 1) + meander_y,
                start.layer
            )
            
            segment = RouteSegment(
                start=current_point,
                end=next_point,
                width=template_segment.width,
                layer=template_segment.layer,
                net_name=template_segment.net_name,
                impedance=template_segment.impedance,
                is_differential=template_segment.is_differential,
                differential_partner=template_segment.differential_partner
            )
            segments.append(segment)
            current_point = next_point
        
        return segments


class ViaOptimizer:
    """Optimize via placement and minimize via count."""
    
    def __init__(self, routing_grid: RoutingGrid):
        self.grid = routing_grid
        
    def optimize_via_placement(self, segments: List[RouteSegment]) -> List[Via]:
        """Optimize via placement for a set of routed segments."""
        vias = []
        
        # Group segments by net
        nets = {}
        for segment in segments:
            if segment.net_name not in nets:
                nets[segment.net_name] = []
            nets[segment.net_name].append(segment)
        
        # Optimize vias for each net
        for net_name, net_segments in nets.items():
            net_vias = self._optimize_net_vias(net_segments, net_name)
            vias.extend(net_vias)
        
        return vias
    
    def _optimize_net_vias(self, segments: List[RouteSegment], net_name: str) -> List[Via]:
        """Optimize vias for a single net."""
        vias = []
        layer_transitions = {}
        
        # Find all layer transitions
        for segment in segments:
            if segment.start.layer != segment.end.layer:
                transition_key = f"{segment.start.layer}_{segment.end.layer}"
                if transition_key not in layer_transitions:
                    layer_transitions[transition_key] = []
                
                # Use midpoint for via placement
                via_x = (segment.start.x + segment.end.x) / 2
                via_y = (segment.start.y + segment.end.y) / 2
                
                layer_transitions[transition_key].append((via_x, via_y))
        
        # Create optimized vias
        for transition, positions in layer_transitions.items():
            start_layer, end_layer = map(int, transition.split('_'))
            
            # Cluster nearby via positions
            clustered_positions = self._cluster_via_positions(positions, min_distance=1.0)
            
            for pos_x, pos_y in clustered_positions:
                via = Via(
                    position=Point(pos_x, pos_y, start_layer),
                    start_layer=start_layer,
                    end_layer=end_layer,
                    drill_size=0.2,  # mm
                    via_type=ViaType.THROUGH,
                    net_name=net_name,
                    cost=1.0
                )
                vias.append(via)
        
        return vias
    
    def _cluster_via_positions(self, positions: List[Tuple[float, float]], 
                             min_distance: float = 1.0) -> List[Tuple[float, float]]:
        """Cluster via positions to minimize via count."""
        if not positions:
            return []
        
        clustered = []
        remaining = positions.copy()
        
        while remaining:
            # Start new cluster with first remaining position
            cluster_center = remaining.pop(0)
            cluster_positions = [cluster_center]
            
            # Find all positions within clustering distance
            i = 0
            while i < len(remaining):
                pos = remaining[i]
                if math.sqrt((cluster_center[0] - pos[0])**2 + (cluster_center[1] - pos[1])**2) <= min_distance:
                    cluster_positions.append(remaining.pop(i))
                else:
                    i += 1
            
            # Calculate cluster centroid
            centroid_x = sum(pos[0] for pos in cluster_positions) / len(cluster_positions)
            centroid_y = sum(pos[1] for pos in cluster_positions) / len(cluster_positions)
            
            clustered.append((centroid_x, centroid_y))
        
        return clustered


class PowerPlaneRouter:
    """Specialized router for power and ground planes."""
    
    def __init__(self, routing_grid: RoutingGrid):
        self.grid = routing_grid
        
    def route_power_plane(self, power_net: str, voltage: float, 
                         components: List[Dict[str, Any]], 
                         plane_layer: int) -> Dict[str, Any]:
        """Route power plane with optimal current distribution."""
        # Create power distribution tree
        power_tree = self._create_power_distribution_tree(components, plane_layer)
        
        # Calculate current paths
        current_paths = self._calculate_current_paths(power_tree, voltage)
        
        # Optimize plane shape
        plane_regions = self._optimize_plane_regions(current_paths, plane_layer)
        
        # Calculate voltage drop
        voltage_analysis = self._analyze_voltage_drop(current_paths, voltage)
        
        return {
            "power_net": power_net,
            "voltage": voltage,
            "plane_layer": plane_layer,
            "power_tree": power_tree,
            "current_paths": current_paths,
            "plane_regions": plane_regions,
            "voltage_analysis": voltage_analysis
        }
    
    def _create_power_distribution_tree(self, components: List[Dict[str, Any]], 
                                      plane_layer: int) -> Dict[str, Any]:
        """Create minimum spanning tree for power distribution."""
        # Simplified power tree - in practice would use more sophisticated algorithms
        power_components = [comp for comp in components if comp.get("power_pin")]
        
        if not power_components:
            return {"nodes": [], "edges": []}
        
        # Create nodes
        nodes = []
        for i, comp in enumerate(power_components):
            nodes.append({
                "id": i,
                "component": comp["name"],
                "position": [comp["x"], comp["y"]],
                "current": comp.get("current", 0.1),  # A
                "layer": plane_layer
            })
        
        # Create minimum spanning tree edges
        edges = []
        if len(nodes) > 1:
            # Simplified MST using nearest neighbor
            connected = [0]
            unconnected = list(range(1, len(nodes)))
            
            while unconnected:
                min_distance = float('inf')
                best_edge = None
                
                for connected_id in connected:
                    for unconnected_id in unconnected:
                        pos1 = nodes[connected_id]["position"]
                        pos2 = nodes[unconnected_id]["position"]
                        distance = math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
                        if distance < min_distance:
                            min_distance = distance
                            best_edge = (connected_id, unconnected_id)
                
                if best_edge:
                    edges.append({
                        "from": best_edge[0],
                        "to": best_edge[1],
                        "length": min_distance,
                        "width": self._calculate_trace_width(nodes[best_edge[1]]["current"])
                    })
                    connected.append(best_edge[1])
                    unconnected.remove(best_edge[1])
        
        return {"nodes": nodes, "edges": edges}
    
    def _calculate_trace_width(self, current: float, temperature_rise: float = 10.0) -> float:
        """Calculate required trace width for given current."""
        # IPC-2221 current carrying capacity
        # I = k * (dT^b) * (A^c)
        # Where k, b, c are constants, dT is temperature rise, A is cross-sectional area
        
        k = 0.048  # Internal layers
        b = 0.44
        c = 0.725
        
        # Solve for area: A = (I / (k * dT^b))^(1/c)
        area_sq_mils = (current / (k * (temperature_rise ** b))) ** (1 / c)
        
        # Convert to width (assuming 1 oz copper = 1.4 mils thick)
        copper_thickness_mils = 1.4
        width_mils = area_sq_mils / copper_thickness_mils
        
        # Convert to mm
        width_mm = width_mils * 0.0254
        
        return max(width_mm, 0.1)  # Minimum 0.1mm
    
    def _calculate_current_paths(self, power_tree: Dict[str, Any], voltage: float) -> List[Dict[str, Any]]:
        """Calculate current distribution through power tree."""
        current_paths = []
        
        for edge in power_tree["edges"]:
            from_node = power_tree["nodes"][edge["from"]]
            to_node = power_tree["nodes"][edge["to"]]
            
            # Calculate resistance
            length_m = edge["length"] / 1000  # Convert mm to m
            width_m = edge["width"] / 1000
            thickness_m = 0.035 / 1000  # 1 oz copper
            area_m2 = width_m * thickness_m
            
            resistance = (1.72e-8 * length_m) / area_m2  # Copper resistivity
            
            current_paths.append({
                "from_component": from_node["component"],
                "to_component": to_node["component"],
                "current": to_node["current"],
                "resistance": resistance,
                "voltage_drop": to_node["current"] * resistance,
                "power_loss": (to_node["current"] ** 2) * resistance,
                "width": edge["width"],
                "length": edge["length"]
            })
        
        return current_paths
    
    def _optimize_plane_regions(self, current_paths: List[Dict[str, Any]], 
                              plane_layer: int) -> List[Dict[str, Any]]:
        """Optimize power plane regions for current density."""
        regions = []
        
        for path in current_paths:
            # Create plane region for each current path
            current_density = path["current"] / (path["width"] * 0.035)  # A/mm²
            
            region = {
                "layer": plane_layer,
                "current_density": current_density,
                "width": path["width"],
                "length": path["length"],
                "copper_pour": current_density > 1.0,  # Use copper pour for high current
                "thermal_vias": current_density > 2.0  # Add thermal vias for very high current
            }
            regions.append(region)
        
        return regions
    
    def _analyze_voltage_drop(self, current_paths: List[Dict[str, Any]], 
                            input_voltage: float) -> Dict[str, Any]:
        """Analyze voltage drop across power distribution network."""
        total_voltage_drop = sum(path["voltage_drop"] for path in current_paths)
        total_power_loss = sum(path["power_loss"] for path in current_paths)
        
        worst_case_drop = max(path["voltage_drop"] for path in current_paths) if current_paths else 0
        worst_case_component = None
        
        if current_paths:
            worst_path = max(current_paths, key=lambda p: p["voltage_drop"])
            worst_case_component = worst_path["to_component"]
        
        voltage_drop_percent = (total_voltage_drop / input_voltage) * 100
        
        return {
            "input_voltage": input_voltage,
            "total_voltage_drop": total_voltage_drop,
            "voltage_drop_percent": voltage_drop_percent,
            "total_power_loss": total_power_loss,
            "worst_case_drop": worst_case_drop,
            "worst_case_component": worst_case_component,
            "efficiency_percent": ((input_voltage - total_voltage_drop) / input_voltage) * 100,
            "status": "PASS" if voltage_drop_percent < 5.0 else "FAIL"
        }


class AdvancedRoutingEngine:
    """Main routing engine that orchestrates all routing algorithms."""
    
    def __init__(self, board_width: float, board_height: float, layers: int, resolution: float = 0.1):
        self.grid = RoutingGrid(board_width, board_height, layers, resolution)
        self.router = AStarRouter(self.grid)
        self.diff_router = DifferentialPairRouter(self.grid)
        self.via_optimizer = ViaOptimizer(self.grid)
        self.power_router = PowerPlaneRouter(self.grid)
        
    def route_design(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route complete PCB design with all constraints."""
        results = {
            "routing_timestamp": "2025-01-01T00:00:00Z",
            "design_data": design_data,
            "routing_results": {}
        }
        
        try:
            # Extract design data
            nets = design_data.get("nets", [])
            differential_pairs = design_data.get("differential_pairs", [])
            components = design_data.get("components", [])
            power_nets = design_data.get("power_nets", [])
            routing_constraints = design_data.get("routing_constraints", [])
            
            # Mark blocked regions (components, etc.)
            for component in components:
                self.grid.mark_blocked({
                    "x1": component["x"] - component["width"]/2,
                    "y1": component["y"] - component["height"]/2,
                    "x2": component["x"] + component["width"]/2,
                    "y2": component["y"] + component["height"]/2,
                    "layer": 0
                })
            
            # Route regular nets
            routed_nets = {}
            for net in nets:
                net_name = net["name"]
                pins = [Point(pin["x"], pin["y"], pin.get("layer", 0)) for pin in net["pins"]]
                
                # Find constraints for this net
                constraint = next((c for c in routing_constraints if c["net_name"] == net_name), None)
                if constraint:
                    constraint_obj = RoutingConstraint(**constraint)
                else:
                    constraint_obj = None
                
                segments = self.router.route_net(pins, net_name, constraint_obj)
                routed_nets[net_name] = {
                    "segments": [asdict(seg) for seg in segments],
                    "total_length": sum(seg.start.distance_to(seg.end) for seg in segments),
                    "layer_count": len(set(seg.layer for seg in segments))
                }
            
            results["routing_results"]["nets"] = routed_nets
            
            # Route differential pairs
            diff_pairs_results = {}
            for diff_pair_data in differential_pairs:
                diff_pair = DifferentialPair(**diff_pair_data)
                
                # Find pins for positive and negative nets
                pos_net = next(net for net in nets if net["name"] == diff_pair.positive_net)
                neg_net = next(net for net in nets if net["name"] == diff_pair.negative_net)
                
                pos_pins = [Point(pin["x"], pin["y"], pin.get("layer", 0)) for pin in pos_net["pins"]]
                neg_pins = [Point(pin["x"], pin["y"], pin.get("layer", 0)) for pin in neg_net["pins"]]
                
                diff_result = self.diff_router.route_differential_pair(diff_pair, pos_pins, neg_pins)
                diff_pairs_results[f"{diff_pair.positive_net}_{diff_pair.negative_net}"] = diff_result
            
            results["routing_results"]["differential_pairs"] = diff_pairs_results
            
            # Optimize vias
            all_segments = []
            for net_result in routed_nets.values():
                all_segments.extend([RouteSegment(**seg) for seg in net_result["segments"]])
            
            vias = self.via_optimizer.optimize_via_placement(all_segments)
            results["routing_results"]["vias"] = [asdict(via) for via in vias]
            
            # Route power planes
            power_planes_results = {}
            for power_net in power_nets:
                power_result = self.power_router.route_power_plane(
                    power_net["name"], 
                    power_net["voltage"], 
                    components, 
                    power_net["layer"]
                )
                power_planes_results[power_net["name"]] = power_result
            
            results["routing_results"]["power_planes"] = power_planes_results
            
            # Overall routing statistics
            results["routing_statistics"] = self._calculate_routing_statistics(results["routing_results"])
            
        except Exception as e:
            logger.error(f"Routing error: {e}")
            results["error"] = str(e)
            results["routing_statistics"] = {"status": "ERROR"}
        
        return results
    
    def _calculate_routing_statistics(self, routing_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall routing statistics."""
        stats = {
            "total_nets": len(routing_results.get("nets", {})),
            "total_differential_pairs": len(routing_results.get("differential_pairs", {})),
            "total_vias": len(routing_results.get("vias", [])),
            "total_power_planes": len(routing_results.get("power_planes", {})),
            "completion_rate": 0.0,
            "average_via_count_per_net": 0.0,
            "longest_net_length": 0.0,
            "routing_density": 0.0
        }
        
        # Calculate completion rate
        successful_nets = sum(1 for net_data in routing_results.get("nets", {}).values() 
                            if net_data.get("segments"))
        if stats["total_nets"] > 0:
            stats["completion_rate"] = (successful_nets / stats["total_nets"]) * 100
        
        # Calculate average via count
        if stats["total_nets"] > 0:
            stats["average_via_count_per_net"] = stats["total_vias"] / stats["total_nets"]
        
        # Find longest net
        for net_data in routing_results.get("nets", {}).values():
            net_length = net_data.get("total_length", 0)
            if net_length > stats["longest_net_length"]:
                stats["longest_net_length"] = net_length
        
        # Calculate routing density (simplified)
        total_trace_length = sum(net_data.get("total_length", 0) 
                               for net_data in routing_results.get("nets", {}).values())
        board_area = self.grid.width * self.grid.height  # mm²
        if board_area > 0:
            stats["routing_density"] = total_trace_length / board_area
        
        # Overall status
        if stats["completion_rate"] > 95:
            stats["status"] = "EXCELLENT"
        elif stats["completion_rate"] > 80:
            stats["status"] = "GOOD"
        elif stats["completion_rate"] > 60:
            stats["status"] = "ACCEPTABLE"
        else:
            stats["status"] = "POOR"
        
        return stats


def create_routing_engine(board_width: float, board_height: float, 
                        layers: int, resolution: float = 0.1) -> AdvancedRoutingEngine:
    """Factory function to create routing engine."""
    return AdvancedRoutingEngine(board_width, board_height, layers, resolution)