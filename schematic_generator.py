#!/usr/bin/env python3
"""
Schematic generator for automated schematic creation.
Converts component requirements into KiCad schematics.
"""

import os
import math
import random
from enum import Enum
from typing import Dict, List, Tuple, Set, Optional, Any, Union
from dataclasses import dataclass, field

# Try to import KiCad eeschema modules
try:
    import pcbnew
    KICAD_AVAILABLE = True
    
    # Check for eeschema Python API
    try:
        import eeschema
        EESCHEMA_AVAILABLE = True
    except ImportError:
        EESCHEMA_AVAILABLE = False
        print("Warning: KiCad eeschema Python API not available. Will use alternative approach.")
except ImportError:
    KICAD_AVAILABLE = False
    EESCHEMA_AVAILABLE = False
    print("Warning: KiCad Python API not available. Schematic generator will use simulation mode.")

@dataclass
class SchematicSymbol:
    """Represents a component symbol in a schematic."""
    reference: str
    value: str
    unit: int = 1
    position: Tuple[float, float] = (0, 0)  # x, y in schematic units
    orientation: int = 0  # 0, 90, 180, 270 degrees
    mirror: bool = False
    fields: Dict[str, str] = field(default_factory=dict)
    library_id: str = ""
    footprint: str = ""

@dataclass
class SchematicWire:
    """Represents a wire connection in a schematic."""
    start: Tuple[float, float]  # x, y in schematic units
    end: Tuple[float, float]    # x, y in schematic units
    net_name: str = ""

@dataclass
class SchematicLabel:
    """Represents a net label in a schematic."""
    position: Tuple[float, float]  # x, y in schematic units
    text: str
    orientation: int = 0  # 0, 90, 180, 270 degrees
    shape: str = "input"  # input, output, bidirectional, etc.

@dataclass
class SchematicJunction:
    """Represents a junction in a schematic."""
    position: Tuple[float, float]  # x, y in schematic units

@dataclass
class SchematicNoConnect:
    """Represents a no-connect marker in a schematic."""
    position: Tuple[float, float]  # x, y in schematic units

