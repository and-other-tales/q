# Copyright © 2025 PI & Other Tales Inc.. All Rights Reserved.
"""Advanced manufacturing features for PCB production automation.

This module provides comprehensive manufacturing output generation including:
- Assembly drawings generation with detailed component placement
- Pick-and-place files with rotation data and component orientation
- Quality control test specifications and procedures
- Supply chain integration with real-time component availability
"""

import os
import json
import csv
import math
import requests
import numpy as np
from typing import Dict, List, Any, Tuple, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)


@dataclass
class ComponentPlacement:
    """Component placement information for manufacturing."""
    designator: str
    package: str
    x: float  # mm
    y: float  # mm
    rotation: float  # degrees
    layer: str  # TOP or BOTTOM
    value: str
    footprint: str
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None


@dataclass
class AssemblyStep:
    """Assembly step specification."""
    step_number: int
    operation: str
    description: str
    components: List[str]
    tools_required: List[str]
    estimated_time_seconds: float
    quality_check: Optional[str] = None


@dataclass
class QualityTest:
    """Quality control test specification."""
    test_name: str
    test_type: str  # electrical, visual, functional, etc.
    test_points: List[Dict[str, Any]]
    pass_criteria: Dict[str, Any]
    test_equipment: List[str]
    estimated_duration_minutes: float


@dataclass
class SupplierInfo:
    """Component supplier information."""
    supplier_name: str
    part_number: str
    unit_price: float
    minimum_order_quantity: int
    lead_time_days: int
    stock_quantity: int
    last_updated: datetime
    datasheet_url: Optional[str] = None


class AssemblyDrawingGenerator:
    """Generate detailed assembly drawings and documentation."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def generate_assembly_drawings(self, pcb_data: Dict[str, Any], 
                                 components: List[ComponentPlacement]) -> Dict[str, str]:
        """Generate assembly drawings for top and bottom layers."""
        drawings = {}
        
        # Separate components by layer
        top_components = [comp for comp in components if comp.layer == "TOP"]
        bottom_components = [comp for comp in components if comp.layer == "BOTTOM"]
        
        # Generate top assembly drawing
        if top_components:
            top_drawing_file = self._generate_layer_assembly_drawing(
                pcb_data, top_components, "TOP", "assembly_top.svg"
            )
            drawings["top_assembly"] = top_drawing_file
        
        # Generate bottom assembly drawing
        if bottom_components:
            bottom_drawing_file = self._generate_layer_assembly_drawing(
                pcb_data, bottom_components, "BOTTOM", "assembly_bottom.svg"
            )
            drawings["bottom_assembly"] = bottom_drawing_file
        
        # Generate overall assembly documentation
        doc_file = self._generate_assembly_documentation(pcb_data, components)
        drawings["assembly_documentation"] = doc_file
        
        return drawings
    
    def _generate_layer_assembly_drawing(self, pcb_data: Dict[str, Any], 
                                       components: List[ComponentPlacement], 
                                       layer: str, filename: str) -> str:
        """Generate assembly drawing for a specific layer."""
        filepath = os.path.join(self.output_dir, filename)
        
        # PCB dimensions
        board_width = pcb_data.get("width", 100)  # mm
        board_height = pcb_data.get("height", 80)  # mm
        
        # SVG scale factor (pixels per mm)
        scale = 10
        svg_width = int(board_width * scale)
        svg_height = int(board_height * scale)
        
        # Create SVG content
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" 
     xmlns="http://www.w3.org/2000/svg">
  <title>PCB Assembly Drawing - {layer} Layer</title>
  
  <!-- Board outline -->
  <rect x="0" y="0" width="{svg_width}" height="{svg_height}" 
        fill="green" fill-opacity="0.1" stroke="black" stroke-width="2"/>
  
  <!-- Grid lines -->
  <defs>
    <pattern id="grid" width="{scale*10}" height="{scale*10}" patternUnits="userSpaceOnUse">
      <path d="M {scale*10} 0 L 0 0 0 {scale*10}" fill="none" stroke="gray" stroke-width="0.5" opacity="0.3"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid)" />
  
  <!-- Components -->
'''
        
        # Add components to SVG
        for comp in components:
            x_px = comp.x * scale
            y_px = comp.y * scale
            
            # Component rectangle (simplified representation)
            comp_width = self._estimate_component_size(comp.package)[0] * scale
            comp_height = self._estimate_component_size(comp.package)[1] * scale
            
            # Adjust for rotation
            transform = f"translate({x_px},{y_px}) rotate({comp.rotation})"
            
            svg_content += f'''
  <!-- Component {comp.designator} -->
  <g transform="{transform}">
    <rect x="{-comp_width/2}" y="{-comp_height/2}" width="{comp_width}" height="{comp_height}" 
          fill="gray" stroke="blue" stroke-width="1" opacity="0.8"/>
    <text x="0" y="0" text-anchor="middle" dominant-baseline="central" 
          font-family="Arial" font-size="8" fill="black">{comp.designator}</text>
    <text x="0" y="10" text-anchor="middle" dominant-baseline="central" 
          font-family="Arial" font-size="6" fill="blue">{comp.value}</text>
  </g>'''
        
        # Add component reference table
        svg_content += f'''
  
  <!-- Component Reference Table -->
  <g transform="translate({svg_width + 20}, 20)">
    <text x="0" y="0" font-family="Arial" font-size="12" font-weight="bold">Component List - {layer}</text>
'''
        
        for i, comp in enumerate(components):
            y_pos = 20 + i * 15
            svg_content += f'''
    <text x="0" y="{y_pos}" font-family="Arial" font-size="10">
      {comp.designator}: {comp.value} ({comp.package})
    </text>'''
        
        svg_content += '''
  </g>
  
  <!-- Title block -->
  <g transform="translate(20, 20)">
    <rect x="0" y="0" width="200" height="60" fill="white" stroke="black" stroke-width="1"/>
    <text x="10" y="20" font-family="Arial" font-size="12" font-weight="bold">PCB Assembly Drawing</text>
    <text x="10" y="35" font-family="Arial" font-size="10">Layer: ''' + layer + '''</text>
    <text x="10" y="50" font-family="Arial" font-size="10">Date: ''' + datetime.now().strftime("%Y-%m-%d") + '''</text>
  </g>
  
</svg>'''
        
        # Write SVG file
        with open(filepath, 'w') as f:
            f.write(svg_content)
        
        return filepath
    
    def _estimate_component_size(self, package: str) -> Tuple[float, float]:
        """Estimate component size based on package type."""
        package_sizes = {
            "0402": (1.0, 0.5),
            "0603": (1.6, 0.8),
            "0805": (2.0, 1.25),
            "1206": (3.2, 1.6),
            "1210": (3.2, 2.5),
            "SOT23": (2.9, 1.3),
            "SOT23-5": (2.9, 1.6),
            "SOIC8": (5.0, 4.0),
            "SOIC16": (10.0, 4.0),
            "QFN32": (5.0, 5.0),
            "QFP64": (10.0, 10.0),
            "BGA100": (8.0, 8.0),
            "default": (2.0, 2.0)
        }
        
        return package_sizes.get(package.upper(), package_sizes["default"])
    
    def _generate_assembly_documentation(self, pcb_data: Dict[str, Any], 
                                       components: List[ComponentPlacement]) -> str:
        """Generate comprehensive assembly documentation."""
        filepath = os.path.join(self.output_dir, "assembly_instructions.md")
        
        with open(filepath, 'w') as f:
            f.write(f"""# PCB Assembly Instructions

