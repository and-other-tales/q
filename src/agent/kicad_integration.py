# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""
KiCad integration module for PCB design automation.
Provides functionality for schematic and PCB creation using KiCad APIs.
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import subprocess
import tempfile

from .component_db import Component


class KiCadSchematic:
    """Handles KiCad schematic creation and manipulation."""
    
    def __init__(self, output_dir: str):
        """Initialize schematic handler."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.schematic_file = self.output_dir / "design.kicad_sch"
        self.symbol_lib_table = self.output_dir / "sym-lib-table"
        
    def create_basic_schematic(self, components: List[Component], 
                             design_name: str = "PCB_Design") -> str:
        """Create a basic KiCad schematic file."""
        
        # KiCad 7+ schematic format (simplified)
        schematic_content = f'''(kicad_sch
  (version 20230121)
  (generator "Othertales Q PCB Agent")
  (general
    (project_name "{design_name}")
  )
  (page "A4")
  
  (lib_symbols
'''
        
        # Add symbol definitions for components
        symbol_id = 1
        component_symbols = {}
        
        for component in components:
            symbol_name = f"Symbol_{symbol_id}"
            component_symbols[component.part_number] = symbol_name
            
            schematic_content += f'''    (symbol "{symbol_name}"
      (pin_names (offset 1.016))
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "{component.category[0]}"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "{component.name}"
        (at 0 -2.54 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "{component.footprint or 'Package_DIP:DIP-8_W7.62mm'}"
        (at 0 -5.08 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "{component.datasheet_url or ''}"
        (at 0 -7.62 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "{symbol_name}_0_1"
        (rectangle (start -5.08 5.08) (end 5.08 -5.08)
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
      )
      (symbol "{symbol_name}_1_1"
        (pin input line (at -7.62 2.54 0) (length 2.54)
          (name "IN" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin output line (at 7.62 2.54 180) (length 2.54)
          (name "OUT" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
      )
    )
'''
            symbol_id += 1
        
        schematic_content += '''  )
  
  (junction (at 100 100) (diameter 0) (color 0 0 0 0)
    (uuid "12345678-1234-1234-1234-123456789abc")
  )
  
'''
        
        # Add component instances
        instance_id = 1
        x_pos = 50
        y_pos = 50
        
        for component in components:
            symbol_name = component_symbols[component.part_number]
            ref_prefix = component.category[0] if component.category else "U"
            
            schematic_content += f'''  (symbol
    (lib_id "{symbol_name}")
    (at {x_pos} {y_pos} 0)
    (unit 1)
    (exclude_from_sim no)
    (in_bom yes)
    (on_board yes)
    (dnp no)
    (uuid "component-{instance_id:08d}-1234-1234-1234-123456789abc")
    (property "Reference" "{ref_prefix}{instance_id}"
      (at {x_pos} {y_pos - 7.62} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "{component.name}"
      (at {x_pos} {y_pos + 7.62} 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" "{component.footprint or 'Package_DIP:DIP-8_W7.62mm'}"
      (at {x_pos} {y_pos} 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Datasheet" "{component.datasheet_url or ''}"
      (at {x_pos} {y_pos} 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (pin "1" (uuid "pin-{instance_id:08d}-1234-1234-1234-123456789abc"))
    (pin "2" (uuid "pin-{instance_id:08d}-1234-1234-1234-123456789abd"))
    (instances
      (project "design"
        (path "/")
        (reference "{ref_prefix}{instance_id}")
        (unit 1)
      )
    )
  )
  
'''
            instance_id += 1
            x_pos += 25
            if x_pos > 200:
                x_pos = 50
                y_pos += 25
        
        # Add basic connections (simplified)
        schematic_content += '''  (wire (pts (xy 80 50) (xy 100 50))
    (stroke (width 0) (type default))
    (uuid "wire-12345678-1234-1234-1234-123456789abc")
  )
  
'''
        
        # Close the schematic
        schematic_content += ")\n"
        
        # Write schematic file
        with open(self.schematic_file, 'w') as f:
            f.write(schematic_content)
        
        # Create symbol library table
        sym_lib_content = '''(sym_lib_table
  (version 7)
  (lib (name "design") (type "KiCad") (uri "${KIPRJMOD}/design.kicad_sym") (options "") (descr ""))
)
'''
        with open(self.symbol_lib_table, 'w') as f:
            f.write(sym_lib_content)
        
        return str(self.schematic_file)


class KiCadPCB:
    """Handles KiCad PCB creation and manipulation."""
    
    def __init__(self, output_dir: str):
        """Initialize PCB handler."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pcb_file = self.output_dir / "design.kicad_pcb"
        
    def create_basic_pcb(self, components: List[Component], 
                        board_width: float = 100, board_height: float = 80) -> str:
        """Create a basic KiCad PCB file."""
        
        # KiCad 7+ PCB format (simplified)
        pcb_content = f'''(kicad_pcb
  (version 20230121)
  (generator "Othertales Q PCB Agent")
  (general
    (thickness 1.6)
    (legacy_teardrops no)
  )
  
  (paper "A4")
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
  )
  
  (setup
    (pad_to_mask_clearance 0)
    (allow_soldermask_bridges_in_footprints no)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros no)
      (usegerberextensions no)
      (usegerberattributes yes)
      (usegerberadvancedattributes yes)
      (creategerberjobfile yes)
      (dashed_line_dash_ratio 12.000000)
      (dashed_line_gap_ratio 3.000000)
      (svgprecision 4)
      (plotframeref no)
      (viasonmask no)
      (mode 1)
      (useauxorigin no)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15.000000)
      (pdf_front_fp_property_popups yes)
      (pdf_back_fp_property_popups yes)
      (dxfpolygonmode yes)
      (dxfimperialunits yes)
      (dxfusepcbnewfont yes)
      (psnegative no)
      (psa4output no)
      (plotreference yes)
      (plotvalue yes)
      (plotinvisibletext no)
      (sketchpadsonfab no)
      (subtractmaskfromsilk no)
      (outputformat 1)
      (mirror no)
      (drillshape 1)
      (scaleselection 1)
      (outputdirectory "")
    )
  )
  
  (net 0 "")
  (net 1 "GND")
  (net 2 "VCC")
  
'''
        
        # Add board outline
        pcb_content += f'''  (gr_rect
    (start 0 0)
    (end {board_width} {board_height})
    (stroke (width 0.1) (type solid))
    (layer "Edge.Cuts")
    (tstamp "outline-12345678-1234-1234-1234-123456789abc")
  )
  
'''
        
        # Add component footprints
        x_pos = 10
        y_pos = 10
        component_id = 1
        
        for component in components:
            ref_prefix = component.category[0] if component.category else "U"
            footprint = component.footprint or "Package_DIP:DIP-8_W7.62mm"
            
            pcb_content += f'''  (footprint "{footprint}"
    (layer "F.Cu")
    (tstamp "fp-{component_id:08d}-1234-1234-1234-123456789abc")
    (at {x_pos} {y_pos})
    (property "Reference" "{ref_prefix}{component_id}"
      (at 0 -3.5 0)
      (layer "F.SilkS")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (property "Value" "{component.name[:20]}"
      (at 0 3.5 0)
      (layer "F.Fab")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (property "Footprint" "{footprint}"
      (at 0 0 0)
      (layer "F.Fab")
      (hide yes)
      (effects (font (size 1.27 1.27) (thickness 0.15)))
    )
    (property "Datasheet" "{component.datasheet_url or ''}"
      (at 0 0 0)
      (layer "F.Fab")
      (hide yes)
      (effects (font (size 1.27 1.27) (thickness 0.15)))
    )
    (path "/component-{component_id:08d}-1234-1234-1234-123456789abc")
    (sheetname "Root")
    (sheetfile "design.kicad_sch")
    (attr through_hole)
    (fp_rect
      (start -2.5 -1.5)
      (end 2.5 1.5)
      (stroke (width 0.12) (type solid))
      (layer "F.SilkS")
    )
    (pad "1" thru_hole circle
      (at -1.27 0)
      (size 1.6 1.6)
      (drill 0.8)
      (layers "*.Cu" "*.Mask")
      (net 1 "GND")
    )
    (pad "2" thru_hole circle
      (at 1.27 0)
      (size 1.6 1.6)
      (drill 0.8)
      (layers "*.Cu" "*.Mask")
      (net 2 "VCC")
    )
  )
  
'''
            component_id += 1
            x_pos += 15
            if x_pos > board_width - 10:
                x_pos = 10
                y_pos += 15
        
        # Add basic traces
        pcb_content += '''  (segment
    (start 8.73 10)
    (end 23.73 10)
    (width 0.25)
    (layer "F.Cu")
    (net 1)
    (tstamp "trace-12345678-1234-1234-1234-123456789abc")
  )
  
'''
        
        # Close the PCB
        pcb_content += ")\n"
        
        # Write PCB file
        with open(self.pcb_file, 'w') as f:
            f.write(pcb_content)
        
        return str(self.pcb_file)