class SchematicGenerator:
    """Generator for creating KiCad schematics from component data."""
    
    def __init__(self, output_dir: str = "."):
        """
        Initialize the schematic generator.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir
        self.symbols: List[SchematicSymbol] = []
        self.wires: List[SchematicWire] = []
        self.labels: List[SchematicLabel] = []
        self.junctions: List[SchematicJunction] = []
        self.no_connects: List[SchematicNoConnect] = []
        self.grid_size: int = 100  # KiCad grid size (100 mil)
        self.next_component_id: int = 1
        
        # Track occupied positions to avoid overlaps
        self.occupied_positions: Set[Tuple[int, int]] = set()
        
        # Map of standard component properties
        self.component_templates: Dict[str, Dict[str, Any]] = {
            "resistor": {
                "lib": "Device",
                "symbol": "R",
                "pins": [
                    {"name": "1", "type": "passive", "position": (-100, 0)},
                    {"name": "2", "type": "passive", "position": (100, 0)}
                ],
                "width": 3,
                "height": 1
            },
            "capacitor": {
                "lib": "Device",
                "symbol": "C",
                "pins": [
                    {"name": "1", "type": "passive", "position": (0, 100)},
                    {"name": "2", "type": "passive", "position": (0, -100)}
                ],
                "width": 1,
                "height": 3
            },
            "led": {
                "lib": "Device",
                "symbol": "LED",
                "pins": [
                    {"name": "K", "type": "passive", "position": (0, 100)},
                    {"name": "A", "type": "passive", "position": (0, -100)}
                ],
                "width": 1,
                "height": 3
            },
            "diode": {
                "lib": "Device",
                "symbol": "D",
                "pins": [
                    {"name": "K", "type": "passive", "position": (100, 0)},
                    {"name": "A", "type": "passive", "position": (-100, 0)}
                ],
                "width": 3,
                "height": 1
            },
            "transistor_npn": {
                "lib": "Device",
                "symbol": "Q_NPN_BCE",
                "pins": [
                    {"name": "B", "type": "input", "position": (-100, 0)},
                    {"name": "C", "type": "passive", "position": (0, -100)},
                    {"name": "E", "type": "passive", "position": (0, 100)}
                ],
                "width": 3,
                "height": 3
            },
            "transistor_pnp": {
                "lib": "Device",
                "symbol": "Q_PNP_BCE",
                "pins": [
                    {"name": "B", "type": "input", "position": (-100, 0)},
                    {"name": "C", "type": "passive", "position": (0, -100)},
                    {"name": "E", "type": "passive", "position": (0, 100)}
                ],
                "width": 3,
                "height": 3
            },
            "voltage_regulator": {
                "lib": "Regulator_Linear",
                "symbol": "LM7805_TO220",
                "pins": [
                    {"name": "VI", "type": "power_in", "position": (-100, 0)},
                    {"name": "GND", "type": "power_in", "position": (0, 100)},
                    {"name": "VO", "type": "power_out", "position": (100, 0)}
                ],
                "width": 4,
                "height": 3
            },
            "atmega328p": {
                "lib": "MCU_Microchip_ATmega",
                "symbol": "ATmega328P-AU",
                "pins": [
                    # Just a subset of pins for demonstration
                    {"name": "PD0", "type": "bidirectional", "position": (100, 0)},
                    {"name": "PD1", "type": "bidirectional", "position": (100, 100)},
                    {"name": "PD2", "type": "bidirectional", "position": (100, 200)},
                    {"name": "VCC", "type": "power_in", "position": (-100, 0)},
                    {"name": "GND", "type": "power_in", "position": (-100, 100)}
                ],
                "width": 6,
                "height": 8
            }
        }
    
    def _generate_reference(self, component_type: str) -> str:
        """
        Generate a reference designator for a component.
        
        Args:
            component_type: Type of component (resistor, capacitor, etc.)
        
        Returns:
            Reference designator string
        """
        prefix_map = {
            "resistor": "R",
            "capacitor": "C",
            "led": "D",
            "diode": "D",
            "transistor_npn": "Q",
            "transistor_pnp": "Q",
            "voltage_regulator": "U",
            "microcontroller": "U",
            "atmega328p": "U",
            "ic": "U",
            "crystal": "Y",
            "connector": "J",
            "switch": "SW",
            "inductor": "L",
            "fuse": "F"
        }
        
        # Get prefix or use "U" as default
        prefix = prefix_map.get(component_type.lower(), "U")
        
        # Generate ID and increment counter
        ref = f"{prefix}{self.next_component_id}"
        self.next_component_id += 1
        
        return ref
    
    def _get_symbol_info(self, component_type: str) -> Dict[str, Any]:
        """
        Get symbol information for a component type.
        
        Args:
            component_type: Type of component
        
        Returns:
            Dictionary with symbol information
        """
        # Convert to lowercase and remove spaces
        comp_type = component_type.lower().replace(" ", "_")
        
        # Check known templates
        if comp_type in self.component_templates:
            return self.component_templates[comp_type]
        
        # Return resistor as default
        print(f"Warning: Unknown component type '{component_type}', using resistor template")
        return self.component_templates["resistor"]
    
    def _find_available_position(self, width: int, height: int) -> Tuple[int, int]:
        """
        Find an available position on the schematic grid.
        
        Args:
            width: Component width in grid units
            height: Component height in grid units
        
        Returns:
            (x, y) position on grid
        """
        # Start from a reasonable position
        grid_x, grid_y = 10, 10
        
        # Simple placement algorithm - keep moving down and right until we find a free spot
        while True:
            # Check if this position is available
            occupied = False
            for x in range(grid_x, grid_x + width):
                for y in range(grid_y, grid_y + height):
                    if (x, y) in self.occupied_positions:
                        occupied = True
                        break
                if occupied:
                    break
            
            if not occupied:
                # Mark this position as occupied
                for x in range(grid_x, grid_x + width):
                    for y in range(grid_y, grid_y + height):
                        self.occupied_positions.add((x, y))
                
                # Convert grid position to schematic coordinates
                return (grid_x * self.grid_size, grid_y * self.grid_size)
            
            # Move to next position
            grid_x += width + 1
            
            # Wrap to next row after 100 grid units
            if grid_x > 100:
                grid_x = 10
                grid_y += height + 1
    
    def add_component(self, component_type: str, value: str = "", 
                      footprint: str = "", properties: Dict[str, str] = None) -> SchematicSymbol:
        """
        Add a component to the schematic.
        
        Args:
            component_type: Type of component (resistor, capacitor, etc.)
            value: Component value (e.g., "10k" for a resistor)
            footprint: Footprint name (e.g., "Resistor_SMD:R_0805_2012Metric")
            properties: Additional component properties
        
        Returns:
            The created SchematicSymbol
        """
        # Generate reference designator
        reference = self._generate_reference(component_type)
        
        # Get symbol information
        symbol_info = self._get_symbol_info(component_type)
        
        # Find an available position
        width = symbol_info.get("width", 3)
        height = symbol_info.get("height", 3)
        position = self._find_available_position(width, height)
        
        # Create library ID
        lib = symbol_info.get("lib", "Device")
        symbol = symbol_info.get("symbol", "R")
        library_id = f"{lib}:{symbol}"
        
        # Create fields dictionary
        fields = properties or {}
        if value:
            fields["Value"] = value
        if footprint:
            fields["Footprint"] = footprint
        
        # Create the symbol
        symbol = SchematicSymbol(
            reference=reference,
            value=value or reference,
            position=position,
            orientation=0,
            mirror=False,
            fields=fields,
            library_id=library_id,
            footprint=footprint
        )
        
        # Add to symbols list
        self.symbols.append(symbol)
        
        return symbol
    
    def connect_pins(self, source_component: str, source_pin: str,
                     target_component: str, target_pin: str,
                     net_name: str = "") -> List[SchematicWire]:
        """
        Connect pins between components.
        
        Args:
            source_component: Source component reference
            source_pin: Source pin name
            target_component: Target component reference
            target_pin: Target pin name
            net_name: Optional net name
        
        Returns:
            List of created SchematicWire objects
        """
        # In a real implementation, this would calculate the actual pin positions
        # based on the component positions and orientations
        # Here we'll create a simplified representation
        
        # Find the components
        source = None
        target = None
        
        for symbol in self.symbols:
            if symbol.reference == source_component:
                source = symbol
            if symbol.reference == target_component:
                target = symbol
        
        if not source or not target:
            print(f"Warning: Cannot connect {source_component}:{source_pin} to {target_component}:{target_pin} - components not found")
            return []
        
        # For now, create a simple horizontal + vertical routing
        source_pos = source.position
        target_pos = target.position
        
        # Create a junction point
        junction_x = source_pos[0]
        junction_y = target_pos[1]
        
        # Create two wire segments
        wire1 = SchematicWire(
            start=source_pos,
            end=(junction_x, junction_y),
            net_name=net_name
        )
        
        wire2 = SchematicWire(
            start=(junction_x, junction_y),
            end=target_pos,
            net_name=net_name
        )
        
        # Add junction if needed
        if (junction_x, junction_y) != source_pos and (junction_x, junction_y) != target_pos:
            junction = SchematicJunction(position=(junction_x, junction_y))
            self.junctions.append(junction)
        
        # Add net label if provided
        if net_name:
            label = SchematicLabel(
                position=(junction_x, junction_y - 100),
                text=net_name
            )
            self.labels.append(label)
        
        # Add wires to list
        self.wires.extend([wire1, wire2])
        
        return [wire1, wire2]
    
    def add_power_net(self, component: str, pin: str, net_name: str) -> SchematicLabel:
        """
        Add a power net label to a component pin.
        
        Args:
            component: Component reference
            pin: Pin name
            net_name: Power net name (e.g., "VCC", "GND")
        
        Returns:
            Created SchematicLabel
        """
        # Find the component
        symbol = None
        for s in self.symbols:
            if s.reference == component:
                symbol = s
                break
        
        if not symbol:
            print(f"Warning: Cannot add power net to {component}:{pin} - component not found")
            return None
        
        # Create a label at the component position (simplified)
        label = SchematicLabel(
            position=(symbol.position[0], symbol.position[1] - 200),
            text=net_name,
            shape="power"
        )
        
        self.labels.append(label)
        return label
    
    def add_global_label(self, position: Tuple[float, float], text: str, 
                        shape: str = "input") -> SchematicLabel:
        """
        Add a global net label.
        
        Args:
            position: Position (x, y) in schematic units
            text: Label text
            shape: Label shape (input, output, bidirectional, etc.)
        
        Returns:
            Created SchematicLabel
        """
        label = SchematicLabel(position=position, text=text, shape=shape)
        self.labels.append(label)
        return label
    
    def add_junction(self, position: Tuple[float, float]) -> SchematicJunction:
        """
        Add a junction.
        
        Args:
            position: Position (x, y) in schematic units
        
        Returns:
            Created SchematicJunction
        """
        junction = SchematicJunction(position=position)
        self.junctions.append(junction)
        return junction
    
    def add_no_connect(self, component: str, pin: str) -> SchematicNoConnect:
        """
        Add a no-connect marker to a component pin.
        
        Args:
            component: Component reference
            pin: Pin name
        
        Returns:
            Created SchematicNoConnect
        """
        # Find the component
        symbol = None
        for s in self.symbols:
            if s.reference == component:
                symbol = s
                break
        
        if not symbol:
            print(f"Warning: Cannot add no-connect to {component}:{pin} - component not found")
            return None
        
        # Create a no-connect at the component position (simplified)
        no_connect = SchematicNoConnect(position=symbol.position)
        self.no_connects.append(no_connect)
        return no_connect
    
    def generate_netlist(self) -> Dict:
        """
        Generate a netlist representation of the schematic.
        
        Returns:
            Dictionary representing the netlist
        """
        # Create a simplified netlist structure
        netlist = {
            "components": [],
            "nets": []
        }
        
        # Add components
        for symbol in self.symbols:
            component = {
                "reference": symbol.reference,
                "value": symbol.value,
                "library": symbol.library_id.split(":")[0],
                "symbol": symbol.library_id.split(":")[1],
                "footprint": symbol.footprint,
                "fields": symbol.fields
            }
            
            netlist["components"].append(component)
        
        # Create nets dictionary
        nets = {}
        
        # Process wires to build nets
        for wire in self.wires:
            net_name = wire.net_name or f"Net-{len(nets)+1}"
            
            if net_name not in nets:
                nets[net_name] = {"name": net_name, "connections": []}
            
            # In a real implementation, this would include actual component pins
            # Here we're just recording the wire endpoints
            connection = {
                "start": wire.start,
                "end": wire.end
            }
            
            nets[net_name]["connections"].append(connection)
        
        # Convert nets dictionary to list
        netlist["nets"] = list(nets.values())
        
        return netlist
    
    def _write_kicad_sch_file(self, filename: str) -> bool:
        """
        Write a KiCad schematic file.
        
        Args:
            filename: Output filename
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filename, 'w') as f:
                # Write schematic header
                f.write("(kicad_sch (version 20211123) (generator schematic_generator.py)\n\n")
                
                # Write project libraries
                f.write("  (lib_symbols\n")
                
                # Add symbol definitions
                # In a real implementation, this would include the actual symbol definitions
                # or rely on the KiCad libraries
                f.write("  )\n\n")
                
                # Write symbols
                for symbol in self.symbols:
                    lib, sym_name = symbol.library_id.split(":")
                    
                    f.write(f"  (symbol (lib_id \"{symbol.library_id}\") (at {symbol.position[0]} {symbol.position[1]} {symbol.orientation})\n")
                    f.write(f"    (property \"Reference\" \"{symbol.reference}\" (id 0) (at 0 0 0))\n")
                    f.write(f"    (property \"Value\" \"{symbol.value}\" (id 1) (at 0 0 0))\n")
                    
                    # Write footprint if available
                    if symbol.footprint:
                        f.write(f"    (property \"Footprint\" \"{symbol.footprint}\" (id 2) (at 0 0 0))\n")
                    
                    # Write additional fields
                    for i, (key, value) in enumerate(symbol.fields.items(), start=3):
                        f.write(f"    (property \"{key}\" \"{value}\" (id {i}) (at 0 0 0))\n")
                    
                    f.write("  )\n\n")
                
                # Write wires
                for wire in self.wires:
                    f.write(f"  (wire (pts (xy {wire.start[0]} {wire.start[1]}) (xy {wire.end[0]} {wire.end[1]}))\n")
                    if wire.net_name:
                        f.write(f"    (net \"{wire.net_name}\")\n")
                    f.write("  )\n\n")
                
                # Write labels
                for label in self.labels:
                    label_type = "label"
                    if label.shape == "power":
                        label_type = "power"
                    elif label.shape == "input" or label.shape == "output" or label.shape == "bidirectional":
                        label_type = "global_label"
                    
                    f.write(f"  ({label_type} \"{label.text}\" (at {label.position[0]} {label.position[1]} {label.orientation})\n")
                    if label_type == "global_label":
                        f.write(f"    (shape {label.shape})\n")
                    f.write("  )\n\n")
                
                # Write junctions
                for junction in self.junctions:
                    f.write(f"  (junction (at {junction.position[0]} {junction.position[1]}))\n")
                
                # Write no-connects
                for nc in self.no_connects:
                    f.write(f"  (no_connect (at {nc.position[0]} {nc.position[1]}))\n")
                
                # Close schematic
                f.write(")\n")
            
            return True
        except Exception as e:
            print(f"Error writing KiCad schematic file: {e}")
            return False
    
    def _write_kicad_pro_file(self, filename: str) -> bool:
        """
        Write a KiCad project file.
        
        Args:
            filename: Output filename
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filename, 'w') as f:
                # Write simple project file
                f.write("{\n")
                f.write("  \"board\": {\n")
                f.write("    \"design_settings\": {\n")
                f.write("      \"defaults\": {\n")
                f.write("        \"board_outline_line_width\": 0.09999999999999999,\n")
                f.write("        \"copper_line_width\": 0.19999999999999998,\n")
                f.write("        \"copper_text_italic\": false,\n")
                f.write("        \"copper_text_size_h\": 1.5,\n")
                f.write("        \"copper_text_size_v\": 1.5,\n")
                f.write("        \"copper_text_thickness\": 0.3,\n")
                f.write("        \"copper_text_upright\": false,\n")
                f.write("        \"courtyard_line_width\": 0.049999999999999996,\n")
                f.write("        \"dimension_precision\": 4,\n")
                f.write("        \"dimension_units\": 3,\n")
                f.write("        \"dimensions\": {\n")
                f.write("          \"arrow_length\": 1270000,\n")
                f.write("          \"extension_offset\": 500000,\n")
                f.write("          \"keep_text_aligned\": true,\n")
                f.write("          \"suppress_zeroes\": false,\n")
                f.write("          \"text_position\": 0,\n")
                f.write("          \"units_format\": 1\n")
                f.write("        },\n")
                f.write("        \"fab_line_width\": 0.09999999999999999,\n")
                f.write("        \"fab_text_italic\": false,\n")
                f.write("        \"fab_text_size_h\": 1.0,\n")
                f.write("        \"fab_text_size_v\": 1.0,\n")
                f.write("        \"fab_text_thickness\": 0.15,\n")
                f.write("        \"fab_text_upright\": false,\n")
                f.write("        \"other_line_width\": 0.15,\n")
                f.write("        \"other_text_italic\": false,\n")
                f.write("        \"other_text_size_h\": 1.0,\n")
                f.write("        \"other_text_size_v\": 1.0,\n")
                f.write("        \"other_text_thickness\": 0.15,\n")
                f.write("        \"other_text_upright\": false,\n")
                f.write("        \"pads\": {\n")
                f.write("          \"drill\": 0.762,\n")
                f.write("          \"height\": 1.524,\n")
                f.write("          \"width\": 1.524\n")
                f.write("        },\n")
                f.write("        \"silk_line_width\": 0.15,\n")
                f.write("        \"silk_text_italic\": false,\n")
                f.write("        \"silk_text_size_h\": 1.0,\n")
                f.write("        \"silk_text_size_v\": 1.0,\n")
                f.write("        \"silk_text_thickness\": 0.15,\n")
                f.write("        \"silk_text_upright\": false,\n")
                f.write("        \"zones\": {\n")
                f.write("          \"45_degree_only\": false,\n")
                f.write("          \"min_clearance\": 0.508\n")
                f.write("        }\n")
                f.write("      },\n")
                f.write("      \"diff_pair_dimensions\": [],\n")
                f.write("      \"drc_exclusions\": [],\n")
                f.write("      \"meta\": {\n")
                f.write("        \"version\": 2\n")
                f.write("      },\n")
                f.write("      \"rule_severities\": {\n")
                f.write("        \"annular_width\": \"error\",\n")
                f.write("        \"clearance\": \"error\",\n")
                f.write("        \"copper_edge_clearance\": \"error\",\n")
                f.write("        \"courtyards_overlap\": \"error\",\n")
                f.write("        \"diff_pair_gap_out_of_range\": \"error\",\n")
                f.write("        \"diff_pair_uncoupled_length_too_long\": \"error\",\n")
                f.write("        \"drill_out_of_range\": \"error\",\n")
                f.write("        \"duplicate_footprints\": \"warning\",\n")
                f.write("        \"extra_footprint\": \"warning\",\n")
                f.write("        \"footprint_type_mismatch\": \"error\",\n")
                f.write("        \"hole_clearance\": \"error\",\n")
                f.write("        \"hole_near_hole\": \"error\",\n")
                f.write("        \"invalid_outline\": \"error\",\n")
                f.write("        \"item_on_disabled_layer\": \"error\",\n")
                f.write("        \"items_not_allowed\": \"error\",\n")
                f.write("        \"length_out_of_range\": \"error\",\n")
                f.write("        \"malformed_courtyard\": \"error\",\n")
                f.write("        \"microvia_drill_out_of_range\": \"error\",\n")
                f.write("        \"missing_courtyard\": \"ignore\",\n")
                f.write("        \"missing_footprint\": \"warning\",\n")
                f.write("        \"net_conflict\": \"warning\",\n")
                f.write("        \"npth_inside_courtyard\": \"ignore\",\n")
                f.write("        \"padstack\": \"error\",\n")
                f.write("        \"pth_inside_courtyard\": \"ignore\",\n")
                f.write("        \"shorting_items\": \"error\",\n")
                f.write("        \"silk_over_copper\": \"warning\",\n")
                f.write("        \"silk_overlap\": \"warning\",\n")
                f.write("        \"skew_out_of_range\": \"error\",\n")
                f.write("        \"through_hole_pad_without_hole\": \"error\",\n")
                f.write("        \"too_many_vias\": \"error\",\n")
                f.write("        \"track_dangling\": \"warning\",\n")
                f.write("        \"track_width\": \"error\",\n")
                f.write("        \"tracks_crossing\": \"error\",\n")
                f.write("        \"unconnected_items\": \"error\",\n")
                f.write("        \"unresolved_variable\": \"error\",\n")
                f.write("        \"via_dangling\": \"warning\",\n")
                f.write("        \"zone_has_empty_net\": \"error\",\n")
                f.write("        \"zones_intersect\": \"error\"\n")
                f.write("      },\n")
                f.write("      \"rules\": {\n")
                f.write("        \"allow_blind_buried_vias\": false,\n")
                f.write("        \"allow_microvias\": false,\n")
                f.write("        \"max_error\": 0.005,\n")
                f.write("        \"min_clearance\": 0.0,\n")
                f.write("        \"min_copper_edge_clearance\": 0.0,\n")
                f.write("        \"min_hole_clearance\": 0.25,\n")
                f.write("        \"min_hole_to_hole\": 0.25,\n")
                f.write("        \"min_microvia_diameter\": 0.19999999999999998,\n")
                f.write("        \"min_microvia_drill\": 0.09999999999999999,\n")
                f.write("        \"min_silk_clearance\": 0.0,\n")
                f.write("        \"min_through_hole_diameter\": 0.3,\n")
                f.write("        \"min_track_width\": 0.19999999999999998,\n")
                f.write("        \"min_via_annular_width\": 0.049999999999999996,\n")
                f.write("        \"min_via_diameter\": 0.39999999999999997,\n")
                f.write("        \"use_height_for_length_calcs\": true\n")
                f.write("      },\n")
                f.write("      \"track_widths\": [],\n")
                f.write("      \"via_dimensions\": [],\n")
                f.write("      \"zones_allow_external_fillets\": false,\n")
                f.write("      \"zones_use_no_outline\": true\n")
                f.write("    }\n")
                f.write("  },\n")
                f.write("  \"schematic\": {\n")
                f.write("    \"legacy_lib_dir\": \"\",\n")
                f.write("    \"legacy_lib_list\": []\n")
                f.write("  },\n")
                f.write("  \"sheets\": [],\n")
                f.write("  \"version\": 1\n")
                f.write("}\n")
            
            return True
        except Exception as e:
            print(f"Error writing KiCad project file: {e}")
            return False
    
    def generate_schematic(self, output_filename: str = "generated_schematic") -> bool:
        """
        Generate a KiCad schematic file from the current data.
        
        Args:
            output_filename: Base name for output files (without extension)
        
        Returns:
            True if successful, False otherwise
        """
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create full paths
        sch_file = os.path.join(self.output_dir, f"{output_filename}.kicad_sch")
        pro_file = os.path.join(self.output_dir, f"{output_filename}.kicad_pro")
        
        # Write the schematic file
        success_sch = self._write_kicad_sch_file(sch_file)
        
        # Write the project file
        success_pro = self._write_kicad_pro_file(pro_file)
        
        if success_sch and success_pro:
            print(f"Schematic generated: {sch_file}")
            return True
        else:
            print(f"Failed to generate schematic: {sch_file}")
            return False
    
    def generate_netlist_file(self, output_filename: str = "generated_netlist.net") -> bool:
        """
        Generate a KiCad netlist file from the current data.
        
        Args:
            output_filename: Output filename for netlist
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Create full path
            netlist_file = os.path.join(self.output_dir, output_filename)
            
            # Generate netlist data
            netlist_data = self.generate_netlist()
            
            # Write netlist in KiCad format
            with open(netlist_file, 'w') as f:
                # Write netlist header
                f.write("(export (version D)\n")
                f.write("  (design\n")
                f.write("    (source \"generated_schematic.sch\")\n")
                f.write("    (date \"{}\")\n".format("2024-05-08"))
                f.write("    (tool \"schematic_generator.py\")\n")
                f.write("  )\n")
                
                # Write components
                f.write("  (components\n")
                for component in netlist_data["components"]:
                    f.write(f"    (comp (ref \"{component['reference']}\")\n")
                    f.write(f"      (value \"{component['value']}\")\n")
                    f.write(f"      (footprint \"{component['footprint']}\")\n")
                    f.write("    )\n")
                f.write("  )\n")
                
                # Write nets
                f.write("  (nets\n")
                for i, net in enumerate(netlist_data["nets"], start=1):
                    f.write(f"    (net (code {i}) (name \"{net['name']}\")\n")
                    
                    # In a real netlist, this would list all pins connected to this net
                    # For our simplified version, we'll just note the connections
                    for conn in net["connections"]:
                        f.write(f"      (node (ref \"CONN\") (pin ?))\n")
                    
                    f.write("    )\n")
                f.write("  )\n")
                
                # Close netlist
                f.write(")\n")
            
            print(f"Netlist generated: {netlist_file}")
            return True
        
        except Exception as e:
            print(f"Error generating netlist file: {e}")
            return False
    
    def create_arduino_shield_template(self) -> None:
        """Create a template for an Arduino shield."""
        # Add Arduino header components
        headers = {
            "J1": ("Connector", "Digital Header", "Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical"),
            "J2": ("Connector", "Power Header", "Connector_PinHeader_2.54mm:PinHeader_1x8_P2.54mm_Vertical"),
            "J3": ("Connector", "Analog Header", "Connector_PinHeader_2.54mm:PinHeader_1x6_P2.54mm_Vertical"),
            "J4": ("Connector", "Digital Header 2", "Connector_PinHeader_2.54mm:PinHeader_1x8_P2.54mm_Vertical"),
        }
        
        # Add headers
        header_symbols = {}
        for ref, (type_, value, footprint) in headers.items():
            symbol = SchematicSymbol(
                reference=ref,
                value=value,
                unit=1,
                position=(self.grid_size * (10 + len(header_symbols) * 10), self.grid_size * 10),
                orientation=0,
                mirror=False,
                fields={},
                library_id="Connector:Conn_01x10_Pin" if "1x10" in footprint else 
                          "Connector:Conn_01x08_Pin" if "1x8" in footprint else 
                          "Connector:Conn_01x06_Pin",
                footprint=footprint
            )
            
            self.symbols.append(symbol)
            header_symbols[ref] = symbol
            
            # Mark position as occupied
            grid_x = 10 + len(header_symbols) * 10
            grid_y = 10
            for x in range(grid_x, grid_x + 3):
                for y in range(grid_y, grid_y + 10):
                    self.occupied_positions.add((x, y))
        
        # Add power and ground labels
        self.add_power_net("J2", "1", "5V")
        self.add_power_net("J2", "4", "GND")
        self.add_power_net("J2", "2", "3V3")
    
    @staticmethod
    def create_arduino_shield_schematic(output_dir: str = ".", 
                                       output_filename: str = "arduino_shield") -> bool:
        """
        Create a basic Arduino shield schematic.
        
        Args:
            output_dir: Output directory
            output_filename: Base name for output files
        
        Returns:
            True if successful, False otherwise
        """
        # Create schematic generator
        generator = SchematicGenerator(output_dir=output_dir)
        
        # Create Arduino shield template
        generator.create_arduino_shield_template()
        
        # Add some example components
        r1 = generator.add_component("resistor", "10k", "Resistor_SMD:R_0805_2012Metric")
        r2 = generator.add_component("resistor", "1k", "Resistor_SMD:R_0805_2012Metric")
        c1 = generator.add_component("capacitor", "100nF", "Capacitor_SMD:C_0805_2012Metric")
        led1 = generator.add_component("led", "LED", "LED_SMD:LED_0805_2012Metric")
        
        # Add some connections
        generator.connect_pins("J2", "1", r1.reference, "1", "5V")
        generator.connect_pins(r1.reference, "2", led1.reference, "1", "LED_CONN")
        generator.connect_pins(led1.reference, "2", "J2", "4", "GND")
        
        # Add a ground connection
        generator.connect_pins(c1.reference, "2", "J2", "4", "GND")
        
        # Generate schematic file
        success = generator.generate_schematic(output_filename)
        
        # Generate netlist
        if success:
            generator.generate_netlist_file(f"{output_filename}.net")
        
        return success

# When run directly, create a demo schematic
if __name__ == "__main__":
    # Create a basic Arduino shield schematic
    SchematicGenerator.create_arduino_shield_schematic()