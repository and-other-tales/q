#!/usr/bin/env python3
"""
Helper functions for working with the KiCad Python API.
These functions simplify common operations when programmatically 
creating and manipulating KiCad designs.
"""

import os
import sys
import math
from typing import Dict, List, Tuple, Optional, Any

# Try to import KiCad modules, handle gracefully if not available
try:
    import pcbnew
    from pcbnew import (
        BOARD, PAD, FOOTPRINT, PCB_SHAPE, VECTOR2I, 
        PCB_LAYER_ID, IU_PER_MM, IU_PER_MILS
    )
    # Check if we also have eeschema access
    try:
        import eeschema
        EESCHEMA_AVAILABLE = True
    except ImportError:
        EESCHEMA_AVAILABLE = False
    
    KICAD_AVAILABLE = True
except ImportError:
    KICAD_AVAILABLE = False
    print("Warning: KiCad Python API not available. Helper functions will be stubs.")

# Unit conversion helpers
def mm_to_kicad_units(mm: float) -> int:
    """Convert millimeters to KiCad internal units."""
    if KICAD_AVAILABLE:
        return int(mm * IU_PER_MM)
    return int(mm * 1000000)  # Fallback approximation

def mils_to_kicad_units(mils: float) -> int:
    """Convert mils to KiCad internal units."""
    if KICAD_AVAILABLE:
        return int(mils * IU_PER_MILS)
    return int(mils * 25400)  # Fallback approximation

def kicad_units_to_mm(ku: int) -> float:
    """Convert KiCad internal units to millimeters."""
    if KICAD_AVAILABLE:
        return float(ku) / IU_PER_MM
    return float(ku) / 1000000  # Fallback approximation

# Board creation helpers
def create_new_board(name: str = "new_design") -> Any:
    """Create a new KiCad PCB board."""
    if not KICAD_AVAILABLE:
        print(f"Would create new board: {name}")
        return None
    
    board = BOARD()
    board.SetFileHeader("KiCad " + pcbnew.GetBuildVersion())
    
    # Set default design rules
    design_settings = board.GetDesignSettings()
    design_settings.SetCopperLayerCount(2)  # 2-layer board by default
    
    # Set trace width and clearance defaults
    default_track_width = mm_to_kicad_units(0.25)  # 0.25mm default track width
    design_settings.m_TrackMinWidth = default_track_width
    
    # Set up standard trace widths
    widths = []
    for width in [0.25, 0.5, 0.75, 1.0]:  # Standard trace widths in mm
        widths.append(mm_to_kicad_units(width))
    design_settings.SetTrackWidthList(widths)
    
    # Set default clearance
    design_settings.m_MinClearance = mm_to_kicad_units(0.2)  # 0.2mm clearance
    
    return board

def save_board(board: Any, filepath: str) -> bool:
    """Save a KiCad board to file."""
    if not KICAD_AVAILABLE:
        print(f"Would save board to: {filepath}")
        return True
    
    try:
        pcbnew.SaveBoard(filepath, board)
        return True
    except Exception as e:
        print(f"Error saving board: {str(e)}")
        return False

def load_board(filepath: str) -> Any:
    """Load a KiCad board from file."""
    if not KICAD_AVAILABLE:
        print(f"Would load board from: {filepath}")
        return None
    
    try:
        board = pcbnew.LoadBoard(filepath)
        return board
    except Exception as e:
        print(f"Error loading board: {str(e)}")
        return None

# Footprint management
def add_footprint(board: Any, footprint_lib: str, footprint_name: str, 
                  position: Tuple[float, float], rotation: float = 0.0, 
                  reference: str = "", value: str = "") -> Any:
    """
    Add a footprint to the board.
    
    Args:
        board: KiCad board object
        footprint_lib: Footprint library name
        footprint_name: Footprint name
        position: (x, y) position in mm
        rotation: Rotation angle in degrees
        reference: Component reference (e.g., "R1")
        value: Component value (e.g., "10k")
    
    Returns:
        The created footprint object or None if failed
    """
    if not KICAD_AVAILABLE:
        print(f"Would add footprint {footprint_name} at position {position}")
        return None
    
    try:
        # Load the footprint from the KiCad library
        footprint_id = f"{footprint_lib}:{footprint_name}"
        fp_loader = pcbnew.PLUGIN_REGISTRY.PluginFind(pcbnew.IO_MGR.KICAD_SEXP)
        
        # Get the library path
        fp_lib_table = pcbnew.FP_LIB_TABLE.GlobalInstance()
        lib_path = fp_lib_table.FindRow(footprint_lib).GetFullURI()
        
        # Load the footprint
        footprint = fp_loader.FootprintLoad(lib_path, footprint_name)
        
        if not footprint:
            print(f"Could not load footprint: {footprint_id}")
            return None
        
        # Set position, rotation, reference, and value
        if reference:
            footprint.SetReference(reference)
        if value:
            footprint.SetValue(value)
        
        # Position is in mm, convert to KiCad units
        pos_x = mm_to_kicad_units(position[0])
        pos_y = mm_to_kicad_units(position[1])
        footprint.SetPosition(VECTOR2I(pos_x, pos_y))
        
        # Set rotation
        footprint.SetOrientation(rotation * 10.0)  # KiCad uses tenths of a degree
        
        # Add to board
        board.Add(footprint)
        return footprint
    
    except Exception as e:
        print(f"Error adding footprint: {str(e)}")
        return None

