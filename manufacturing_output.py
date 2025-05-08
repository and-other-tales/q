#!/usr/bin/env python3
"""
Manufacturing output generator for PCB designs.
Handles generation of Gerber files, drill files, BOM, and assembly documentation.
"""

import os
import csv
import json
import tempfile
import zipfile
from typing import Dict, List, Tuple, Set, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import datetime

# Try to import KiCad modules
try:
    import pcbnew
    KICAD_AVAILABLE = True
except ImportError:
    KICAD_AVAILABLE = False
    print("Warning: KiCad Python API not available. Limited manufacturing output capabilities available.")

# Import our KiCad helpers
import kicad_helpers as kh

# Import our PCB layout engine
from pcb_layout_engine import PCBLayoutEngine

@dataclass
class GerberLayer:
    """Represents a Gerber file layer."""
    name: str
    file_extension: str
    description: str
    kicad_layer_id: Optional[int] = None

@dataclass
class DrillFile:
    """Represents a drill file."""
    name: str
    file_extension: str
    description: str
    plated: bool = True

@dataclass
class BOMItem:
    """Represents an item in the Bill of Materials."""
    reference: str
    value: str
    footprint: str
    quantity: int
    manufacturer: str = ""
    part_number: str = ""
    supplier: str = ""
    supplier_part_number: str = ""
    datasheet_url: str = ""
    substitutions: List[str] = field(default_factory=list)

@dataclass
class PickAndPlaceItem:
    """Represents an item in the pick-and-place file."""
    reference: str
    value: str
    footprint: str
    position_x: float  # mm
    position_y: float  # mm
    rotation: float  # degrees
    side: str  # "top" or "bottom"