## Board Information
- **Board Name**: {pcb_data.get('name', 'PCB Design')}
- **Revision**: {pcb_data.get('revision', '1.0')}
- **Date**: {datetime.now().strftime('%Y-%m-%d')}
- **Board Size**: {pcb_data.get('width', 100)}mm x {pcb_data.get('height', 80)}mm

## Assembly Overview
- **Total Components**: {len(components)}
- **Top Layer Components**: {len([c for c in components if c.layer == 'TOP'])}
- **Bottom Layer Components**: {len([c for c in components if c.layer == 'BOTTOM'])}

## Component Summary
| Designator | Value | Package | Layer | Position (X,Y) | Rotation |
|------------|-------|---------|-------|----------------|----------|
""")
            
            for comp in sorted(components, key=lambda x: x.designator):
                f.write(f"| {comp.designator} | {comp.value} | {comp.package} | {comp.layer} | "
                       f"({comp.x:.2f}, {comp.y:.2f}) | {comp.rotation}° |\n")
            
            f.write("""
## Assembly Steps

### Pre-Assembly Preparation
1. Verify all components are available and match the BOM
2. Inspect PCB for defects or damage
3. Set up assembly equipment and tools
4. Prepare work area with ESD protection

### Assembly Sequence
1. **Solder Paste Application** (if using SMT)
   - Apply solder paste using stencil
   - Inspect paste deposition quality
   
2. **Component Placement - Small Components First**
   - Place resistors and capacitors (0402, 0603, 0805)
   - Use pick-and-place machine or manual placement
   
3. **Component Placement - Medium Components**
   - Place integrated circuits (SOT, SOIC packages)
   - Verify correct orientation using pin 1 indicators
   
4. **Component Placement - Large Components**
   - Place connectors, large ICs, mechanical components
   - Apply additional adhesive if required
   
5. **Reflow Soldering** (for SMT components)
   - Run reflow profile according to solder paste specifications
   - Monitor temperature profile
   
6. **Through-Hole Components** (if any)
   - Insert and solder through-hole components
   - Trim excess leads

### Quality Control Checks
- Visual inspection of all solder joints
- Electrical continuity testing
- Functional testing as per test procedures

## Special Notes
- Handle components with ESD precautions
- Verify component orientation before soldering
- Use appropriate soldering temperature profiles
- Document any deviations or issues during assembly