# Track and via helpers
def add_track(board: Any, start_pos: Tuple[float, float], end_pos: Tuple[float, float], 
              width: float = 0.25, layer: str = "F.Cu") -> Any:
    """
    Add a track (trace) to the board.
    
    Args:
        board: KiCad board object
        start_pos: (x, y) start position in mm
        end_pos: (x, y) end position in mm
        width: Track width in mm
        layer: Layer name ("F.Cu" or "B.Cu" typically)
    
    Returns:
        The created track object or None if failed
    """
    if not KICAD_AVAILABLE:
        print(f"Would add track from {start_pos} to {end_pos} on layer {layer}")
        return None
    
    try:
        # Create a new track
        track = pcbnew.PCB_TRACK(board)
        
        # Convert positions to KiCad units
        start_x = mm_to_kicad_units(start_pos[0])
        start_y = mm_to_kicad_units(start_pos[1])
        end_x = mm_to_kicad_units(end_pos[0])
        end_y = mm_to_kicad_units(end_pos[1])
        
        # Set track properties
        track.SetStart(VECTOR2I(start_x, start_y))
        track.SetEnd(VECTOR2I(end_x, end_y))
        track.SetWidth(mm_to_kicad_units(width))
        
        # Set layer
        layer_id = get_layer_id(layer)
        track.SetLayer(layer_id)
        
        # Add to board
        board.Add(track)
        return track
    
    except Exception as e:
        print(f"Error adding track: {str(e)}")
        return None

def add_via(board: Any, position: Tuple[float, float], size: float = 0.8, 
            drill: float = 0.4, layers: Tuple[str, str] = ("F.Cu", "B.Cu")) -> Any:
    """
    Add a via to the board.
    
    Args:
        board: KiCad board object
        position: (x, y) position in mm
        size: Via diameter in mm
        drill: Drill diameter in mm
        layers: Tuple of layer names the via connects
    
    Returns:
        The created via object or None if failed
    """
    if not KICAD_AVAILABLE:
        print(f"Would add via at {position} connecting {layers}")
        return None
    
    try:
        # Create a new via
        via = pcbnew.PCB_VIA(board)
        
        # Convert position to KiCad units
        pos_x = mm_to_kicad_units(position[0])
        pos_y = mm_to_kicad_units(position[1])
        
        # Set via properties
        via.SetPosition(VECTOR2I(pos_x, pos_y))
        via.SetWidth(mm_to_kicad_units(size))
        via.SetDrill(mm_to_kicad_units(drill))
        
        # Set layers
        via.SetLayerPair(get_layer_id(layers[0]), get_layer_id(layers[1]))
        
        # Add to board
        board.Add(via)
        return via
    
    except Exception as e:
        print(f"Error adding via: {str(e)}")
        return None

# Zone (copper pour) helpers
def add_zone(board: Any, points: List[Tuple[float, float]], layer: str = "F.Cu", 
             net_name: str = "GND", min_thickness: float = 0.2) -> Any:
    """
    Add a copper zone (pour) to the board.
    
    Args:
        board: KiCad board object
        points: List of (x, y) points defining the zone outline in mm
        layer: Layer name
        net_name: Net name (typically "GND" for ground plane)
        min_thickness: Minimum copper thickness in mm
    
    Returns:
        The created zone object or None if failed
    """
    if not KICAD_AVAILABLE:
        print(f"Would add zone on layer {layer} for net {net_name}")
        return None
    
    try:
        # Create a new zone
        zone = pcbnew.ZONE(board)
        
        # Set layer
        layer_id = get_layer_id(layer)
        zone.SetLayer(layer_id)
        
        # Set net
        net_code = get_net_code(board, net_name)
        if net_code > 0:
            zone.SetNetCode(net_code)
        
        # Set min thickness
        zone.SetMinThickness(mm_to_kicad_units(min_thickness))
        
        # Create outline
        outline = zone.Outline()
        for i, point in enumerate(points):
            x = mm_to_kicad_units(point[0])
            y = mm_to_kicad_units(point[1])
            
            if i == 0:
                # Start new outline
                outline.NewOutline()
            
            # Add point to outline
            outline.Append(VECTOR2I(x, y))
        
        # Add to board
        board.Add(zone)
        return zone
    
    except Exception as e:
        print(f"Error adding zone: {str(e)}")
        return None