class KiCadProject:
    """Manages complete KiCad project creation."""
    
    def __init__(self, output_dir: str, project_name: str = "pcb_design"):
        """Initialize KiCad project manager."""
        self.output_dir = Path(output_dir)
        self.project_name = project_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.schematic = KiCadSchematic(output_dir)
        self.pcb = KiCadPCB(output_dir)
        
        # Create project file
        self.project_file = self.output_dir / f"{project_name}.kicad_pro"
        self._create_project_file()
    
    def _create_project_file(self):
        """Create KiCad project file."""
        project_content = {
            "board": {
                "3dviewports": [],
                "design_settings": {
                    "defaults": {
                        "board_outline_line_width": 0.1,
                        "copper_line_width": 0.2,
                        "copper_text_size_h": 1.5,
                        "copper_text_size_v": 1.5,
                        "copper_text_thickness": 0.3
                    },
                    "diff_pair_dimensions": [],
                    "drc_exclusions": [],
                    "rules": {
                        "min_copper_edge_clearance": 0.0,
                        "solder_mask_clearance": 0.0,
                        "solder_mask_min_width": 0.0
                    },
                    "track_widths": [0.25],
                    "via_dimensions": [{"diameter": 0.8, "drill": 0.4}]
                }
            },
            "libraries": {
                "pinned_footprint_libs": [],
                "pinned_symbol_libs": []
            },
            "meta": {
                "filename": f"{self.project_name}.kicad_pro",
                "version": 1
            },
            "net_settings": {
                "classes": [
                    {
                        "bus_width": 12.0,
                        "clearance": 0.2,
                        "diff_pair_gap": 0.25,
                        "diff_pair_via_gap": 0.25,
                        "diff_pair_width": 0.2,
                        "line_style": 0,
                        "microvia_diameter": 0.3,
                        "microvia_drill": 0.1,
                        "name": "Default",
                        "pcb_color": "rgba(0, 0, 0, 0.000)",
                        "schematic_color": "rgba(0, 0, 0, 0.000)",
                        "track_width": 0.25,
                        "via_diameter": 0.8,
                        "via_drill": 0.4,
                        "wire_width": 6.0
                    }
                ],
                "meta": {
                    "version": 3
                }
            },
            "pcbnew": {
                "last_paths": {
                    "gencad": "",
                    "idf": "",
                    "netlist": "",
                    "specctra_dsn": "",
                    "step": "",
                    "vrml": ""
                },
                "page_layout_descr_file": ""
            },
            "schematic": {
                "annotate_start_num": 0,
                "drawing": {
                    "dashed_lines_dash_length_ratio": 12.0,
                    "dashed_lines_gap_length_ratio": 3.0,
                    "default_line_thickness": 6.0,
                    "default_text_size": 50.0,
                    "field_names": [],
                    "intersheets_ref_own_page": False,
                    "intersheets_ref_prefix": "",
                    "intersheets_ref_short": False,
                    "intersheets_ref_show": False,
                    "intersheets_ref_suffix": "",
                    "junction_size_choice": 3,
                    "label_size_ratio": 0.375,
                    "pin_symbol_size": 25.0,
                    "text_offset_ratio": 0.15
                },
                "legacy_lib_dir": "",
                "legacy_lib_list": [],
                "meta": {
                    "version": 1
                },
                "net_format_name": "",
                "page_layout_descr_file": "",
                "plot_directory": "",
                "spice_current_sheet_as_root": False,
                "spice_external_command": "spice \"%I\"",
                "spice_model_current_sheet_as_root": True,
                "spice_save_all_currents": False,
                "spice_save_all_voltages": False,
                "subpart_first_id": 65,
                "subpart_id_separator": 0
            }
        }
        
        with open(self.project_file, 'w') as f:
            json.dump(project_content, f, indent=2)
    
    def create_complete_project(self, components: List[Component], 
                              board_width: float = 100, 
                              board_height: float = 80) -> Dict[str, str]:
        """Create complete KiCad project with schematic and PCB."""
        
        # Create schematic
        schematic_file = self.schematic.create_basic_schematic(components, self.project_name)
        
        # Create PCB
        pcb_file = self.pcb.create_basic_pcb(components, board_width, board_height)
        
        return {
            "project_file": str(self.project_file),
            "schematic_file": schematic_file,
            "pcb_file": pcb_file
        }