class ManufacturingOutputGenerator:
    """Generator for PCB manufacturing output files."""
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize the manufacturing output generator.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir
        self.board = None
        self.layout_engine = None
        
        # Define Gerber layers
        self.gerber_layers = [
            GerberLayer("F_Cu", "gtl", "Top Copper", pcbnew.F_Cu if KICAD_AVAILABLE else None),
            GerberLayer("B_Cu", "gbl", "Bottom Copper", pcbnew.B_Cu if KICAD_AVAILABLE else None),
            GerberLayer("F_Paste", "gtp", "Top Paste", pcbnew.F_Paste if KICAD_AVAILABLE else None),
            GerberLayer("B_Paste", "gbp", "Bottom Paste", pcbnew.B_Paste if KICAD_AVAILABLE else None),
            GerberLayer("F_SilkS", "gto", "Top Silkscreen", pcbnew.F_SilkS if KICAD_AVAILABLE else None),
            GerberLayer("B_SilkS", "gbo", "Bottom Silkscreen", pcbnew.B_SilkS if KICAD_AVAILABLE else None),
            GerberLayer("F_Mask", "gts", "Top Solder Mask", pcbnew.F_Mask if KICAD_AVAILABLE else None),
            GerberLayer("B_Mask", "gbs", "Bottom Solder Mask", pcbnew.B_Mask if KICAD_AVAILABLE else None),
            GerberLayer("Edge_Cuts", "gm1", "Board Outline", pcbnew.Edge_Cuts if KICAD_AVAILABLE else None)
        ]
        
        # Define drill files
        self.drill_files = [
            DrillFile("PTH", "drl", "Plated Through Holes", True),
            DrillFile("NPTH", "drl", "Non-Plated Through Holes", False)
        ]
    
    def set_board(self, board) -> None:
        """
        Set the KiCad board for manufacturing outputs.
        
        Args:
            board: KiCad board object
        """
        self.board = board
    
    def set_layout_engine(self, layout_engine: PCBLayoutEngine) -> None:
        """
        Set the PCB layout engine.
        
        Args:
            layout_engine: PCB layout engine
        """
        self.layout_engine = layout_engine
        
        # If layout engine has a board and KiCad is available, use it
        if layout_engine and layout_engine.board and KICAD_AVAILABLE:
            self.board = layout_engine.board
    
    def load_board(self, board_file: str) -> bool:
        """
        Load a KiCad PCB file.
        
        Args:
            board_file: Path to KiCad PCB file
        
        Returns:
            True if successful, False otherwise
        """
        if not KICAD_AVAILABLE:
            print(f"KiCad Python API not available. Cannot load board from {board_file}")
            return False
        
        try:
            self.board = pcbnew.LoadBoard(board_file)
            return True
        except Exception as e:
            print(f"Error loading board: {e}")
            return False
    
    def generate_gerber_files(self) -> List[str]:
        """
        Generate Gerber files for PCB manufacturing.
        
        Returns:
            List of generated file paths
        """
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # If we have a KiCad board, use KiCad's Gerber generator
        if KICAD_AVAILABLE and self.board:
            return self._generate_gerber_files_kicad()
        
        # Simulated Gerber generation
        return self._generate_gerber_files_simulated()
    
    def _generate_gerber_files_kicad(self) -> List[str]:
        """
        Generate Gerber files using KiCad's native functions.
        
        Returns:
            List of generated file paths
        """
        generated_files = []
        
        try:
            # Create plot controller
            plot_controller = pcbnew.PLOT_CONTROLLER(self.board)
            plot_options = plot_controller.GetPlotOptions()
            
            # Set up plot options
            plot_options.SetOutputDirectory(self.output_dir)
            plot_options.SetPlotFrameRef(False)
            plot_options.SetSkipPlotNPTH_Pads(False)
            plot_options.SetPlotViaOnMaskLayer(False)
            plot_options.SetExcludeEdgeLayer(True)
            plot_options.SetUseGerberAttributes(True)
            plot_options.SetUseGerberProtelExtensions(False)
            plot_options.SetScale(1)
            plot_options.SetUseAuxOrigin(False)
            
            # Get board base filename
            board_filename = os.path.splitext(os.path.basename(self.board.GetFileName()))[0]
            if not board_filename:
                board_filename = "pcb"
            
            # Plot each Gerber layer
            for layer in self.gerber_layers:
                if layer.kicad_layer_id is None:
                    continue
                
                plot_controller.SetLayer(layer.kicad_layer_id)
                plot_controller.OpenPlotfile(layer.name, pcbnew.PLOT_FORMAT_GERBER, layer.description)
                plot_controller.PlotLayer()
                
                # Get generated file path
                file_path = os.path.join(self.output_dir, f"{board_filename}-{layer.name}.{layer.file_extension}")
                plot_file = plot_controller.GetPlotFileName()
                
                # Rename file to match expected extensions if needed
                if os.path.exists(plot_file) and os.path.normpath(plot_file) != os.path.normpath(file_path):
                    os.rename(plot_file, file_path)
                    generated_files.append(file_path)
                else:
                    generated_files.append(plot_file)
                
                plot_controller.ClosePlot()
            
            # Generate drill files
            drill_writer = pcbnew.EXCELLON_WRITER(self.board)
            drill_writer.SetMapFileFormat(pcbnew.PLOT_FORMAT_PDF)
            
            # Drill options
            drill_writer.SetOptions(
                False,  # Mirror
                False,  # Minimal header
                pcbnew.wxPoint(0, 0),  # Offset
                False,  # Merge PTH and NPTH
                False,  # Numbers as drill size
                True    # 2.5 format
            )
            
            # Create drill and map files
            drill_writer.CreateDrillandMapFilesSet(self.output_dir, True, False)
            
            # Add drill files to the list
            for drill_file in self.drill_files:
                file_path = os.path.join(self.output_dir, f"{board_filename}-{drill_file.name}.{drill_file.file_extension}")
                if os.path.exists(file_path):
                    generated_files.append(file_path)
            
            return generated_files
        
        except Exception as e:
            print(f"Error generating Gerber files: {e}")
            return generated_files
    
    def _generate_gerber_files_simulated(self) -> List[str]:
        """
        Simulate Gerber file generation (when KiCad is not available).
        
        Returns:
            List of simulated file paths
        """
        generated_files = []
        
        try:
            # Dummy file creation for simulation
            for layer in self.gerber_layers:
                file_path = os.path.join(self.output_dir, f"simulated-{layer.name}.{layer.file_extension}")
                
                with open(file_path, 'w') as f:
                    f.write(f"% Simulated Gerber file for {layer.description}\n")
                    f.write("% Created by Manufacturing Output Generator\n")
                    f.write(f"% {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    
                    # Add some dummy Gerber commands
                    f.write("G04 Begin of file*\n")
                    f.write("%TF.GenerationSoftware,KiCad,Pcbnew,(6.0.0)*%\n")
                    f.write("%TF.SameCoordinates,Original*%\n")
                    f.write("%TF.FileFunction,{layer_function}*%\n".replace("{layer_function}", layer.description))
                    f.write("%FSLAX46Y46*%\n")
                    f.write("G04 Gerber Fmt 4.6, Leading zero omitted, Abs format (unit mm)*\n")
                    f.write("G04 Created by Manufacturing Output Generator*\n")
                    f.write("%MOMM*%\n")
                    f.write("%LPD*%\n")
                    f.write("G04 APERTURE LIST*\n")
                    f.write("%ADD10C,0.150000*%\n")
                    f.write("G04 APERTURE END LIST*\n")
                    f.write("D10*\n")
                    
                    # Draw a simple outline for demonstration
                    f.write("X0Y0D02*\n")
                    f.write("X100000000Y0D01*\n")
                    f.write("X100000000Y80000000D01*\n")
                    f.write("X0Y80000000D01*\n")
                    f.write("X0Y0D01*\n")
                    f.write("M02*\n")
                
                generated_files.append(file_path)
            
            # Create drill files
            for drill_file in self.drill_files:
                file_path = os.path.join(self.output_dir, f"simulated-{drill_file.name}.{drill_file.file_extension}")
                
                with open(file_path, 'w') as f:
                    f.write(f"; Simulated drill file for {drill_file.description}\n")
                    f.write("; Created by Manufacturing Output Generator\n")
                    f.write(f"; {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("M48\n")
                    f.write("; DRILL file {units} mm\n".replace("{units}", "METRIC"))
                    f.write("FMAT, 2\n")
                    f.write("METRIC, TZ\n")
                    f.write("T1C0.400\n")
                    f.write("T2C1.000\n")
                    f.write("%\n")
                    f.write("G90\n")
                    f.write("G05\n")
                    f.write("T1\n")
                    f.write("X10.0Y10.0\n")
                    f.write("X20.0Y10.0\n")
                    f.write("X10.0Y20.0\n")
                    f.write("T2\n")
                    f.write("X50.0Y50.0\n")
                    f.write("T0\n")
                    f.write("M30\n")
                
                generated_files.append(file_path)
            
            return generated_files
        
        except Exception as e:
            print(f"Error generating simulated Gerber files: {e}")
            return generated_files
    
    def generate_bom(self, output_format: str = "csv") -> Optional[str]:
        """
        Generate a Bill of Materials.
        
        Args:
            output_format: Output format ("csv", "json", or "html")
        
        Returns:
            Path to generated BOM file or None if failed
        """
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get filename base
        if KICAD_AVAILABLE and self.board:
            base_filename = os.path.splitext(os.path.basename(self.board.GetFileName()))[0]
            if not base_filename:
                base_filename = "pcb"
        else:
            base_filename = "pcb"
        
        # Output file path
        output_file = os.path.join(self.output_dir, f"{base_filename}_bom.{output_format}")
        
        # Generate BOM items
        bom_items = self._generate_bom_items()
        
        # If no items, return None
        if not bom_items:
            print("No components found for BOM")
            return None
        
        try:
            # Write BOM in specified format
            if output_format == "csv":
                return self._write_bom_csv(bom_items, output_file)
            elif output_format == "json":
                return self._write_bom_json(bom_items, output_file)
            elif output_format == "html":
                return self._write_bom_html(bom_items, output_file)
            else:
                print(f"Unsupported BOM format: {output_format}")
                return None
        
        except Exception as e:
            print(f"Error generating BOM: {e}")
            return None
    
    def _generate_bom_items(self) -> List[BOMItem]:
        """
        Generate BOM items from the board.
        
        Returns:
            List of BOM items
        """
        bom_items = []
        
        # Get components from KiCad board
        if KICAD_AVAILABLE and self.board:
            # Get all footprints
            footprints = self.board.GetFootprints()
            
            # Group by value and footprint
            components = {}
            for fp in footprints:
                ref = fp.GetReference()
                val = fp.GetValue()
                fp_name = fp.GetFPID().GetLibItemName()
                
                # Group key
                key = f"{val}_{fp_name}"
                
                if key not in components:
                    components[key] = {
                        'value': val,
                        'footprint': fp_name,
                        'references': []
                    }
                
                components[key]['references'].append(ref)
            
            # Create BOM items
            for key, data in components.items():
                # Sort references
                references = sorted(data['references'], key=lambda x: (x.rstrip('0123456789'), int(x[len(x.rstrip('0123456789')):] or 0)))
                
                # Create BOM item
                item = BOMItem(
                    reference=",".join(references),
                    value=data['value'],
                    footprint=data['footprint'],
                    quantity=len(references)
                )
                
                bom_items.append(item)
        
        # Get components from layout engine
        elif self.layout_engine:
            # Group by value and footprint
            components = {}
            for component in self.layout_engine.components:
                ref = component.reference
                val = component.reference.split('_')[1] if '_' in component.reference else ""
                fp_name = component.footprint_name
                
                # Group key
                key = f"{val}_{fp_name}"
                
                if key not in components:
                    components[key] = {
                        'value': val,
                        'footprint': fp_name,
                        'references': []
                    }
                
                components[key]['references'].append(ref)
            
            # Create BOM items
            for key, data in components.items():
                # Sort references
                references = sorted(data['references'], key=lambda x: (x.rstrip('0123456789'), int(x[len(x.rstrip('0123456789')):] or 0)))
                
                # Create BOM item
                item = BOMItem(
                    reference=",".join(references),
                    value=data['value'],
                    footprint=data['footprint'],
                    quantity=len(references)
                )
                
                bom_items.append(item)
        
        return bom_items
    
    def _write_bom_csv(self, bom_items: List[BOMItem], output_file: str) -> str:
        """
        Write BOM to CSV file.
        
        Args:
            bom_items: List of BOM items
            output_file: Output file path
        
        Returns:
            Path to generated file
        """
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['Reference', 'Value', 'Footprint', 'Quantity', 
                          'Manufacturer', 'Part Number', 'Supplier', 
                          'Supplier Part Number', 'Datasheet']
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in bom_items:
                writer.writerow({
                    'Reference': item.reference,
                    'Value': item.value,
                    'Footprint': item.footprint,
                    'Quantity': item.quantity,
                    'Manufacturer': item.manufacturer,
                    'Part Number': item.part_number,
                    'Supplier': item.supplier,
                    'Supplier Part Number': item.supplier_part_number,
                    'Datasheet': item.datasheet_url
                })
        
        return output_file
    
    def _write_bom_json(self, bom_items: List[BOMItem], output_file: str) -> str:
        """
        Write BOM to JSON file.
        
        Args:
            bom_items: List of BOM items
            output_file: Output file path
        
        Returns:
            Path to generated file
        """
        # Convert to dicts
        items_dict = []
        for item in bom_items:
            items_dict.append({
                'reference': item.reference,
                'value': item.value,
                'footprint': item.footprint,
                'quantity': item.quantity,
                'manufacturer': item.manufacturer,
                'part_number': item.part_number,
                'supplier': item.supplier,
                'supplier_part_number': item.supplier_part_number,
                'datasheet_url': item.datasheet_url,
                'substitutions': item.substitutions
            })
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(items_dict, f, indent=2)
        
        return output_file
    
    def _write_bom_html(self, bom_items: List[BOMItem], output_file: str) -> str:
        """
        Write BOM to HTML file.
        
        Args:
            bom_items: List of BOM items
            output_file: Output file path
        
        Returns:
            Path to generated file
        """
        with open(output_file, 'w') as f:
            # Write HTML header
            f.write("<!DOCTYPE html>\n")
            f.write("<html>\n")
            f.write("<head>\n")
            f.write("  <title>Bill of Materials</title>\n")
            f.write("  <style>\n")
            f.write("    body { font-family: Arial, sans-serif; margin: 20px; }\n")
            f.write("    h1 { color: #333; }\n")
            f.write("    table { border-collapse: collapse; width: 100%; }\n")
            f.write("    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n")
            f.write("    th { background-color: #f2f2f2; }\n")
            f.write("    tr:nth-child(even) { background-color: #f9f9f9; }\n")
            f.write("  </style>\n")
            f.write("</head>\n")
            f.write("<body>\n")
            f.write("  <h1>Bill of Materials</h1>\n")
            f.write(f"  <p>Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
            
            # Write BOM table
            f.write("  <table>\n")
            f.write("    <tr>\n")
            f.write("      <th>Item</th>\n")
            f.write("      <th>Reference</th>\n")
            f.write("      <th>Value</th>\n")
            f.write("      <th>Footprint</th>\n")
            f.write("      <th>Quantity</th>\n")
            f.write("      <th>Manufacturer</th>\n")
            f.write("      <th>Part Number</th>\n")
            f.write("      <th>Supplier</th>\n")
            f.write("      <th>Supplier Part</th>\n")
            f.write("      <th>Datasheet</th>\n")
            f.write("    </tr>\n")
            
            # Write BOM items
            for i, item in enumerate(bom_items, 1):
                f.write("    <tr>\n")
                f.write(f"      <td>{i}</td>\n")
                f.write(f"      <td>{item.reference}</td>\n")
                f.write(f"      <td>{item.value}</td>\n")
                f.write(f"      <td>{item.footprint}</td>\n")
                f.write(f"      <td>{item.quantity}</td>\n")
                f.write(f"      <td>{item.manufacturer}</td>\n")
                f.write(f"      <td>{item.part_number}</td>\n")
                f.write(f"      <td>{item.supplier}</td>\n")
                f.write(f"      <td>{item.supplier_part_number}</td>\n")
                
                # Check if datasheet URL is available
                if item.datasheet_url:
                    f.write(f"      <td><a href=\"{item.datasheet_url}\" target=\"_blank\">Datasheet</a></td>\n")
                else:
                    f.write("      <td></td>\n")
                
                f.write("    </tr>\n")
            
            f.write("  </table>\n")
            f.write("</body>\n")
            f.write("</html>\n")
        
        return output_file
    
    def generate_pick_and_place(self, output_format: str = "csv") -> Optional[str]:
        """
        Generate a pick-and-place (centroid) file.
        
        Args:
            output_format: Output format ("csv" or "json")
        
        Returns:
            Path to generated file or None if failed
        """
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get filename base
        if KICAD_AVAILABLE and self.board:
            base_filename = os.path.splitext(os.path.basename(self.board.GetFileName()))[0]
            if not base_filename:
                base_filename = "pcb"
        else:
            base_filename = "pcb"
        
        # Output file path
        output_file = os.path.join(self.output_dir, f"{base_filename}_position.{output_format}")
        
        # Generate pick-and-place items
        pnp_items = self._generate_pick_and_place_items()
        
        # If no items, return None
        if not pnp_items:
            print("No components found for pick-and-place file")
            return None
        
        try:
            # Write pick-and-place in specified format
            if output_format == "csv":
                return self._write_pnp_csv(pnp_items, output_file)
            elif output_format == "json":
                return self._write_pnp_json(pnp_items, output_file)
            else:
                print(f"Unsupported pick-and-place format: {output_format}")
                return None
        
        except Exception as e:
            print(f"Error generating pick-and-place file: {e}")
            return None
    
    def _generate_pick_and_place_items(self) -> List[PickAndPlaceItem]:
        """
        Generate pick-and-place items from the board.
        
        Returns:
            List of pick-and-place items
        """
        pnp_items = []
        
        # Get components from KiCad board
        if KICAD_AVAILABLE and self.board:
            # Get all footprints
            footprints = self.board.GetFootprints()
            
            for fp in footprints:
                ref = fp.GetReference()
                val = fp.GetValue()
                fp_name = fp.GetFPID().GetLibItemName()
                
                # Get position
                pos = fp.GetPosition()
                pos_x = pcbnew.ToMM(pos.x)
                pos_y = pcbnew.ToMM(pos.y)
                
                # Get rotation
                rot = fp.GetOrientation() / 10.0  # KiCad uses tenths of a degree
                
                # Get side
                side = "top"
                if fp.GetLayer() == pcbnew.B_Cu:
                    side = "bottom"
                
                # Skip virtual components, mounting holes, fiducials, etc.
                skip_refs = ["MH", "FID"]
                if any(ref.startswith(skip) for skip in skip_refs):
                    continue
                
                # Create pick-and-place item
                item = PickAndPlaceItem(
                    reference=ref,
                    value=val,
                    footprint=fp_name,
                    position_x=pos_x,
                    position_y=pos_y,
                    rotation=rot,
                    side=side
                )
                
                pnp_items.append(item)
        
        # Get components from layout engine
        elif self.layout_engine:
            for component in self.layout_engine.components:
                ref = component.reference
                val = component.reference.split('_')[1] if '_' in component.reference else ""
                fp_name = component.footprint_name
                
                # Get position
                pos_x = component.position[0]
                pos_y = component.position[1]
                
                # Get rotation
                rot = component.rotation
                
                # Get side
                side = component.layer
                if side != "top" and side != "bottom":
                    side = "top"  # Default to top
                
                # Skip virtual components, mounting holes, fiducials, etc.
                skip_refs = ["MH", "FID"]
                if any(ref.startswith(skip) for skip in skip_refs):
                    continue
                
                # Create pick-and-place item
                item = PickAndPlaceItem(
                    reference=ref,
                    value=val,
                    footprint=fp_name,
                    position_x=pos_x,
                    position_y=pos_y,
                    rotation=rot,
                    side=side
                )
                
                pnp_items.append(item)
        
        return pnp_items
    
    def _write_pnp_csv(self, pnp_items: List[PickAndPlaceItem], output_file: str) -> str:
        """
        Write pick-and-place to CSV file.
        
        Args:
            pnp_items: List of pick-and-place items
            output_file: Output file path
        
        Returns:
            Path to generated file
        """
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['Designator', 'Value', 'Footprint', 'X(mm)', 'Y(mm)', 'Rotation', 'Layer']
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in pnp_items:
                writer.writerow({
                    'Designator': item.reference,
                    'Value': item.value,
                    'Footprint': item.footprint,
                    'X(mm)': f"{item.position_x:.3f}",
                    'Y(mm)': f"{item.position_y:.3f}",
                    'Rotation': f"{item.rotation:.2f}",
                    'Layer': item.side
                })
        
        return output_file
    
    def _write_pnp_json(self, pnp_items: List[PickAndPlaceItem], output_file: str) -> str:
        """
        Write pick-and-place to JSON file.
        
        Args:
            pnp_items: List of pick-and-place items
            output_file: Output file path
        
        Returns:
            Path to generated file
        """
        # Convert to dicts
        items_dict = []
        for item in pnp_items:
            items_dict.append({
                'reference': item.reference,
                'value': item.value,
                'footprint': item.footprint,
                'position_x': item.position_x,
                'position_y': item.position_y,
                'rotation': item.rotation,
                'side': item.side
            })
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(items_dict, f, indent=2)
        
        return output_file
    
    def generate_assembly_drawings(self) -> List[str]:
        """
        Generate assembly drawings.
        
        Returns:
            List of generated file paths
        """
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get filename base
        if KICAD_AVAILABLE and self.board:
            base_filename = os.path.splitext(os.path.basename(self.board.GetFileName()))[0]
            if not base_filename:
                base_filename = "pcb"
        else:
            base_filename = "pcb"
        
        # Output file paths
        top_file = os.path.join(self.output_dir, f"{base_filename}_assembly_top.pdf")
        bottom_file = os.path.join(self.output_dir, f"{base_filename}_assembly_bottom.pdf")
        
        generated_files = []
        
        # Generate assembly drawings using KiCad
        if KICAD_AVAILABLE and self.board:
            try:
                # Create plot controller
                plot_controller = pcbnew.PLOT_CONTROLLER(self.board)
                plot_options = plot_controller.GetPlotOptions()
                
                # Set up plot options for assembly drawings
                plot_options.SetOutputDirectory(self.output_dir)
                plot_options.SetPlotFrameRef(True)
                plot_options.SetPlotValue(True)
                plot_options.SetPlotReference(True)
                plot_options.SetPlotInvisibleText(False)
                plot_options.SetPlotViaOnMaskLayer(False)
                plot_options.SetExcludeEdgeLayer(False)
                plot_options.SetScale(1)
                plot_options.SetUseAuxOrigin(False)
                plot_options.SetMirror(False)
                plot_options.SetNegative(False)
                plot_options.SetPlotPadsOnSilkLayer(True)
                
                # Set layers for assembly drawing
                # Top side assembly drawing
                plot_controller.SetColorMode(True)  # Plot in color
                
                # Plot top assembly
                plot_controller.OpenPlotfile("Assembly_Top", pcbnew.PLOT_FORMAT_PDF, "Assembly Top")
                
                # Create a custom layer set for top assembly
                layers_set = pcbnew.LSET()
                layers_set.AddLayer(pcbnew.F_SilkS)
                layers_set.AddLayer(pcbnew.F_Fab)
                layers_set.AddLayer(pcbnew.Edge_Cuts)
                
                plot_controller.SetLayer(pcbnew.F_SilkS)  # Dummy, the layers set will be used instead
                plot_controller.PlotLayers(layers_set)
                plot_controller.ClosePlot()
                
                generated_files.append(os.path.join(self.output_dir, "Assembly_Top.pdf"))
                
                # Plot bottom assembly
                plot_controller.OpenPlotfile("Assembly_Bottom", pcbnew.PLOT_FORMAT_PDF, "Assembly Bottom")
                
                # Create a custom layer set for bottom assembly
                layers_set = pcbnew.LSET()
                layers_set.AddLayer(pcbnew.B_SilkS)
                layers_set.AddLayer(pcbnew.B_Fab)
                layers_set.AddLayer(pcbnew.Edge_Cuts)
                
                # Set mirrored mode for bottom view
                plot_options.SetMirror(True)
                
                plot_controller.SetLayer(pcbnew.B_SilkS)  # Dummy, the layers set will be used instead
                plot_controller.PlotLayers(layers_set)
                plot_controller.ClosePlot()
                
                generated_files.append(os.path.join(self.output_dir, "Assembly_Bottom.pdf"))
            
            except Exception as e:
                print(f"Error generating assembly drawings: {e}")
        
        # If KiCad is not available or failed, create simplified placeholder files
        if not generated_files:
            try:
                # Create simple placeholder files
                for side in ["top", "bottom"]:
                    file_path = os.path.join(self.output_dir, f"{base_filename}_assembly_{side}.txt")
                    
                    with open(file_path, 'w') as f:
                        f.write(f"Assembly drawing for {side} side\n")
                        f.write(f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        
                        # List components
                        f.write("Components:\n")
                        
                        if self.layout_engine:
                            for component in self.layout_engine.components:
                                if component.layer == side:
                                    f.write(f"{component.reference}: {component.footprint_name} at ({component.position[0]:.2f}, {component.position[1]:.2f}) rotation {component.rotation:.1f}°\n")
                    
                    generated_files.append(file_path)
            
            except Exception as e:
                print(f"Error generating placeholder assembly files: {e}")
        
        return generated_files
    
    def generate_fabrication_notes(self) -> Optional[str]:
        """
        Generate fabrication notes.
        
        Returns:
            Path to generated file or None if failed
        """
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get filename base
        if KICAD_AVAILABLE and self.board:
            base_filename = os.path.splitext(os.path.basename(self.board.GetFileName()))[0]
            if not base_filename:
                base_filename = "pcb"
        else:
            base_filename = "pcb"
        
        # Output file path
        output_file = os.path.join(self.output_dir, f"{base_filename}_fabrication_notes.txt")
        
        try:
            with open(output_file, 'w') as f:
                f.write("PCB Fabrication Notes\n")
                f.write("====================\n\n")
                f.write(f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Board specifications
                f.write("Board Specifications:\n")
                f.write("-------------------\n")
                
                if KICAD_AVAILABLE and self.board:
                    # Get board dimensions
                    board_edge_coords = []
                    for drawing in self.board.GetDrawings():
                        if drawing.GetLayer() == pcbnew.Edge_Cuts:
                            if drawing.GetShape() == pcbnew.S_SEGMENT:
                                board_edge_coords.extend([
                                    (pcbnew.ToMM(drawing.GetStart().x), pcbnew.ToMM(drawing.GetStart().y)),
                                    (pcbnew.ToMM(drawing.GetEnd().x), pcbnew.ToMM(drawing.GetEnd().y))
                                ])
                    
                    if board_edge_coords:
                        min_x = min(x for x, y in board_edge_coords)
                        max_x = max(x for x, y in board_edge_coords)
                        min_y = min(y for x, y in board_edge_coords)
                        max_y = max(y for x, y in board_edge_coords)
                        
                        width = max_x - min_x
                        height = max_y - min_y
                        
                        f.write(f"- Board dimensions: {width:.2f} x {height:.2f} mm\n")
                    
                    # Get layer count
                    layer_count = self.board.GetCopperLayerCount()
                    f.write(f"- Number of copper layers: {layer_count}\n")
                    
                    # Get board thickness
                    design_settings = self.board.GetDesignSettings()
                    thickness = design_settings.GetBoardThickness() / 1000000.0  # Convert to mm
                    f.write(f"- Board thickness: {thickness:.2f} mm\n")
                    
                    # Get trace width and clearance
                    min_track_width = pcbnew.ToMM(design_settings.m_TrackMinWidth)
                    min_clearance = pcbnew.ToMM(design_settings.m_MinClearance)
                    f.write(f"- Minimum trace width: {min_track_width:.3f} mm\n")
                    f.write(f"- Minimum clearance: {min_clearance:.3f} mm\n")
                
                elif self.layout_engine:
                    # Get board dimensions from layout engine
                    if self.layout_engine.board_outline:
                        width = self.layout_engine.board_outline.width
                        height = self.layout_engine.board_outline.height
                        f.write(f"- Board dimensions: {width:.2f} x {height:.2f} mm\n")
                    
                    # Get layer count
                    f.write(f"- Number of copper layers: {self.layout_engine.layer_count}\n")
                    
                    # Get trace width and clearance
                    f.write(f"- Minimum trace width: {self.layout_engine.min_track_width:.3f} mm\n")
                    f.write(f"- Minimum clearance: {self.layout_engine.min_clearance:.3f} mm\n")
                
                else:
                    f.write("- Board dimensions: [NOT AVAILABLE]\n")
                    f.write("- Number of copper layers: 2\n")
                    f.write("- Board thickness: 1.6 mm\n")
                    f.write("- Minimum trace width: 0.2 mm\n")
                    f.write("- Minimum clearance: 0.2 mm\n")
                
                # Default specifications
                f.write("- Material: FR4\n")
                f.write("- Copper weight: 1 oz\n")
                f.write("- Surface finish: HASL lead-free\n")
                f.write("- Silkscreen color: White\n")
                f.write("- Soldermask color: Green\n")
                
                # Special instructions
                f.write("\nSpecial Instructions:\n")
                f.write("-------------------\n")
                f.write("1. Follow IPC-6012 Class 2 standards\n")
                f.write("2. Perform 100% electrical test\n")
                f.write("3. Include fabrication panel rails if quantity > 1\n")
                
                # File information
                f.write("\nFile Information:\n")
                f.write("---------------\n")
                f.write("- Gerber files: RS-274X format\n")
                f.write("- Excellon drill files: 2.4 format, absolute coordinates\n")
                f.write("- Units: Millimeters\n")
                
                # Layer stackup
                f.write("\nLayer Stackup:\n")
                f.write("-------------\n")
                
                if KICAD_AVAILABLE and self.board:
                    layer_count = self.board.GetCopperLayerCount()
                elif self.layout_engine:
                    layer_count = self.layout_engine.layer_count
                else:
                    layer_count = 2
                
                if layer_count == 2:
                    f.write("1. Top Copper\n")
                    f.write("2. FR4\n")
                    f.write("3. Bottom Copper\n")
                elif layer_count == 4:
                    f.write("1. Top Copper\n")
                    f.write("2. Prepreg\n")
                    f.write("3. Inner Layer 1\n")
                    f.write("4. Core\n")
                    f.write("5. Inner Layer 2\n")
                    f.write("6. Prepreg\n")
                    f.write("7. Bottom Copper\n")
                elif layer_count == 6:
                    f.write("1. Top Copper\n")
                    f.write("2. Prepreg\n")
                    f.write("3. Inner Layer 1\n")
                    f.write("4. Prepreg\n")
                    f.write("5. Inner Layer 2\n")
                    f.write("6. Core\n")
                    f.write("7. Inner Layer 3\n")
                    f.write("8. Prepreg\n")
                    f.write("9. Inner Layer 4\n")
                    f.write("10. Prepreg\n")
                    f.write("11. Bottom Copper\n")
                
                # Gerber file descriptions
                f.write("\nGerber File Descriptions:\n")
                f.write("-----------------------\n")
                for layer in self.gerber_layers:
                    f.write(f"- *.{layer.file_extension}: {layer.description}\n")
                
                # Drill file descriptions
                f.write("\nDrill File Descriptions:\n")
                f.write("----------------------\n")
                for drill in self.drill_files:
                    f.write(f"- *-{drill.name}.{drill.file_extension}: {drill.description}\n")
            
            return output_file
        
        except Exception as e:
            print(f"Error generating fabrication notes: {e}")
            return None
    
    def generate_manufacturing_package(self, include_source_files: bool = False) -> Optional[str]:
        """
        Generate a complete manufacturing package as a ZIP file.
        
        Args:
            include_source_files: Whether to include source files (KiCad project files)
        
        Returns:
            Path to generated ZIP file or None if failed
        """
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get filename base
        if KICAD_AVAILABLE and self.board:
            base_filename = os.path.splitext(os.path.basename(self.board.GetFileName()))[0]
            if not base_filename:
                base_filename = "pcb"
        else:
            base_filename = "pcb"
        
        # Output file path
        output_file = os.path.join(self.output_dir, f"{base_filename}_manufacturing.zip")
        
        try:
            # Generate all necessary files
            gerber_files = self.generate_gerber_files()
            bom_file = self.generate_bom("csv")
            bom_html_file = self.generate_bom("html")
            pnp_file = self.generate_pick_and_place("csv")
            assembly_files = self.generate_assembly_drawings()
            fab_notes_file = self.generate_fabrication_notes()
            
            # Create ZIP file
            with zipfile.ZipFile(output_file, 'w') as zipf:
                # Add all generated files
                for file_path in gerber_files:
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
                
                if bom_file and os.path.exists(bom_file):
                    zipf.write(bom_file, os.path.basename(bom_file))
                
                if bom_html_file and os.path.exists(bom_html_file):
                    zipf.write(bom_html_file, os.path.basename(bom_html_file))
                
                if pnp_file and os.path.exists(pnp_file):
                    zipf.write(pnp_file, os.path.basename(pnp_file))
                
                for file_path in assembly_files:
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
                
                if fab_notes_file and os.path.exists(fab_notes_file):
                    zipf.write(fab_notes_file, os.path.basename(fab_notes_file))
                
                # Include source files if requested
                if include_source_files and KICAD_AVAILABLE and self.board:
                    board_file = self.board.GetFileName()
                    if os.path.exists(board_file):
                        zipf.write(board_file, f"source/{os.path.basename(board_file)}")
                    
                    # Add schematic file if it exists
                    schematic_file = board_file.replace(".kicad_pcb", ".kicad_sch")
                    if os.path.exists(schematic_file):
                        zipf.write(schematic_file, f"source/{os.path.basename(schematic_file)}")
                    
                    # Add project file if it exists
                    project_file = board_file.replace(".kicad_pcb", ".kicad_pro")
                    if os.path.exists(project_file):
                        zipf.write(project_file, f"source/{os.path.basename(project_file)}")
            
            print(f"Manufacturing package generated: {output_file}")
            return output_file
        
        except Exception as e:
            print(f"Error generating manufacturing package: {e}")
            return None

# Main function for demonstration
def demo():
    """Run a demonstration of the manufacturing output generator."""
    # Import PCB layout engine (for the demo)
    import pcb_layout_engine as ple
    
    # Create a simple PCB layout
    engine = ple.PCBLayoutEngine()
    engine.set_board_outline(100.0, 80.0)  # 100x80mm board
    
    # Add some components
    components = [
        ple.ComponentPlacement(
            component_id="U1_ATmega328P",
            reference="U1",
            footprint_name="TQFP-32_7x7mm_P0.8mm",
            position=(50.0, 40.0),
            rotation=0.0,
            layer="top",
            fixed=True  # Fix the microcontroller in the center
        ),
        ple.ComponentPlacement(
            component_id="R1_10k",
            reference="R1",
            footprint_name="R_0805_2012Metric",
            position=(30.0, 30.0),
            rotation=0.0,
            layer="top"
        ),
        ple.ComponentPlacement(
            component_id="R2_10k",
            reference="R2",
            footprint_name="R_0805_2012Metric",
            position=(30.0, 40.0),
            rotation=0.0,
            layer="top"
        ),
        ple.ComponentPlacement(
            component_id="C1_100n",
            reference="C1",
            footprint_name="C_0805_2012Metric",
            position=(60.0, 30.0),
            rotation=90.0,
            layer="top"
        ),
        ple.ComponentPlacement(
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
        ple.NetConnection(
            net_name="VCC",
            source_component="U1",
            source_pad="7",
            target_component="R1",
            target_pad="1"
        ),
        ple.NetConnection(
            net_name="GND",
            source_component="U1",
            source_pad="8",
            target_component="C1",
            target_pad="2"
        ),
        ple.NetConnection(
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
    
    # Create manufacturing output generator
    generator = ManufacturingOutputGenerator(output_dir="manufacturing_output")
    
    # Set layout engine
    generator.set_layout_engine(engine)
    
    # Generate manufacturing package
    print("Generating manufacturing package...")
    generator.generate_manufacturing_package()
    
    print("Demo completed.")

if __name__ == "__main__":
    demo()