# Helper functions
def get_layer_id(layer_name: str) -> int:
    """Convert a layer name to a KiCad layer ID."""
    if not KICAD_AVAILABLE:
        # Return dummy values for simulation
        if layer_name == "F.Cu":
            return 0
        elif layer_name == "B.Cu":
            return 31
        return 0
    
    # Common layer mapping
    layer_map = {
        "F.Cu": pcbnew.F_Cu,
        "B.Cu": pcbnew.B_Cu,
        "F.Paste": pcbnew.F_Paste,
        "B.Paste": pcbnew.B_Paste,
        "F.SilkS": pcbnew.F_SilkS,
        "B.SilkS": pcbnew.B_SilkS,
        "F.Mask": pcbnew.F_Mask,
        "B.Mask": pcbnew.B_Mask,
        "Edge.Cuts": pcbnew.Edge_Cuts
    }
    
    return layer_map.get(layer_name, pcbnew.F_Cu)

def get_net_code(board: Any, net_name: str) -> int:
    """Get net code for a given net name."""
    if not KICAD_AVAILABLE:
        return 1  # Dummy value for simulation
    
    netinfo = board.GetNetInfo()
    net = netinfo.FindNet(net_name)
    
    if net:
        return net.GetNetCode()
    
    # If net doesn't exist, create it
    new_net = pcbnew.NETINFO_ITEM(board, net_name)
    netinfo.AppendNet(new_net)
    return new_net.GetNetCode()

# Schematic creation helpers (if eeschema is available)
def create_new_schematic(name: str = "new_schematic") -> Any:
    """Create a new schematic."""
    if not KICAD_AVAILABLE or not EESCHEMA_AVAILABLE:
        print(f"Would create new schematic: {name}")
        return None
    
    # This functionality depends on eeschema API which is less well-documented
    # In a full implementation, this would create a new schematic
    print("Schematic creation not fully implemented")
    return None

# Generating manufacturing outputs
def generate_gerber_files(board: Any, output_dir: str) -> List[str]:
    """
    Generate Gerber files for manufacturing.
    
    Args:
        board: KiCad board object
        output_dir: Directory to save Gerber files
        
    Returns:
        List of generated file paths
    """
    if not KICAD_AVAILABLE:
        print(f"Would generate Gerber files in: {output_dir}")
        return []
    
    try:
        # Make sure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Create Gerber plot controller
        plot_controller = pcbnew.PLOT_CONTROLLER(board)
        plot_options = plot_controller.GetPlotOptions()
        
        # Set up plot options
        plot_options.SetOutputDirectory(output_dir)
        plot_options.SetPlotFrameRef(False)
        plot_options.SetSkipPlotNPTH_Pads(True)
        plot_options.SetPlotViaOnMaskLayer(False)
        plot_options.SetExcludeEdgeLayer(True)
        plot_options.SetUseGerberAttributes(True)
        plot_options.SetUseGerberProtelExtensions(False)
        plot_options.SetScale(1)
        plot_options.SetUseAuxOrigin(False)
        
        # Gerber files to generate
        gerber_layers = [
            ("F.Cu", pcbnew.F_Cu, "Top copper"),
            ("B.Cu", pcbnew.B_Cu, "Bottom copper"),
            ("F.Paste", pcbnew.F_Paste, "Top paste"),
            ("B.Paste", pcbnew.B_Paste, "Bottom paste"),
            ("F.SilkS", pcbnew.F_SilkS, "Top silkscreen"),
            ("B.SilkS", pcbnew.B_SilkS, "Bottom silkscreen"),
            ("F.Mask", pcbnew.F_Mask, "Top solder mask"),
            ("B.Mask", pcbnew.B_Mask, "Bottom solder mask"),
            ("Edge.Cuts", pcbnew.Edge_Cuts, "Board outline")
        ]
        
        generated_files = []
        
        # Generate each Gerber file
        for layer_info in gerber_layers:
            layer_name = layer_info[0]
            layer_id = layer_info[1]
            
            plot_controller.SetLayer(layer_id)
            plot_controller.OpenPlotfile(layer_name, pcbnew.PLOT_FORMAT_GERBER, layer_name)
            plot_controller.PlotLayer()
            generated_files.append(plot_controller.GetPlotFileName())
            plot_controller.ClosePlot()
        
        # Generate drill file
        drill_writer = pcbnew.EXCELLON_WRITER(board)
        drill_writer.SetMapFileFormat(pcbnew.PLOT_FORMAT_PDF)
        
        drill_writer.SetOptions(
            False,  # Mirror
            False,  # Minimal header
            pcbnew.wxPoint(0, 0),  # Offset
            False,  # Merge PTH and NPTH
            False,  # Numbers as drill size
            True    # 2.5 format
        )
        
        drill_writer.CreateDrillandMapFilesSet(output_dir, True, False)
        
        # Add drill files to generated files list
        drill_files = [
            os.path.join(output_dir, board.GetFileName() + "-PTH.drl"),
            os.path.join(output_dir, board.GetFileName() + "-NPTH.drl")
        ]
        
        generated_files.extend([f for f in drill_files if os.path.exists(f)])
        
        return generated_files
    
    except Exception as e:
        print(f"Error generating Gerber files: {str(e)}")
        return []

