#!/usr/bin/env python3
"""
PCB layout engine for automated component placement and routing.
Provides algorithms for optimizing component placement and trace routing.
"""

import math
import random
import numpy as np
from typing import Dict, List, Tuple, Set, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass

# Try to import KiCad modules
try:
    import pcbnew
    from pcbnew import (
        BOARD, FOOTPRINT, PAD, PCB_TRACK, PCB_VIA, VECTOR2I, 
        PCB_SHAPE, IU_PER_MM, NETINFO_ITEM
    )
    KICAD_AVAILABLE = True
except ImportError:
    KICAD_AVAILABLE = False
    print("Warning: KiCad Python API not available. Layout engine will use simulation mode.")

# Import our KiCad helper functions
import kicad_helpers as kh

# Component placement constraint types
class PlacementConstraint(Enum):
    """Types of placement constraints for components."""
    FIXED_POSITION = 1  # Component must be at specific coordinates
    REGION = 2          # Component must be in a specific region
    ALIGNMENT = 3       # Component must align with another component
    PROXIMITY = 4       # Component must be near another component
    SEPARATION = 5      # Component must be separated from another component
    THERMAL = 6         # Component must be placed for thermal considerations
    ORIENTATION = 7     # Component must have specific orientation

# Routing constraint types
class RoutingConstraint(Enum):
    """Types of routing constraints for traces."""
    LENGTH_MATCHING = 1  # Traces must have matched lengths
    IMPEDANCE = 2        # Traces must maintain specific impedance
    CLEARANCE = 3        # Traces must maintain minimum clearance
    LAYER = 4            # Traces must be on specific layer
    PARALLEL = 5         # Traces must be parallel
    NO_VIAS = 6          # Traces must not use vias
    DIFFERENTIAL = 7     # Traces are differential pair

@dataclass
class ComponentPlacement:
    """Represents a component's placement on the PCB."""
    component_id: str
    reference: str
    footprint_name: str
    position: Tuple[float, float]  # x, y in mm
    rotation: float  # degrees
    layer: str  # "top" or "bottom"
    fixed: bool = False  # If True, don't move during optimization

@dataclass
class TraceSegment:
    """Represents a segment of a trace on the PCB."""
    net_name: str
    start_point: Tuple[float, float]  # x, y in mm
    end_point: Tuple[float, float]    # x, y in mm
    width: float  # mm
    layer: str
    via_end: bool = False  # True if this segment ends with a via

@dataclass
class NetConnection:
    """Represents a net connection between components."""
    net_name: str
    source_component: str  # reference designator
    source_pad: str        # pad name/number
    target_component: str  # reference designator
    target_pad: str        # pad name/number
    constraints: List[RoutingConstraint] = None

@dataclass
class BoardOutline:
    """Represents the PCB board outline."""
    points: List[Tuple[float, float]]  # List of x, y points in mm
    
    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Get the bounding box of the outline (min_x, min_y, max_x, max_y)."""
        min_x = min(p[0] for p in self.points)
        min_y = min(p[1] for p in self.points)
        max_x = max(p[0] for p in self.points)
        max_y = max(p[1] for p in self.points)
        return (min_x, min_y, max_x, max_y)
    
    @property
    def width(self) -> float:
        """Get the width of the board."""
        min_x, _, max_x, _ = self.bounds
        return max_x - min_x
    
    @property
    def height(self) -> float:
        """Get the height of the board."""
        _, min_y, _, max_y = self.bounds
        return max_y - min_y
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get the center point of the board."""
        min_x, min_y, max_x, max_y = self.bounds
        return ((max_x + min_x) / 2, (max_y + min_y) / 2)