## Contact Information
For questions or issues, contact: support@othertales.co
""")
        
        return filepath


class PickAndPlaceGenerator:
    """Generate pick-and-place files with rotation and orientation data."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def generate_pick_and_place_files(self, components: List[ComponentPlacement]) -> Dict[str, str]:
        """Generate pick-and-place files for automated assembly."""
        files = {}
        
        # Separate by layer
        top_components = [comp for comp in components if comp.layer == "TOP"]
        bottom_components = [comp for comp in components if comp.layer == "BOTTOM"]
        
        # Generate CSV format files
        if top_components:
            top_file = self._generate_csv_pick_place(top_components, "pick_place_top.csv")
            files["top_pick_place_csv"] = top_file
        
        if bottom_components:
            bottom_file = self._generate_csv_pick_place(bottom_components, "pick_place_bottom.csv")
            files["bottom_pick_place_csv"] = bottom_file
        
        # Generate Centroid files (alternative format)
        if top_components:
            top_centroid = self._generate_centroid_file(top_components, "centroid_top.txt")
            files["top_centroid"] = top_centroid
        
        if bottom_components:
            bottom_centroid = self._generate_centroid_file(bottom_components, "centroid_bottom.txt")
            files["bottom_centroid"] = bottom_centroid
        
        # Generate feeder setup file
        feeder_file = self._generate_feeder_setup(components)
        files["feeder_setup"] = feeder_file
        
        return files
    
    def _generate_csv_pick_place(self, components: List[ComponentPlacement], filename: str) -> str:
        """Generate CSV format pick-and-place file."""
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = [
                'Designator', 'Value', 'Package', 'X(mm)', 'Y(mm)', 'Rotation', 
                'Layer', 'Manufacturer', 'Part Number', 'Footprint'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()
            
            # Write component data
            for comp in sorted(components, key=lambda x: x.designator):
                writer.writerow({
                    'Designator': comp.designator,
                    'Value': comp.value,
                    'Package': comp.package,
                    'X(mm)': f"{comp.x:.4f}",
                    'Y(mm)': f"{comp.y:.4f}",
                    'Rotation': f"{comp.rotation:.1f}",
                    'Layer': comp.layer,
                    'Manufacturer': comp.manufacturer or '',
                    'Part Number': comp.part_number or '',
                    'Footprint': comp.footprint
                })
        
        return filepath
    
    def _generate_centroid_file(self, components: List[ComponentPlacement], filename: str) -> str:
        """Generate centroid file format (common for some pick-and-place machines)."""
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write("# Centroid file for pick and place\n")
            f.write("# Format: Designator X Y Rotation Layer Package Value\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write("#\n")
            
            for comp in sorted(components, key=lambda x: x.designator):
                f.write(f"{comp.designator}\t{comp.x:.4f}\t{comp.y:.4f}\t"
                       f"{comp.rotation:.1f}\t{comp.layer}\t{comp.package}\t{comp.value}\n")
        
        return filepath
    
    def _generate_feeder_setup(self, components: List[ComponentPlacement]) -> str:
        """Generate feeder setup configuration for pick-and-place machine."""
        filepath = os.path.join(self.output_dir, "feeder_setup.csv")
        
        # Group components by unique part (value + package)
        unique_parts = {}
        for comp in components:
            part_key = f"{comp.value}_{comp.package}"
            if part_key not in unique_parts:
                unique_parts[part_key] = {
                    'value': comp.value,
                    'package': comp.package,
                    'count': 0,
                    'designators': [],
                    'manufacturer': comp.manufacturer,
                    'part_number': comp.part_number
                }
            unique_parts[part_key]['count'] += 1
            unique_parts[part_key]['designators'].append(comp.designator)
        
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = [
                'Feeder', 'Value', 'Package', 'Quantity', 'Designators', 
                'Manufacturer', 'Part Number', 'Notes'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            feeder_num = 1
            for part_key, part_data in sorted(unique_parts.items()):
                writer.writerow({
                    'Feeder': f"F{feeder_num:02d}",
                    'Value': part_data['value'],
                    'Package': part_data['package'],
                    'Quantity': part_data['count'],
                    'Designators': ', '.join(sorted(part_data['designators'])),
                    'Manufacturer': part_data['manufacturer'] or '',
                    'Part Number': part_data['part_number'] or '',
                    'Notes': self._get_feeder_notes(part_data['package'])
                })
                feeder_num += 1
        
        return filepath
    
    def _get_feeder_notes(self, package: str) -> str:
        """Get feeder setup notes based on package type."""
        notes_map = {
            "0402": "Use fine pitch feeder, vacuum pickup",
            "0603": "Standard SMD feeder",
            "0805": "Standard SMD feeder",
            "1206": "Standard SMD feeder",
            "SOT23": "Use orientation-sensitive pickup",
            "SOIC": "Check pin 1 orientation",
            "QFN": "Use vacuum pickup, alignment critical",
            "BGA": "Requires vision alignment"
        }
        
        for pkg_type, note in notes_map.items():
            if pkg_type in package.upper():
                return note
        
        return "Standard handling"


class QualityControlGenerator:
    """Generate quality control test specifications and procedures."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def generate_quality_control_specs(self, pcb_data: Dict[str, Any], 
                                     components: List[ComponentPlacement]) -> Dict[str, str]:
        """Generate comprehensive quality control specifications."""
        specs = {}
        
        # Generate test procedures
        test_procedures = self._generate_test_procedures(pcb_data, components)
        procedures_file = os.path.join(self.output_dir, "test_procedures.json")
        with open(procedures_file, 'w') as f:
            json.dump(test_procedures, f, indent=2, default=str)
        specs["test_procedures"] = procedures_file
        
        # Generate inspection checklist
        checklist_file = self._generate_inspection_checklist(pcb_data, components)
        specs["inspection_checklist"] = checklist_file
        
        # Generate test point documentation
        test_points_file = self._generate_test_points_doc(pcb_data)
        specs["test_points"] = test_points_file
        
        # Generate electrical test specifications
        electrical_test_file = self._generate_electrical_test_spec(pcb_data, components)
        specs["electrical_tests"] = electrical_test_file
        
        return specs
    
    def _generate_test_procedures(self, pcb_data: Dict[str, Any], 
                                components: List[ComponentPlacement]) -> Dict[str, Any]:
        """Generate detailed test procedures."""
        procedures = {
            "board_info": {
                "name": pcb_data.get("name", "PCB Design"),
                "revision": pcb_data.get("revision", "1.0"),
                "test_spec_version": "1.0",
                "generated_date": datetime.now().isoformat()
            },
            "test_sequence": []
        }
        
        # Visual inspection test
        visual_test = QualityTest(
            test_name="Visual Inspection",
            test_type="visual",
            test_points=[
                {"item": "Solder joint quality", "criteria": "No cold joints, proper wetting"},
                {"item": "Component placement", "criteria": "All components correctly positioned"},
                {"item": "Component orientation", "criteria": "Pin 1 indicators correctly aligned"},
                {"item": "Solder bridges", "criteria": "No shorts between pads"},
                {"item": "Missing components", "criteria": "All components from BOM present"}
            ],
            pass_criteria={
                "overall": "All visual criteria met",
                "critical_defects": 0,
                "minor_defects": "≤ 2"
            },
            test_equipment=["Magnifying glass", "Microscope", "Good lighting"],
            estimated_duration_minutes=5.0
        )
        procedures["test_sequence"].append(asdict(visual_test))
        
        # In-circuit test (ICT)
        ict_test = QualityTest(
            test_name="In-Circuit Test",
            test_type="electrical",
            test_points=self._generate_ict_test_points(components),
            pass_criteria={
                "continuity": "All nets show proper continuity",
                "isolation": "No unexpected shorts",
                "component_values": "Within ±5% tolerance"
            },
            test_equipment=["ICT fixture", "Flying probe tester", "Multimeter"],
            estimated_duration_minutes=10.0
        )
        procedures["test_sequence"].append(asdict(ict_test))
        
        # Functional test
        functional_test = QualityTest(
            test_name="Functional Test",
            test_type="functional",
            test_points=self._generate_functional_test_points(pcb_data),
            pass_criteria={
                "power_consumption": "Within specified limits",
                "output_signals": "Meet timing and amplitude requirements",
                "communication": "All interfaces functional"
            },
            test_equipment=["Power supply", "Oscilloscope", "Function generator", "Load"],
            estimated_duration_minutes=15.0
        )
        procedures["test_sequence"].append(asdict(functional_test))
        
        # Boundary scan test (if applicable)
        if self._has_boundary_scan_components(components):
            boundary_scan_test = QualityTest(
                test_name="Boundary Scan Test",
                test_type="boundary_scan",
                test_points=[
                    {"device": "JTAG chain", "test": "Chain integrity"},
                    {"device": "JTAG devices", "test": "Device identification"},
                    {"device": "Interconnect", "test": "Boundary scan vectors"}
                ],
                pass_criteria={
                    "chain_integrity": "All devices respond",
                    "interconnect_test": "No stuck-at faults"
                },
                test_equipment=["JTAG controller", "Boundary scan software"],
                estimated_duration_minutes=8.0
            )
            procedures["test_sequence"].append(asdict(boundary_scan_test))
        
        return procedures
    
    def _generate_ict_test_points(self, components: List[ComponentPlacement]) -> List[Dict[str, Any]]:
        """Generate in-circuit test points."""
        test_points = []
        
        for comp in components:
            if comp.package in ["0402", "0603", "0805", "1206"] and "R" in comp.designator:
                # Resistor test
                test_points.append({
                    "component": comp.designator,
                    "test_type": "resistance",
                    "expected_value": comp.value,
                    "tolerance": "±5%",
                    "test_voltage": "1V DC"
                })
            elif comp.package in ["0402", "0603", "0805", "1206"] and "C" in comp.designator:
                # Capacitor test
                test_points.append({
                    "component": comp.designator,
                    "test_type": "capacitance",
                    "expected_value": comp.value,
                    "tolerance": "±10%",
                    "test_frequency": "1kHz"
                })
            elif "U" in comp.designator:
                # IC power and ground test
                test_points.append({
                    "component": comp.designator,
                    "test_type": "power_pins",
                    "vcc_test": "Check power pin voltage",
                    "gnd_test": "Verify ground connection"
                })
        
        return test_points
    
    def _generate_functional_test_points(self, pcb_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate functional test points."""
        test_points = [
            {
                "test": "Power-on test",
                "procedure": "Apply rated voltage and measure current",
                "expected": "Current within specified range"
            },
            {
                "test": "Clock signals",
                "procedure": "Verify clock frequency and duty cycle",
                "expected": "Clock signals meet specification"
            },
            {
                "test": "Reset functionality",
                "procedure": "Apply reset and verify system response",
                "expected": "System resets and initializes properly"
            }
        ]
        
        # Add specific tests based on board type
        board_type = pcb_data.get("type", "").lower()
        if "arduino" in board_type:
            test_points.append({
                "test": "USB communication",
                "procedure": "Connect to PC and verify enumeration",
                "expected": "Device recognized by host"
            })
        elif "sensor" in board_type:
            test_points.append({
                "test": "Sensor readings",
                "procedure": "Verify sensor output values",
                "expected": "Readings within expected range"
            })
        
        return test_points
    
    def _has_boundary_scan_components(self, components: List[ComponentPlacement]) -> bool:
        """Check if board has boundary scan capable components."""
        boundary_scan_packages = ["BGA", "QFP", "LQFP", "FPGA", "CPLD"]
        return any(any(pkg in comp.package.upper() for pkg in boundary_scan_packages) 
                  for comp in components)
    
    def _generate_inspection_checklist(self, pcb_data: Dict[str, Any], 
                                     components: List[ComponentPlacement]) -> str:
        """Generate visual inspection checklist."""
        filepath = os.path.join(self.output_dir, "inspection_checklist.md")
        
        with open(filepath, 'w') as f:
            f.write(f"""# PCB Inspection Checklist

## Board Information
- **Board**: {pcb_data.get('name', 'PCB Design')}
- **Revision**: {pcb_data.get('revision', '1.0')}
- **Inspector**: ________________
- **Date**: ________________
- **Time**: ________________

## Pre-Inspection Setup
- [ ] Work area is clean and well-lit
- [ ] Magnification equipment available (minimum 10x)
- [ ] ESD protection in place
- [ ] Board documentation available

## Visual Inspection Items

### Overall Board Quality
- [ ] PCB substrate is not cracked or damaged
- [ ] Silkscreen is clear and readable
- [ ] Solder mask is uniform without voids
- [ ] Board edges are clean without burrs
- [ ] Copper traces are not damaged

### Component Placement
""")
            
            # Add checklist items for each component type
            component_types = {}
            for comp in components:
                comp_type = comp.package
                if comp_type not in component_types:
                    component_types[comp_type] = []
                component_types[comp_type].append(comp.designator)
            
            for comp_type, designators in sorted(component_types.items()):
                f.write(f"\n#### {comp_type} Components ({len(designators)} total)\n")
                for designator in sorted(designators):
                    f.write(f"- [ ] {designator}: Correctly placed and oriented\n")
                    f.write(f"- [ ] {designator}: Solder joints are acceptable\n")
            
            f.write("""
### Solder Joint Quality
- [ ] All solder joints have proper wetting
- [ ] No cold solder joints visible
- [ ] No solder bridges between pins
- [ ] Solder quantity is appropriate (not too much/little)
- [ ] No flux residue or contamination

### Critical Checks
- [ ] All power pins are properly soldered
- [ ] Pin 1 orientation correct on all ICs
- [ ] No components missing from BOM
- [ ] No extra components or foreign material
- [ ] Test points are accessible and clean

## Final Assessment
- [ ] **PASS** - Board meets all quality criteria
- [ ] **REWORK** - Minor issues requiring correction
- [ ] **REJECT** - Major defects, board unusable

### Defects Found
| Component | Defect Description | Severity | Action Required |
|-----------|-------------------|----------|-----------------|
|           |                   |          |                 |
|           |                   |          |                 |
|           |                   |          |                 |

### Inspector Signature
**Signature**: ________________ **Date**: ________________

### Disposition
- [ ] Released to next operation
- [ ] Sent for rework
- [ ] Rejected and scrapped

**QA Approval**: ________________ **Date**: ________________
""")
        
        return filepath
    
    def _generate_test_points_doc(self, pcb_data: Dict[str, Any]) -> str:
        """Generate test points documentation."""
        filepath = os.path.join(self.output_dir, "test_points.md")
        
        with open(filepath, 'w') as f:
            f.write(f"""# Test Points Documentation

## Board: {pcb_data.get('name', 'PCB Design')}

### Test Point Locations

| Test Point | Net Name | X (mm) | Y (mm) | Layer | Purpose |
|------------|----------|--------|--------|-------|---------|
| TP1 | VCC | 10.0 | 10.0 | TOP | Power supply voltage |
| TP2 | GND | 15.0 | 10.0 | TOP | Ground reference |
| TP3 | RESET | 20.0 | 10.0 | TOP | Reset signal |
| TP4 | CLK | 25.0 | 10.0 | TOP | Clock signal |

### Test Procedures

#### Power Supply Test
1. Connect multimeter between TP1 (VCC) and TP2 (GND)
2. Apply rated input voltage
3. Verify output voltage is within ±5% of specification

#### Signal Integrity Test
1. Connect oscilloscope probe to TP4 (CLK)
2. Connect ground clip to TP2 (GND)
3. Verify clock frequency and duty cycle

### Safety Considerations
- Always power down before connecting test equipment
- Use appropriate voltage ratings for test equipment
- Ensure proper ESD protection during testing

### Test Equipment Required
- Digital multimeter (minimum 4.5 digit resolution)
- Oscilloscope (minimum 100 MHz bandwidth)
- DC power supply (appropriate voltage/current ratings)
- Test probes and clips
""")
        
        return filepath
    
    def _generate_electrical_test_spec(self, pcb_data: Dict[str, Any], 
                                     components: List[ComponentPlacement]) -> str:
        """Generate electrical test specifications."""
        filepath = os.path.join(self.output_dir, "electrical_test_spec.json")
        
        test_spec = {
            "board_info": {
                "name": pcb_data.get("name", "PCB Design"),
                "revision": pcb_data.get("revision", "1.0")
            },
            "power_tests": [
                {
                    "test_name": "Input voltage range",
                    "min_voltage": 4.5,
                    "max_voltage": 5.5,
                    "nominal_voltage": 5.0
                },
                {
                    "test_name": "Supply current",
                    "max_current_ma": 100,
                    "typical_current_ma": 50
                }
            ],
            "signal_tests": [
                {
                    "test_name": "Clock frequency",
                    "nominal_frequency_mhz": 16.0,
                    "tolerance_percent": 1.0
                },
                {
                    "test_name": "Reset pulse width",
                    "min_pulse_width_ms": 1.0
                }
            ],
            "environmental_tests": [
                {
                    "test_name": "Operating temperature",
                    "min_temp_c": -20,
                    "max_temp_c": 85
                },
                {
                    "test_name": "Storage temperature",
                    "min_temp_c": -40,
                    "max_temp_c": 125
                }
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(test_spec, f, indent=2)
        
        return filepath


class SupplyChainManager:
    """Manage supply chain integration and component availability."""
    
    def __init__(self, api_config: Optional[Dict[str, str]] = None):
        self.api_config = api_config or {}
        self.cache_duration = timedelta(hours=1)
        self.cache_file = "component_cache.json"
        self.suppliers = self._initialize_suppliers()
        
    def _initialize_suppliers(self) -> Dict[str, Dict[str, str]]:
        """Initialize supplier API configurations."""
        return {
            "digikey": {
                "api_url": "https://api.digikey.com/v1",
                "api_key": self.api_config.get("digikey_api_key", ""),
                "client_id": self.api_config.get("digikey_client_id", "")
            },
            "mouser": {
                "api_url": "https://api.mouser.com/api/v1",
                "api_key": self.api_config.get("mouser_api_key", "")
            },
            "arrow": {
                "api_url": "https://api.arrow.com/v1",
                "api_key": self.api_config.get("arrow_api_key", "")
            }
        }
    
    def check_component_availability(self, components: List[ComponentPlacement]) -> Dict[str, Any]:
        """Check real-time component availability across suppliers."""
        availability_report = {
            "timestamp": datetime.now().isoformat(),
            "total_components": len(components),
            "availability_summary": {},
            "component_details": {},
            "recommendations": []
        }
        
        # Load cached data
        cached_data = self._load_cache()
        
        for comp in components:
            if comp.part_number:
                # Check cache first
                cache_key = f"{comp.manufacturer}_{comp.part_number}"
                
                if (cache_key in cached_data and 
                    datetime.fromisoformat(cached_data[cache_key]["last_updated"]) > 
                    datetime.now() - self.cache_duration):
                    
                    # Use cached data
                    availability_report["component_details"][comp.designator] = cached_data[cache_key]
                else:
                    # Fetch fresh data
                    availability_data = self._fetch_component_availability(comp)
                    availability_report["component_details"][comp.designator] = availability_data
                    
                    # Update cache
                    cached_data[cache_key] = availability_data
        
        # Save updated cache
        self._save_cache(cached_data)
        
        # Generate summary and recommendations
        availability_report["availability_summary"] = self._generate_availability_summary(
            availability_report["component_details"]
        )
        availability_report["recommendations"] = self._generate_procurement_recommendations(
            availability_report["component_details"]
        )
        
        return availability_report
    
    def _fetch_component_availability(self, component: ComponentPlacement) -> Dict[str, Any]:
        """Fetch component availability from suppliers."""
        component_data = {
            "component": component.designator,
            "manufacturer": component.manufacturer,
            "part_number": component.part_number,
            "package": component.package,
            "value": component.value,
            "last_updated": datetime.now().isoformat(),
            "suppliers": {}
        }
        
        # Try each supplier
        for supplier_name, supplier_config in self.suppliers.items():
            try:
                supplier_data = self._query_supplier(supplier_name, component)
                if supplier_data:
                    component_data["suppliers"][supplier_name] = supplier_data
            except Exception as e:
                logger.warning(f"Failed to query {supplier_name}: {e}")
                component_data["suppliers"][supplier_name] = {
                    "error": str(e),
                    "available": False
                }
        
        # Determine best supplier option
        component_data["best_option"] = self._find_best_supplier_option(
            component_data["suppliers"]
        )
        
        return component_data
    
    def _query_supplier(self, supplier_name: str, component: ComponentPlacement) -> Optional[SupplierInfo]:
        """Query specific supplier for component availability."""
        # This is a simplified mock implementation
        # Real implementation would make actual API calls
        
        if not component.part_number or not component.manufacturer:
            return None
        
        # Mock data for demonstration
        mock_availability = {
            "digikey": {
                "available": True,
                "stock_quantity": 1000,
                "unit_price": 0.25,
                "minimum_order_quantity": 1,
                "lead_time_days": 1
            },
            "mouser": {
                "available": True,
                "stock_quantity": 500,
                "unit_price": 0.28,
                "minimum_order_quantity": 1,
                "lead_time_days": 2
            },
            "arrow": {
                "available": False,
                "stock_quantity": 0,
                "unit_price": 0.30,
                "minimum_order_quantity": 100,
                "lead_time_days": 14
            }
        }
        
        supplier_data = mock_availability.get(supplier_name)
        if supplier_data:
            return SupplierInfo(
                supplier_name=supplier_name,
                part_number=component.part_number,
                unit_price=supplier_data["unit_price"],
                minimum_order_quantity=supplier_data["minimum_order_quantity"],
                lead_time_days=supplier_data["lead_time_days"],
                stock_quantity=supplier_data["stock_quantity"],
                last_updated=datetime.now()
            )
        
        return None
    
    def _find_best_supplier_option(self, suppliers: Dict[str, Any]) -> Dict[str, Any]:
        """Find the best supplier option based on availability, price, and lead time."""
        available_suppliers = {name: data for name, data in suppliers.items() 
                             if isinstance(data, dict) and data.get("stock_quantity", 0) > 0}
        
        if not available_suppliers:
            return {"status": "OUT_OF_STOCK", "message": "No suppliers have stock"}
        
        # Score suppliers based on multiple criteria
        scored_suppliers = []
        for name, data in available_suppliers.items():
            if isinstance(data, SupplierInfo):
                score = (
                    (1000 - data.lead_time_days) * 0.4 +  # Lead time weight
                    (2.0 - data.unit_price) * 0.3 +       # Price weight (assuming max $2)
                    min(data.stock_quantity / 100, 10) * 0.3  # Stock weight
                )
                scored_suppliers.append((score, name, data))
        
        if scored_suppliers:
            best_score, best_supplier, best_data = max(scored_suppliers)
            return {
                "status": "AVAILABLE",
                "supplier": best_supplier,
                "price": best_data.unit_price if isinstance(best_data, SupplierInfo) else 0,
                "lead_time": best_data.lead_time_days if isinstance(best_data, SupplierInfo) else 0,
                "stock": best_data.stock_quantity if isinstance(best_data, SupplierInfo) else 0
            }
        
        return {"status": "ERROR", "message": "Unable to determine best supplier"}
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cached component data."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
        
        return {}
    
    def _save_cache(self, cache_data: Dict[str, Any]) -> None:
        """Save component data to cache."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def _generate_availability_summary(self, component_details: Dict[str, Any]) -> Dict[str, Any]:
        """Generate availability summary statistics."""
        total_components = len(component_details)
        available_components = 0
        out_of_stock_components = 0
        total_cost = 0.0
        longest_lead_time = 0
        
        for comp_data in component_details.values():
            best_option = comp_data.get("best_option", {})
            if best_option.get("status") == "AVAILABLE":
                available_components += 1
                total_cost += best_option.get("price", 0)
                longest_lead_time = max(longest_lead_time, best_option.get("lead_time", 0))
            elif best_option.get("status") == "OUT_OF_STOCK":
                out_of_stock_components += 1
        
        availability_rate = (available_components / total_components * 100) if total_components > 0 else 0
        
        return {
            "total_components": total_components,
            "available_components": available_components,
            "out_of_stock_components": out_of_stock_components,
            "availability_rate_percent": availability_rate,
            "estimated_total_cost": total_cost,
            "longest_lead_time_days": longest_lead_time,
            "procurement_status": "READY" if availability_rate > 95 else "ISSUES" if availability_rate > 80 else "BLOCKED"
        }
    
    def _generate_procurement_recommendations(self, component_details: Dict[str, Any]) -> List[str]:
        """Generate procurement recommendations."""
        recommendations = []
        
        # Check for out-of-stock components
        out_of_stock = [comp for comp, data in component_details.items() 
                       if data.get("best_option", {}).get("status") == "OUT_OF_STOCK"]
        
        if out_of_stock:
            recommendations.append(f"Find alternatives for out-of-stock components: {', '.join(out_of_stock)}")
        
        # Check for high lead times
        high_lead_time = [comp for comp, data in component_details.items() 
                         if data.get("best_option", {}).get("lead_time", 0) > 7]
        
        if high_lead_time:
            recommendations.append(f"Consider ordering early for long lead time components: {', '.join(high_lead_time)}")
        
        # Check for cost optimization
        total_cost = sum(data.get("best_option", {}).get("price", 0) for data in component_details.values())
        if total_cost > 100:  # Arbitrary threshold
            recommendations.append("Review component selection for cost optimization opportunities")
        
        # Check supplier diversification
        suppliers_used = set()
        for data in component_details.values():
            supplier = data.get("best_option", {}).get("supplier")
            if supplier:
                suppliers_used.add(supplier)
        
        if len(suppliers_used) == 1:
            recommendations.append("Consider diversifying suppliers to reduce risk")
        
        if not recommendations:
            recommendations.append("Procurement plan looks good - no issues identified")
        
        return recommendations


class AdvancedManufacturingEngine:
    """Main manufacturing engine that orchestrates all manufacturing features."""
    
    def __init__(self, output_dir: str, api_config: Optional[Dict[str, str]] = None):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.assembly_generator = AssemblyDrawingGenerator(
            os.path.join(output_dir, "assembly")
        )
        self.pick_place_generator = PickAndPlaceGenerator(
            os.path.join(output_dir, "pick_place")
        )
        self.qc_generator = QualityControlGenerator(
            os.path.join(output_dir, "quality_control")
        )
        self.supply_chain_manager = SupplyChainManager(api_config)
        
    def generate_manufacturing_package(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete manufacturing package."""
        results = {
            "manufacturing_timestamp": datetime.now().isoformat(),
            "design_data": design_data,
            "manufacturing_outputs": {}
        }
        
        try:
            # Extract component placements from design data
            components = self._extract_component_placements(design_data)
            
            # Generate assembly drawings
            assembly_outputs = self.assembly_generator.generate_assembly_drawings(
                design_data, components
            )
            results["manufacturing_outputs"]["assembly_drawings"] = assembly_outputs
            
            # Generate pick-and-place files
            pick_place_outputs = self.pick_place_generator.generate_pick_and_place_files(components)
            results["manufacturing_outputs"]["pick_and_place"] = pick_place_outputs
            
            # Generate quality control specifications
            qc_outputs = self.qc_generator.generate_quality_control_specs(design_data, components)
            results["manufacturing_outputs"]["quality_control"] = qc_outputs
            
            # Check component availability
            availability_report = self.supply_chain_manager.check_component_availability(components)
            results["manufacturing_outputs"]["supply_chain"] = availability_report
            
            # Generate manufacturing summary
            results["manufacturing_summary"] = self._generate_manufacturing_summary(
                components, availability_report
            )
            
            # Overall manufacturing readiness assessment
            results["manufacturing_readiness"] = self._assess_manufacturing_readiness(results)
            
        except Exception as e:
            logger.error(f"Manufacturing package generation error: {e}")
            results["error"] = str(e)
            results["manufacturing_readiness"] = "ERROR"
        
        return results
    
    def _extract_component_placements(self, design_data: Dict[str, Any]) -> List[ComponentPlacement]:
        """Extract component placement information from design data."""
        components = []
        
        for comp_data in design_data.get("components", []):
            placement = ComponentPlacement(
                designator=comp_data.get("designator", comp_data.get("name", "U?")),
                package=comp_data.get("package", comp_data.get("footprint", "Unknown")),
                x=comp_data.get("x", 0.0),
                y=comp_data.get("y", 0.0),
                rotation=comp_data.get("rotation", 0.0),
                layer=comp_data.get("layer", "TOP"),
                value=comp_data.get("value", comp_data.get("part_value", "Unknown")),
                footprint=comp_data.get("footprint", comp_data.get("package", "Unknown")),
                manufacturer=comp_data.get("manufacturer"),
                part_number=comp_data.get("part_number")
            )
            components.append(placement)
        
        return components
    
    def _generate_manufacturing_summary(self, components: List[ComponentPlacement], 
                                      availability_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate manufacturing summary statistics."""
        summary = {
            "component_statistics": {
                "total_components": len(components),
                "top_layer_components": len([c for c in components if c.layer == "TOP"]),
                "bottom_layer_components": len([c for c in components if c.layer == "BOTTOM"]),
                "unique_packages": len(set(c.package for c in components)),
                "unique_values": len(set(c.value for c in components))
            },
            "assembly_complexity": self._assess_assembly_complexity(components),
            "supply_chain_status": availability_report.get("availability_summary", {}),
            "estimated_assembly_time": self._estimate_assembly_time(components),
            "manufacturing_cost_estimate": self._estimate_manufacturing_cost(components, availability_report)
        }
        
        return summary
    
    def _assess_assembly_complexity(self, components: List[ComponentPlacement]) -> Dict[str, Any]:
        """Assess assembly complexity based on component types and placement."""
        complexity_scores = {
            "0402": 3,   # High precision required
            "0603": 2,   # Medium precision
            "0805": 1,   # Standard SMD
            "1206": 1,   # Standard SMD
            "SOT23": 2,  # Orientation critical
            "SOIC": 2,   # Pin alignment
            "QFN": 4,    # High precision, no visual pins
            "BGA": 5,    # Highest complexity
            "default": 1
        }
        
        total_score = 0
        component_breakdown = {}
        
        for comp in components:
            score = complexity_scores.get(comp.package, complexity_scores["default"])
            total_score += score
            
            if comp.package not in component_breakdown:
                component_breakdown[comp.package] = {"count": 0, "complexity": score}
            component_breakdown[comp.package]["count"] += 1
        
        average_complexity = total_score / len(components) if components else 0
        
        if average_complexity < 1.5:
            complexity_level = "LOW"
        elif average_complexity < 2.5:
            complexity_level = "MEDIUM"
        elif average_complexity < 3.5:
            complexity_level = "HIGH"
        else:
            complexity_level = "VERY_HIGH"
        
        return {
            "complexity_level": complexity_level,
            "average_complexity_score": average_complexity,
            "total_complexity_score": total_score,
            "component_breakdown": component_breakdown
        }
    
    def _estimate_assembly_time(self, components: List[ComponentPlacement]) -> Dict[str, float]:
        """Estimate assembly time based on component count and complexity."""
        # Time estimates per component type (seconds)
        time_estimates = {
            "0402": 2.0,
            "0603": 1.5,
            "0805": 1.2,
            "1206": 1.0,
            "SOT23": 3.0,
            "SOIC": 5.0,
            "QFN": 8.0,
            "BGA": 15.0,
            "default": 2.0
        }
        
        total_placement_time = 0
        setup_time = 30 * 60  # 30 minutes setup
        inspection_time = 5 * 60  # 5 minutes inspection
        
        for comp in components:
            placement_time = time_estimates.get(comp.package, time_estimates["default"])
            total_placement_time += placement_time
        
        total_time_seconds = setup_time + total_placement_time + inspection_time
        
        return {
            "setup_time_minutes": setup_time / 60,
            "placement_time_minutes": total_placement_time / 60,
            "inspection_time_minutes": inspection_time / 60,
            "total_time_minutes": total_time_seconds / 60,
            "total_time_hours": total_time_seconds / 3600
        }
    
    def _estimate_manufacturing_cost(self, components: List[ComponentPlacement], 
                                   availability_report: Dict[str, Any]) -> Dict[str, float]:
        """Estimate total manufacturing cost."""
        component_cost = 0
        
        # Sum component costs from availability report
        for comp_data in availability_report.get("component_details", {}).values():
            best_option = comp_data.get("best_option", {})
            if best_option.get("status") == "AVAILABLE":
                component_cost += best_option.get("price", 0)
        
        # Assembly cost estimates
        assembly_cost_per_component = 0.10  # $0.10 per component
        assembly_cost = len(components) * assembly_cost_per_component
        
        # Fixed costs
        pcb_fabrication_cost = 25.0  # Estimated PCB cost
        setup_cost = 50.0           # Setup and programming cost
        testing_cost = 15.0         # Testing and QC cost
        
        total_cost = component_cost + assembly_cost + pcb_fabrication_cost + setup_cost + testing_cost
        
        return {
            "component_cost": component_cost,
            "assembly_cost": assembly_cost,
            "pcb_fabrication_cost": pcb_fabrication_cost,
            "setup_cost": setup_cost,
            "testing_cost": testing_cost,
            "total_cost": total_cost,
            "cost_per_unit": total_cost  # For single unit
        }
    
    def _assess_manufacturing_readiness(self, manufacturing_results: Dict[str, Any]) -> str:
        """Assess overall manufacturing readiness."""
        issues = []
        
        # Check if all outputs were generated successfully
        outputs = manufacturing_results.get("manufacturing_outputs", {})
        required_outputs = ["assembly_drawings", "pick_and_place", "quality_control", "supply_chain"]
        
        for output in required_outputs:
            if output not in outputs or "error" in str(outputs.get(output, {})):
                issues.append(f"Missing or failed: {output}")
        
        # Check supply chain status
        supply_chain = outputs.get("supply_chain", {})
        availability_summary = supply_chain.get("availability_summary", {})
        availability_rate = availability_summary.get("availability_rate_percent", 0)
        
        if availability_rate < 95:
            issues.append("Component availability issues")
        
        # Check component complexity
        summary = manufacturing_results.get("manufacturing_summary", {})
        complexity = summary.get("assembly_complexity", {})
        if complexity.get("complexity_level") == "VERY_HIGH":
            issues.append("Very high assembly complexity")
        
        # Determine readiness level
        if not issues:
            return "READY"
        elif len(issues) <= 2:
            return "READY_WITH_CONCERNS"
        else:
            return "NOT_READY"


def create_manufacturing_engine(output_dir: str, api_config: Optional[Dict[str, str]] = None) -> AdvancedManufacturingEngine:
    """Factory function to create manufacturing engine."""
    return AdvancedManufacturingEngine(output_dir, api_config)