def generate_bom(board: Any, output_path: str) -> bool:
    """
    Generate a Bill of Materials (BOM) for the PCB.
    
    Args:
        board: KiCad board object
        output_path: Output file path
        
    Returns:
        True if successful, False otherwise
    """
    if not KICAD_AVAILABLE:
        print(f"Would generate BOM at: {output_path}")
        return True
    
    try:
        # Get all footprints on the board
        footprints = board.GetFootprints()
        
        # Open output file
        with open(output_path, 'w') as f:
            # Write header
            f.write("Reference,Value,Footprint,Quantity\n")
            
            # Process footprints and create BOM
            components = {}
            for fp in footprints:
                ref = fp.GetReference()
                val = fp.GetValue()
                fp_name = fp.GetFPID().GetLibItemName()
                
                # Group by value and footprint
                key = f"{val}_{fp_name}"
                if key not in components:
                    components[key] = {
                        'value': val,
                        'footprint': fp_name,
                        'references': []
                    }
                
                components[key]['references'].append(ref)
            
            # Write components to BOM
            for key, data in components.items():
                refs = ','.join(sorted(data['references']))
                qty = len(data['references'])
                f.write(f"{refs},{data['value']},{data['footprint']},{qty}\n")
        
        return True
    
    except Exception as e:
        print(f"Error generating BOM: {str(e)}")
        return False

# Design rule checking
def run_drc(board: Any) -> List[Dict]:
    """
    Run Design Rule Check on the board.
    
    Args:
        board: KiCad board object
        
    Returns:
        List of DRC violations (each as a dict with details)
    """
    if not KICAD_AVAILABLE:
        print("Would run DRC checks")
        return []
    
    try:
        # Create DRC runner
        drc = pcbnew.DRC(board)
        drc.SetViolationHandler(pcbnew.DRC_VIOLATION_HANDLER())
        
        # Run DRC tests
        drc.RunTests()
        
        # Get violations
        violations = []
        for item in drc.GetViolations():
            violation = {
                'type': item.GetViolationCode(),
                'description': item.GetMainText(),
                'location_x': kicad_units_to_mm(item.GetViolatingItem().GetPosition().x),
                'location_y': kicad_units_to_mm(item.GetViolatingItem().GetPosition().y)
            }
            violations.append(violation)
        
        return violations
    
    except Exception as e:
        print(f"Error running DRC: {str(e)}")
        return []

# Utility function to add a PCB outline
def add_board_outline(board: Any, width: float, height: float) -> bool:
    """
    Add a rectangular board outline to the PCB.
    
    Args:
        board: KiCad board object
        width: Board width in mm
        height: Board height in mm
        
    Returns:
        True if successful, False otherwise
    """
    if not KICAD_AVAILABLE:
        print(f"Would add board outline: {width}mm x {height}mm")
        return True
    
    try:
        # Convert dimensions to KiCad units
        w = mm_to_kicad_units(width)
        h = mm_to_kicad_units(height)
        
        # Create rectangle at (0,0) with width and height
        rect = pcbnew.PCB_SHAPE(board)
        rect.SetShape(pcbnew.SHAPE_T_RECT)
        rect.SetLayer(pcbnew.Edge_Cuts)
        rect.SetStart(VECTOR2I(0, 0))
        rect.SetEnd(VECTOR2I(w, h))
        rect.SetWidth(mm_to_kicad_units(0.1))  # 0.1mm line width
        
        # Add to board
        board.Add(rect)
        return True
    
    except Exception as e:
        print(f"Error adding board outline: {str(e)}")
        return False