def generate_gerber_files(pcb_file: str, output_dir: str) -> List[str]:
    """Generate Gerber files for manufacturing from KiCad PCB."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create Gerber files (simulation - in real implementation would use KiCad Python API)
    gerber_files = [
        "design.gtl",   # Top copper
        "design.gbl",   # Bottom copper  
        "design.gto",   # Top silkscreen
        "design.gbo",   # Bottom silkscreen
        "design.gm1",   # Mechanical layer
        "design.drl",   # Drill file
        "design.csv"    # BOM
    ]
    
    manufacturing_files = []
    
    for gerber_file in gerber_files:
        file_path = output_path / gerber_file
        
        # Create placeholder Gerber content
        if gerber_file.endswith('.csv'):
            # BOM file
            content = """Reference,Quantity,Value,Footprint,Part Number
U1,1,STM32F405RGT6,LQFP-64,STM32F405RGT6
R1,1,1kΩ,0805,RC0805FR-071KL
C1,1,100nF,0805,GRM21BR71C104KA01L
"""
        elif gerber_file.endswith('.drl'):
            # Drill file
            content = """%
T1C0.8000
T2C1.0000
G90
G05
T1
X100Y100
X150Y100
T2
X200Y200
M30
%
"""
        else:
            # Gerber file
            content = f"""G04 Generated by Othertales Q PCB Agent*
G04 {gerber_file}*
%FSLAX24Y24*%
%MOMM*%
%TA.AperFunction,Conductor*%
%ADD10C,0.2500*%
G01*
X100000Y100000D02*
X150000Y100000D01*
M02*
"""
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        manufacturing_files.append(str(file_path))
    
    return manufacturing_files