class PCBLayoutEngine:
    """Engine for automated PCB component placement and routing."""
    
    def __init__(self, board=None):
        """
        Initialize the PCB layout engine.
        
        Args:
            board: KiCad board object (optional)
        """
        self.board = board
        self.components: List[ComponentPlacement] = []
        self.traces: List[TraceSegment] = []
        self.nets: List[NetConnection] = []
        self.board_outline: Optional[BoardOutline] = None
        self.grid_resolution: float = 0.1  # mm
        self.min_track_width: float = 0.2  # mm
        self.min_clearance: float = 0.2    # mm
        self.via_diameter: float = 0.8     # mm
        self.via_drill: float = 0.4        # mm
        self.layer_count: int = 2          # Default to 2-layer board
        
        # Grid for routing
        self.grid: Optional[np.ndarray] = None
        
        # Keep track of component placements
        self.placement_cache: Dict[str, Tuple[float, float, float]] = {}
        
        # Setup with board if provided
        if self.board and KICAD_AVAILABLE:
            self._import_from_kicad_board()
    
    def _import_from_kicad_board(self):
        """Import board data from KiCad board object."""
        if not KICAD_AVAILABLE or not self.board:
            return
        
        # Get design settings
        design_settings = self.board.GetDesignSettings()
        self.min_track_width = kh.kicad_units_to_mm(design_settings.m_TrackMinWidth)
        self.min_clearance = kh.kicad_units_to_mm(design_settings.m_MinClearance)
        self.layer_count = design_settings.GetCopperLayerCount()
        
        # Import board outline
        board_outline_points = []
        for drawing in self.board.GetDrawings():
            if drawing.GetLayer() == pcbnew.Edge_Cuts:
                if drawing.GetShape() == pcbnew.SHAPE_T_RECT:
                    # Rectangle
                    start = drawing.GetStart()
                    end = drawing.GetEnd()
                    start_x = kh.kicad_units_to_mm(start.x)
                    start_y = kh.kicad_units_to_mm(start.y)
                    end_x = kh.kicad_units_to_mm(end.x)
                    end_y = kh.kicad_units_to_mm(end.y)
                    
                    board_outline_points.extend([
                        (start_x, start_y),
                        (end_x, start_y),
                        (end_x, end_y),
                        (start_x, end_y),
                        (start_x, start_y)  # Close the loop
                    ])
                    break
                elif drawing.GetShape() == pcbnew.SHAPE_T_POLY:
                    # Polygon
                    poly = drawing.GetPolyShape()
                    for i in range(poly.OutlineCount()):
                        outline = poly.Outline(i)
                        for j in range(outline.PointCount()):
                            point = outline.Point(j)
                            x = kh.kicad_units_to_mm(point.x)
                            y = kh.kicad_units_to_mm(point.y)
                            board_outline_points.append((x, y))
                        
                        # Close the loop
                        first_point = outline.Point(0)
                        x = kh.kicad_units_to_mm(first_point.x)
                        y = kh.kicad_units_to_mm(first_point.y)
                        board_outline_points.append((x, y))
        
        if board_outline_points:
            self.board_outline = BoardOutline(points=board_outline_points)
        
        # Import components (footprints)
        for footprint in self.board.GetFootprints():
            ref = footprint.GetReference()
            name = footprint.GetFPID().GetLibItemName()
            pos = footprint.GetPosition()
            x = kh.kicad_units_to_mm(pos.x)
            y = kh.kicad_units_to_mm(pos.y)
            rotation = footprint.GetOrientation() / 10.0  # KiCad uses tenths of a degree
            
            layer = "top"
            if footprint.GetLayer() == pcbnew.B_Cu:
                layer = "bottom"
            
            component = ComponentPlacement(
                component_id=f"{ref}_{name}",
                reference=ref,
                footprint_name=name,
                position=(x, y),
                rotation=rotation,
                layer=layer,
                fixed=footprint.IsFixed()
            )
            
            self.components.append(component)
            self.placement_cache[ref] = (x, y, rotation)
        
        # Import nets and connections
        netinfo = self.board.GetNetInfo()
        for netcode in range(1, netinfo.GetNetCount()):
            net = netinfo.GetNetItem(netcode)
            net_name = net.GetNetname()
            
            # TODO: Extract net connections from the board
            # This is more complex and requires traversing connected items
    
    def _export_to_kicad_board(self) -> bool:
        """Export layout data to KiCad board object."""
        if not KICAD_AVAILABLE or not self.board:
            return False
        
        try:
            # Set board outline if defined
            if self.board_outline:
                # Remove old outline
                for drawing in list(self.board.GetDrawings()):
                    if drawing.GetLayer() == pcbnew.Edge_Cuts:
                        self.board.Remove(drawing)
                
                # Create new outline
                shape = PCB_SHAPE(self.board)
                shape.SetShape(pcbnew.SHAPE_T_POLY)
                shape.SetLayer(pcbnew.Edge_Cuts)
                poly = shape.GetPolyShape()
                
                outline = pcbnew.SHAPE_LINE_CHAIN()
                for point in self.board_outline.points:
                    x = kh.mm_to_kicad_units(point[0])
                    y = kh.mm_to_kicad_units(point[1])
                    outline.Append(VECTOR2I(x, y))
                
                poly.AddOutline(outline)
                self.board.Add(shape)
            
            # Update component placements
            for component in self.components:
                footprint = self.board.FindFootprintByReference(component.reference)
                if footprint:
                    # Update position
                    x = kh.mm_to_kicad_units(component.position[0])
                    y = kh.mm_to_kicad_units(component.position[1])
                    footprint.SetPosition(VECTOR2I(x, y))
                    
                    # Update rotation
                    footprint.SetOrientation(component.rotation * 10.0)
                    
                    # Update layer
                    if component.layer == "top":
                        footprint.SetLayer(pcbnew.F_Cu)
                    else:
                        footprint.SetLayer(pcbnew.B_Cu)
            
            # Create traces
            for trace in self.traces:
                # Get net info
                netinfo = self.board.GetNetInfo()
                net = netinfo.FindNet(trace.net_name)
                if not net:
                    # Create net if it doesn't exist
                    net = NETINFO_ITEM(self.board, trace.net_name)
                    netinfo.AppendNet(net)
                
                # Create track
                track = PCB_TRACK(self.board)
                
                # Set positions
                start_x = kh.mm_to_kicad_units(trace.start_point[0])
                start_y = kh.mm_to_kicad_units(trace.start_point[1])
                end_x = kh.mm_to_kicad_units(trace.end_point[0])
                end_y = kh.mm_to_kicad_units(trace.end_point[1])
                
                track.SetStart(VECTOR2I(start_x, start_y))
                track.SetEnd(VECTOR2I(end_x, end_y))
                
                # Set width and layer
                track.SetWidth(kh.mm_to_kicad_units(trace.width))
                if trace.layer == "F.Cu":
                    track.SetLayer(pcbnew.F_Cu)
                else:
                    track.SetLayer(pcbnew.B_Cu)
                
                # Set net
                track.SetNetCode(net.GetNetCode())
                
                # Add to board
                self.board.Add(track)
                
                # Add via if needed
                if trace.via_end:
                    via = PCB_VIA(self.board)
                    via.SetPosition(VECTOR2I(end_x, end_y))
                    via.SetWidth(kh.mm_to_kicad_units(self.via_diameter))
                    via.SetDrill(kh.mm_to_kicad_units(self.via_drill))
                    via.SetNetCode(net.GetNetCode())
                    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                    self.board.Add(via)
            
            return True
        
        except Exception as e:
            print(f"Error exporting to KiCad board: {e}")
            return False
    
    def set_board_outline(self, width: float, height: float) -> None:
        """
        Set a simple rectangular board outline.
        
        Args:
            width: Board width in mm
            height: Board height in mm
        """
        # Create a rectangular outline
        self.board_outline = BoardOutline(points=[
            (0, 0),
            (width, 0),
            (width, height),
            (0, height),
            (0, 0)  # Close the loop
        ])
        
        # Initialize routing grid
        self._initialize_grid()
    
    def _initialize_grid(self) -> None:
        """Initialize the routing grid based on board outline."""
        if not self.board_outline:
            return
        
        # Get board dimensions
        min_x, min_y, max_x, max_y = self.board_outline.bounds
        
        # Calculate grid size
        grid_width = int((max_x - min_x) / self.grid_resolution) + 1
        grid_height = int((max_y - min_y) / self.grid_resolution) + 1
        
        # Create grid for each layer
        self.grid = np.zeros((self.layer_count, grid_height, grid_width), dtype=np.int8)
        
        # Mark board outline on grid
        # This is a simple approximation - real implementation would be more precise
        for y in range(grid_height):
            for x in range(grid_width):
                real_x = min_x + x * self.grid_resolution
                real_y = min_y + y * self.grid_resolution
                
                if real_x <= min_x + self.grid_resolution or real_x >= max_x - self.grid_resolution or \
                   real_y <= min_y + self.grid_resolution or real_y >= max_y - self.grid_resolution:
                    # Mark cells near the edge as obstacles
                    for layer in range(self.layer_count):
                        self.grid[layer, y, x] = 1  # 1 = obstacle
    
    def add_component(self, component: ComponentPlacement) -> None:
        """
        Add a component to the layout.
        
        Args:
            component: Component placement information
        """
        self.components.append(component)
        
        # Update placement cache
        self.placement_cache[component.reference] = (
            component.position[0],
            component.position[1],
            component.rotation
        )
        
        # Update grid to mark component position as occupied
        self._update_grid_for_component(component)
    
    def _update_grid_for_component(self, component: ComponentPlacement) -> None:
        """
        Update the routing grid to mark a component's position.
        
        Args:
            component: Component placement information
        """
        if not self.grid or not self.board_outline:
            return
        
        # For a real implementation, this would use the actual footprint bounds
        # Here, we'll just use a simple approximation based on the reference
        
        # Determine component size (very rough approximation)
        width = 5.0  # mm
        height = 5.0  # mm
        
        if component.reference.startswith('R') or component.reference.startswith('C'):
            width = 2.0
            height = 1.2
        elif component.reference.startswith('U'):
            width = 10.0
            height = 10.0
        
        # Convert to grid coordinates
        min_x, min_y, _, _ = self.board_outline.bounds
        
        grid_x = int((component.position[0] - min_x) / self.grid_resolution)
        grid_y = int((component.position[1] - min_y) / self.grid_resolution)
        
        grid_width = int(width / self.grid_resolution)
        grid_height = int(height / self.grid_resolution)
        
        # Mark grid cells as occupied
        layer_index = 0 if component.layer == "top" else 1
        
        for y in range(max(0, grid_y - grid_height//2), 
                      min(self.grid.shape[1], grid_y + grid_height//2 + 1)):
            for x in range(max(0, grid_x - grid_width//2), 
                          min(self.grid.shape[2], grid_x + grid_width//2 + 1)):
                self.grid[layer_index, y, x] = 1  # 1 = obstacle
    
    def auto_place_components(self) -> bool:
        """
        Automatically place components on the board.
        Uses a simplified force-directed placement algorithm.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.board_outline or not self.components:
            return False
        
        # Get board dimensions
        min_x, min_y, max_x, max_y = self.board_outline.bounds
        width = max_x - min_x
        height = max_y - min_y
        
        # Filter out fixed components
        movable_components = [c for c in self.components if not c.fixed]
        fixed_components = [c for c in self.components if c.fixed]
        
        if not movable_components:
            return True  # Nothing to place
        
        # Initialize with random positions if not already placed
        for component in movable_components:
            if component.reference not in self.placement_cache:
                x = min_x + random.uniform(5, width - 5)
                y = min_y + random.uniform(5, height - 5)
                rotation = random.choice([0, 90, 180, 270])
                component.position = (x, y)
                component.rotation = rotation
        
        # Create net connections dictionary for faster lookup
        net_connections: Dict[str, List[str]] = {}
        for net in self.nets:
            if net.net_name not in net_connections:
                net_connections[net.net_name] = []
            
            net_connections[net.net_name].append(net.source_component)
            net_connections[net.net_name].append(net.target_component)
        
        # Optimize placement using simple force-directed algorithm
        iterations = 100
        cooling_factor = 0.95
        temperature = min(width, height) / 4
        
        for iteration in range(iterations):
            # Calculate forces for each component
            for i, component in enumerate(movable_components):
                # Initialize force
                force_x = 0.0
                force_y = 0.0
                
                # Repulsive forces from other components (avoid overlap)
                for other in self.components:
                    if component.reference == other.reference:
                        continue
                    
                    dx = component.position[0] - other.position[0]
                    dy = component.position[1] - other.position[1]
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance < 0.1:  # Avoid division by zero
                        distance = 0.1
                    
                    # Simple repulsive force
                    force = 100.0 / (distance * distance)
                    
                    # Apply force in the direction away from other component
                    force_x += force * (dx / distance)
                    force_y += force * (dy / distance)
                
                # Attractive forces from connected components (nets)
                for net_name, components in net_connections.items():
                    if component.reference in components:
                        # Find other components in this net
                        for other_ref in components:
                            if other_ref == component.reference:
                                continue
                            
                            # Find the other component
                            other = None
                            for c in self.components:
                                if c.reference == other_ref:
                                    other = c
                                    break
                            
                            if not other:
                                continue
                            
                            # Calculate attractive force
                            dx = other.position[0] - component.position[0]
                            dy = other.position[1] - component.position[1]
                            distance = math.sqrt(dx*dx + dy*dy)
                            
                            if distance < 0.1:  # Avoid division by zero
                                distance = 0.1
                            
                            # Simple attractive force
                            force = 0.05 * distance
                            
                            # Apply force in the direction toward other component
                            force_x += force * (dx / distance)
                            force_y += force * (dy / distance)
                
                # Attractive force to board center (to keep components on the board)
                center_x, center_y = self.board_outline.center
                dx = center_x - component.position[0]
                dy = center_y - component.position[1]
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > width / 4:  # Only apply when far from center
                    if distance < 0.1:  # Avoid division by zero
                        distance = 0.1
                    
                    force = 0.01 * distance
                    force_x += force * (dx / distance)
                    force_y += force * (dy / distance)
                
                # Update position based on forces
                delta_x = force_x * temperature
                delta_y = force_y * temperature
                
                new_x = component.position[0] + delta_x
                new_y = component.position[1] + delta_y
                
                # Constrain to board boundaries with margin
                margin = 2.0  # mm
                new_x = max(min_x + margin, min(max_x - margin, new_x))
                new_y = max(min_y + margin, min(max_y - margin, new_y))
                
                # Update component position
                component.position = (new_x, new_y)
                
                # Determine best orientation (simplistic approach)
                if iteration > iterations / 2:  # Only consider orientation in later iterations
                    # For now, just use a fixed orientation based on component type
                    if component.reference.startswith('R'):
                        component.rotation = 0.0
                    elif component.reference.startswith('C'):
                        component.rotation = 90.0
            
            # Cool down temperature
            temperature *= cooling_factor
        
        # Update placement cache with final positions
        for component in self.components:
            self.placement_cache[component.reference] = (
                component.position[0],
                component.position[1],
                component.rotation
            )
        
        # Reinitialize grid with new component positions
        self._initialize_grid()
        for component in self.components:
            self._update_grid_for_component(component)
        
        return True
    
    def route_net(self, net_name: str, use_astar: bool = True) -> bool:
        """
        Route a single net.
        
        Args:
            net_name: Name of the net to route
            use_astar: Whether to use A* algorithm (True) or simple maze router (False)
        
        Returns:
            True if successful, False otherwise
        """
        # Find all connections for this net
        connections = [n for n in self.nets if n.net_name == net_name]
        
        if not connections:
            return False
        
        # Initialize trace segments
        net_traces = []
        
        # Route each connection
        for connection in connections:
            # Find the components
            source = None
            target = None
            
            for component in self.components:
                if component.reference == connection.source_component:
                    source = component
                if component.reference == connection.target_component:
                    target = component
            
            if not source or not target:
                print(f"Cannot find components for net {net_name}")
                continue
            
            # Get connection pads positions
            # In a real implementation, this would look up the actual pad positions
            # based on the footprint definition
            
            # Simplified pad position calculation
            source_pos = source.position
            target_pos = target.position
            
            # Determine routing layers
            source_layer = source.layer
            target_layer = target.layer
            
            # Route traces between source and target
            if use_astar:
                # A* routing algorithm
                trace_segments = self._route_astar(
                    net_name,
                    source_pos,
                    target_pos,
                    source_layer,
                    target_layer
                )
            else:
                # Simple maze routing algorithm
                trace_segments = self._route_maze(
                    net_name,
                    source_pos,
                    target_pos,
                    source_layer,
                    target_layer
                )
            
            if trace_segments:
                net_traces.extend(trace_segments)
        
        # Add traces to the layout
        self.traces.extend(net_traces)
        
        return len(net_traces) > 0
    
    def _route_astar(self, net_name: str, start: Tuple[float, float], end: Tuple[float, float],
                     start_layer: str, end_layer: str) -> List[TraceSegment]:
        """
        Route a connection using A* algorithm.
        
        Args:
            net_name: Name of the net
            start: Start position (x, y) in mm
            end: End position (x, y) in mm
            start_layer: Starting layer
            end_layer: Ending layer
        
        Returns:
            List of trace segments for the route
        """
        if not self.grid or not self.board_outline:
            return []
        
        # Convert mm positions to grid coordinates
        min_x, min_y, _, _ = self.board_outline.bounds
        
        start_grid_x = int((start[0] - min_x) / self.grid_resolution)
        start_grid_y = int((start[1] - min_y) / self.grid_resolution)
        end_grid_x = int((end[0] - min_x) / self.grid_resolution)
        end_grid_y = int((end[1] - min_y) / self.grid_resolution)
        
        # Determine layer indices
        start_layer_idx = 0 if start_layer == "top" else 1
        end_layer_idx = 0 if end_layer == "top" else 1
        
        # Implementation of A* algorithm
        # This is a simplified version - real implementation would handle more complex scenarios
        
        # Node structure: (x, y, layer, cost, parent_x, parent_y, parent_layer)
        open_set = []
        closed_set = set()
        
        # Add start node to open set
        start_node = (start_grid_x, start_grid_y, start_layer_idx, 0, -1, -1, -1)
        open_set.append(start_node)
        
        # Heuristic function (Manhattan distance)
        def heuristic(x, y, layer, tx, ty, tlayer):
            return abs(tx - x) + abs(ty - y) + (0 if layer == tlayer else 2)
        
        while open_set:
            # Sort open set by cost + heuristic
            open_set.sort(key=lambda node: node[3] + heuristic(node[0], node[1], node[2], 
                                                               end_grid_x, end_grid_y, end_layer_idx))
            
            # Get node with lowest cost
            current = open_set.pop(0)
            x, y, layer, cost, parent_x, parent_y, parent_layer = current
            
            # Check if we reached the goal
            if x == end_grid_x and y == end_grid_y and layer == end_layer_idx:
                # Reconstruct path
                path = []
                while parent_x != -1:
                    path.append((x, y, layer))
                    node = (x, y, layer, cost, parent_x, parent_y, parent_layer)
                    x, y, layer = parent_x, parent_y, parent_layer
                    
                    # Find parent node
                    for item in closed_set:
                        if item[0] == x and item[1] == y and item[2] == layer:
                            parent_x, parent_y, parent_layer = item[4], item[5], item[6]
                            break
                
                path.append((start_grid_x, start_grid_y, start_layer_idx))
                path.reverse()
                
                # Convert grid path to trace segments
                trace_segments = []
                for i in range(len(path) - 1):
                    x1, y1, l1 = path[i]
                    x2, y2, l2 = path[i + 1]
                    
                    # Convert back to mm
                    start_x = min_x + x1 * self.grid_resolution
                    start_y = min_y + y1 * self.grid_resolution
                    end_x = min_x + x2 * self.grid_resolution
                    end_y = min_y + y2 * self.grid_resolution
                    
                    # Determine if this segment crosses layers
                    via_end = (l1 != l2)
                    
                    # Create trace segment
                    layer_name = "F.Cu" if l1 == 0 else "B.Cu"
                    segment = TraceSegment(
                        net_name=net_name,
                        start_point=(start_x, start_y),
                        end_point=(end_x, end_y),
                        width=self.min_track_width,
                        layer=layer_name,
                        via_end=via_end
                    )
                    
                    trace_segments.append(segment)
                
                return trace_segments
            
            # Add current node to closed set
            closed_set.add(current)
            
            # Check neighbors
            neighbors = []
            
            # Adjacent cells on the same layer
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                
                # Check if within grid bounds
                if nx < 0 or ny < 0 or nx >= self.grid.shape[2] or ny >= self.grid.shape[1]:
                    continue
                
                # Check if cell is not an obstacle
                if self.grid[layer, ny, nx] == 1:
                    continue
                
                neighbors.append((nx, ny, layer))
            
            # Via to other layers
            for l in range(self.layer_count):
                if l != layer:
                    # Check if the cell is free on the other layer
                    if self.grid[l, y, x] == 0:
                        neighbors.append((x, y, l))
            
            # Process neighbors
            for nx, ny, nl in neighbors:
                # Check if neighbor is already in closed set
                in_closed = False
                for node in closed_set:
                    if node[0] == nx and node[1] == ny and node[2] == nl:
                        in_closed = True
                        break
                
                if in_closed:
                    continue
                
                # Calculate new cost
                new_cost = cost + 1
                if nl != layer:
                    new_cost += 3  # Penalty for vias
                
                # Check if neighbor is in open set with higher cost
                in_open = False
                for i, node in enumerate(open_set):
                    if node[0] == nx and node[1] == ny and node[2] == nl:
                        in_open = True
                        if node[3] > new_cost:
                            # Update cost
                            open_set[i] = (nx, ny, nl, new_cost, x, y, layer)
                        break
                
                if not in_open:
                    # Add to open set
                    open_set.append((nx, ny, nl, new_cost, x, y, layer))
        
        # No path found
        return []
    
    def _route_maze(self, net_name: str, start: Tuple[float, float], end: Tuple[float, float],
                   start_layer: str, end_layer: str) -> List[TraceSegment]:
        """
        Route a connection using simple maze routing algorithm.
        
        Args:
            net_name: Name of the net
            start: Start position (x, y) in mm
            end: End position (x, y) in mm
            start_layer: Starting layer
            end_layer: Ending layer
        
        Returns:
            List of trace segments for the route
        """
        # For many simple routes, we can just create direct connections
        # This is a fallback for when the A* algorithm fails
        
        trace_segments = []
        
        # Create a basic route: start -> end with a single via if needed
        layer_name = "F.Cu" if start_layer == "top" else "B.Cu"
        via_needed = (start_layer != end_layer)
        
        # If on different layers, route to via point first
        if via_needed:
            # Calculate a via point halfway between start and end
            via_x = (start[0] + end[0]) / 2
            via_y = (start[1] + end[1]) / 2
            
            # Start to via segment
            segment1 = TraceSegment(
                net_name=net_name,
                start_point=start,
                end_point=(via_x, via_y),
                width=self.min_track_width,
                layer=layer_name,
                via_end=True
            )
            
            # Via to end segment
            end_layer_name = "F.Cu" if end_layer == "top" else "B.Cu"
            segment2 = TraceSegment(
                net_name=net_name,
                start_point=(via_x, via_y),
                end_point=end,
                width=self.min_track_width,
                layer=end_layer_name,
                via_end=False
            )
            
            trace_segments.extend([segment1, segment2])
        else:
            # Direct connection on same layer
            segment = TraceSegment(
                net_name=net_name,
                start_point=start,
                end_point=end,
                width=self.min_track_width,
                layer=layer_name,
                via_end=False
            )
            
            trace_segments.append(segment)
        
        return trace_segments
    
    def auto_route_all_nets(self) -> bool:
        """
        Automatically route all nets on the board.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.nets:
            return False
        
        # Get unique net names
        net_names = set(n.net_name for n in self.nets)
        
        # Route each net
        success_count = 0
        for net_name in net_names:
            if self.route_net(net_name):
                success_count += 1
        
        return success_count == len(net_names)
    
    def add_ground_plane(self, layer: str = "B.Cu", net_name: str = "GND", 
                         clearance: float = 0.5) -> bool:
        """
        Add a ground plane to the board.
        
        Args:
            layer: Layer name
            net_name: Net name for the ground plane
            clearance: Clearance around other objects in mm
        
        Returns:
            True if successful, False otherwise
        """
        if not self.board_outline:
            return False
        
        try:
            # Get board outline with clearance
            min_x, min_y, max_x, max_y = self.board_outline.bounds
            
            # Add margin for clearance
            min_x += clearance
            min_y += clearance
            max_x -= clearance
            max_y -= clearance
            
            # Create ground plane outline
            outline_points = [
                (min_x, min_y),
                (max_x, min_y),
                (max_x, max_y),
                (min_x, max_y),
                (min_x, min_y)  # Close the loop
            ]
            
            # Add to traces as a zone
            if KICAD_AVAILABLE and self.board:
                # Use KiCad helpers to add a zone
                success = kh.add_zone(
                    self.board,
                    outline_points,
                    layer,
                    net_name,
                    min_thickness=self.min_track_width
                ) is not None
            else:
                # Just record the zone information for simulation
                zone = TraceSegment(
                    net_name=net_name,
                    start_point=(min_x, min_y),
                    end_point=(max_x, max_y),
                    width=0.0,  # Not used for zones
                    layer=layer,
                    via_end=False
                )
                
                self.traces.append(zone)
                success = True
            
            return success
        except Exception as e:
            print(f"Error adding ground plane: {e}")
            return False
    
    def export_to_kicad(self, board_file: str) -> bool:
        """
        Export the layout to a KiCad PCB file.
        
        Args:
            board_file: Output PCB file path
        
        Returns:
            True if successful, False otherwise
        """
        if not KICAD_AVAILABLE:
            print(f"KiCad Python API not available. Would export to {board_file}")
            return False
        
        try:
            # Create new board if we don't have one
            if not self.board:
                self.board = kh.create_new_board()
                
                # Add components to board
                for component in self.components:
                    # This is simplified - a real implementation would look up the actual footprint library
                    library = "Resistor_SMD" if component.reference.startswith('R') else "Package_SO"
                    
                    kh.add_footprint(
                        self.board,
                        library,
                        component.footprint_name,
                        component.position,
                        component.rotation,
                        component.reference,
                        "Value"  # Default value
                    )
            
            # Export our layout data to the board
            self._export_to_kicad_board()
            
            # Save the board
            kh.save_board(self.board, board_file)
            return True
        
        except Exception as e:
            print(f"Error exporting to KiCad: {e}")
            return False
    
    def import_from_kicad(self, board_file: str) -> bool:
        """
        Import a layout from a KiCad PCB file.
        
        Args:
            board_file: Input PCB file path
        
        Returns:
            True if successful, False otherwise
        """
        if not KICAD_AVAILABLE:
            print(f"KiCad Python API not available. Would import from {board_file}")
            return False
        
        try:
            # Load board
            self.board = kh.load_board(board_file)
            if not self.board:
                return False
            
            # Import data from the board
            self._import_from_kicad_board()
            return True
        
        except Exception as e:
            print(f"Error importing from KiCad: {e}")
            return False
    
    def run_drc(self) -> List[Dict]:
        """
        Run design rule checks on the layout.
        
        Returns:
            List of DRC violations (each as a dict with details)
        """
        if not KICAD_AVAILABLE or not self.board:
            print("KiCad Python API not available. Would run DRC checks")
            return []
        
        try:
            return kh.run_drc(self.board)
        except Exception as e:
            print(f"Error running DRC: {e}")
            return [{"error": str(e)}]
    
    def optimize_trace_lengths(self, net_names: List[str]) -> bool:
        """
        Optimize trace lengths for length matching.
        
        Args:
            net_names: List of net names to optimize
        
        Returns:
            True if successful, False otherwise
        """
        # This would implement a sophisticated length matching algorithm
        # For now, it's just a placeholder
        return True

# Main demo function
def demo():
    """Run a demo of the PCB layout engine."""
    # Create layout engine
    engine = PCBLayoutEngine()
    
    # Set board outline
    engine.set_board_outline(100.0, 80.0)  # 100x80mm board
    
    # Add some components
    components = [
        ComponentPlacement(
            component_id="U1_ATmega328P",
            reference="U1",
            footprint_name="TQFP-32_7x7mm_P0.8mm",
            position=(50.0, 40.0),
            rotation=0.0,
            layer="top",
            fixed=True  # Fix the microcontroller in the center
        ),
        ComponentPlacement(
            component_id="R1_10k",
            reference="R1",
            footprint_name="R_0805_2012Metric",
            position=(30.0, 30.0),
            rotation=0.0,
            layer="top"
        ),
        ComponentPlacement(
            component_id="R2_10k",
            reference="R2",
            footprint_name="R_0805_2012Metric",
            position=(30.0, 40.0),
            rotation=0.0,
            layer="top"
        ),
        ComponentPlacement(
            component_id="C1_100n",
            reference="C1",
            footprint_name="C_0805_2012Metric",
            position=(60.0, 30.0),
            rotation=90.0,
            layer="top"
        ),
        ComponentPlacement(
            component_id="C2_100n",
            reference="C2",
            footprint_name="C_0805_2012Metric",
            position=(70.0, 40.0),
            rotation=90.0,
            layer="top"
        )
    ]
    
    for component in components:
        engine.add_component(component)
    
    # Define some nets
    nets = [
        NetConnection(
            net_name="VCC",
            source_component="U1",
            source_pad="7",
            target_component="R1",
            target_pad="1"
        ),
        NetConnection(
            net_name="GND",
            source_component="U1",
            source_pad="8",
            target_component="C1",
            target_pad="2"
        ),
        NetConnection(
            net_name="RESET",
            source_component="U1",
            source_pad="1",
            target_component="R2",
            target_pad="1"
        )
    ]
    
    engine.nets = nets
    
    # Auto-place components
    print("Auto-placing components...")
    engine.auto_place_components()
    
    # Auto-route connections
    print("Auto-routing nets...")
    engine.auto_route_all_nets()
    
    # Add ground plane
    print("Adding ground plane...")
    engine.add_ground_plane()
    
    # Export to KiCad
    if KICAD_AVAILABLE:
        print("Exporting to KiCad...")
        engine.export_to_kicad("demo.kicad_pcb")
        print("Running DRC...")
        violations = engine.run_drc()
        if violations:
            print(f"Found {len(violations)} DRC violations")
            for violation in violations:
                print(f"- {violation}")
        else:
            print("No DRC violations found")
    else:
        print("KiCad not available. Cannot export or run DRC.")
    
    print("Demo completed.")

if __name__ == "__main__":
    demo()