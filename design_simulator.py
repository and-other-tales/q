#!/usr/bin/env python3
"""
Design simulator for PCB design validation.
Handles electrical rule checking, signal integrity analysis, and thermal simulations.
"""

import os
import sys
import math
import numpy as np
import tempfile
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

# Import our PCB layout engine
from pcb_layout_engine import PCBLayoutEngine, TraceSegment, ComponentPlacement

# Try to import KiCad modules
try:
    import pcbnew
    KICAD_AVAILABLE = True
except ImportError:
    KICAD_AVAILABLE = False
    print("Warning: KiCad Python API not available. Simulation will be approximate.")

class SimulationType(Enum):
    """Types of PCB design simulations."""
    ELECTRICAL_RULE_CHECK = 1
    SIGNAL_INTEGRITY = 2 
    POWER_INTEGRITY = 3
    THERMAL = 4
    EMI = 5

@dataclass
class ElectricalRuleViolation:
    """Represents an electrical rule violation in the design."""
    rule_name: str
    severity: str  # "error", "warning", "info"
    description: str
    location: Optional[Tuple[float, float]] = None  # x, y in mm
    component: Optional[str] = None  # Reference designator
    net: Optional[str] = None  # Net name

@dataclass
class SignalIntegrityResult:
    """Represents signal integrity analysis results."""
    net_name: str
    impedance: float  # ohms
    delay: float  # nanoseconds
    ringing: float  # percentage
    crosstalk: Dict[str, float] = field(default_factory=dict)  # neighboring net -> crosstalk in mV
    eye_height: Optional[float] = None  # mV
    eye_width: Optional[float] = None  # ps
    pass_fail: bool = True

@dataclass
class PowerIntegrityResult:
    """Represents power integrity analysis results."""
    net_name: str
    voltage_min: float  # V
    voltage_max: float  # V
    voltage_ripple: float  # mV
    current_max: float  # A
    ir_drop: float  # mV
    pass_fail: bool = True

@dataclass
class ThermalResult:
    """Represents thermal analysis results."""
    temperature_max: float  # °C
    temperature_min: float  # °C
    hotspot_locations: List[Tuple[float, float, float]] = field(default_factory=list)  # List of (x, y, temp) in mm and °C
    component_temperatures: Dict[str, float] = field(default_factory=dict)  # Reference designator -> temperature in °C
    pass_fail: bool = True

@dataclass
class EMIResult:
    """Represents electromagnetic interference analysis results."""
    emission_hotspots: List[Tuple[float, float, float, float]] = field(default_factory=list)  # x, y, frequency (MHz), amplitude (dBµV/m)
    frequencies: List[Tuple[float, float]] = field(default_factory=list)  # frequency (MHz), amplitude (dBµV/m)
    pass_fail: bool = True

@dataclass
class SimulationResults:
    """Container for all simulation results."""
    electrical_rule_violations: List[ElectricalRuleViolation] = field(default_factory=list)
    signal_integrity: Dict[str, SignalIntegrityResult] = field(default_factory=dict)
    power_integrity: Dict[str, PowerIntegrityResult] = field(default_factory=dict)
    thermal: Optional[ThermalResult] = None
    emi: Optional[EMIResult] = None
    
    def has_violations(self, include_warnings: bool = True) -> bool:
        """Check if there are any violations."""
        if include_warnings:
            return len(self.electrical_rule_violations) > 0
        return any(v.severity == "error" for v in self.electrical_rule_violations)
    
    def get_worst_violation(self) -> Optional[ElectricalRuleViolation]:
        """Get the most severe violation."""
        errors = [v for v in self.electrical_rule_violations if v.severity == "error"]
        if errors:
            return errors[0]
        warnings = [v for v in self.electrical_rule_violations if v.severity == "warning"]
        if warnings:
            return warnings[0]
        if self.electrical_rule_violations:
            return self.electrical_rule_violations[0]
        return None
    
    def summary(self) -> str:
        """Get a summary of simulation results."""
        lines = []
        
        # Electrical rule violations
        error_count = len([v for v in self.electrical_rule_violations if v.severity == "error"])
        warning_count = len([v for v in self.electrical_rule_violations if v.severity == "warning"])
        info_count = len([v for v in self.electrical_rule_violations if v.severity == "info"])
        
        lines.append(f"Electrical Rule Check: {error_count} errors, {warning_count} warnings, {info_count} notices")
        
        # Signal integrity
        if self.signal_integrity:
            failing_nets = [net for net, result in self.signal_integrity.items() if not result.pass_fail]
            lines.append(f"Signal Integrity: {len(failing_nets)} failing nets out of {len(self.signal_integrity)}")
        
        # Power integrity
        if self.power_integrity:
            failing_nets = [net for net, result in self.power_integrity.items() if not result.pass_fail]
            lines.append(f"Power Integrity: {len(failing_nets)} failing nets out of {len(self.power_integrity)}")
        
        # Thermal
        if self.thermal:
            thermal_status = "PASS" if self.thermal.pass_fail else "FAIL"
            lines.append(f"Thermal Analysis: {thermal_status}, Max temperature: {self.thermal.temperature_max:.1f}°C")
        
        # EMI
        if self.emi:
            emi_status = "PASS" if self.emi.pass_fail else "FAIL"
            lines.append(f"EMI Analysis: {emi_status}")
        
        return "\n".join(lines)

class DesignSimulator:
    """Simulator for PCB design validation."""
    
    def __init__(self, layout_engine: Optional[PCBLayoutEngine] = None):
        """
        Initialize the design simulator.
        
        Args:
            layout_engine: Optional PCB layout engine
        """
        self.layout_engine = layout_engine
        self.board = None
        self.results = SimulationResults()
        
        # Design rules
        self.min_trace_width = 0.2  # mm
        self.min_clearance = 0.2  # mm
        self.max_temperature = 85.0  # °C
        self.impedance_targets = {}  # net name -> target impedance in ohms
        
        # If layout engine has a board and KiCad is available, use it
        if layout_engine and layout_engine.board and KICAD_AVAILABLE:
            self.board = layout_engine.board
    
    def load_board(self, board_file: str) -> bool:
        """
        Load a KiCad PCB file for simulation.
        
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
    
    def run_simulation(self, sim_type: SimulationType) -> bool:
        """
        Run a specific type of simulation.
        
        Args:
            sim_type: Type of simulation to run
        
        Returns:
            True if successful, False otherwise
        """
        if sim_type == SimulationType.ELECTRICAL_RULE_CHECK:
            return self.run_electrical_rule_check()
        elif sim_type == SimulationType.SIGNAL_INTEGRITY:
            return self.run_signal_integrity_analysis()
        elif sim_type == SimulationType.POWER_INTEGRITY:
            return self.run_power_integrity_analysis()
        elif sim_type == SimulationType.THERMAL:
            return self.run_thermal_analysis()
        elif sim_type == SimulationType.EMI:
            return self.run_emi_analysis()
        else:
            print(f"Unknown simulation type: {sim_type}")
            return False
    
    def run_all_simulations(self) -> SimulationResults:
        """
        Run all available simulations.
        
        Returns:
            Simulation results
        """
        # Reset results
        self.results = SimulationResults()
        
        # Run all simulations
        self.run_electrical_rule_check()
        self.run_signal_integrity_analysis()
        self.run_power_integrity_analysis()
        self.run_thermal_analysis()
        self.run_emi_analysis()
        
        return self.results
    
    def run_electrical_rule_check(self) -> bool:
        """
        Run electrical rule check (DRC).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear previous results
            self.results.electrical_rule_violations = []
            
            # If we have a KiCad board, use its DRC
            if KICAD_AVAILABLE and self.board:
                # Run KiCad DRC
                drc = pcbnew.DRC(self.board)
                drc.SetViolationHandler(pcbnew.DRC_VIOLATION_HANDLER())
                drc.RunTests()
                
                # Get violations
                for item in drc.GetViolations():
                    # Create violation object
                    violation = ElectricalRuleViolation(
                        rule_name=str(item.GetViolationCode()),
                        severity="error",
                        description=item.GetMainText(),
                        location=(
                            pcbnew.ToMM(item.GetViolatingItem().GetPosition().x),
                            pcbnew.ToMM(item.GetViolatingItem().GetPosition().y)
                        )
                    )
                    self.results.electrical_rule_violations.append(violation)
                
                return True
            
            # Otherwise, use our own checks based on the layout engine
            elif self.layout_engine:
                # Check trace widths
                for trace in self.layout_engine.traces:
                    if trace.width < self.min_trace_width:
                        violation = ElectricalRuleViolation(
                            rule_name="MinTraceWidth",
                            severity="error",
                            description=f"Trace width {trace.width:.2f} mm is less than minimum {self.min_trace_width:.2f} mm",
                            location=trace.start_point,
                            net=trace.net_name
                        )
                        self.results.electrical_rule_violations.append(violation)
                
                # Check for unrouted nets
                routed_nets = set(trace.net_name for trace in self.layout_engine.traces)
                all_nets = set(net.net_name for net in self.layout_engine.nets)
                
                for net_name in all_nets - routed_nets:
                    violation = ElectricalRuleViolation(
                        rule_name="UnroutedNet",
                        severity="error",
                        description=f"Net {net_name} is not routed",
                        net=net_name
                    )
                    self.results.electrical_rule_violations.append(violation)
                
                # Add more checks here...
                
                return True
            
            else:
                print("No board or layout engine available for electrical rule check")
                return False
        
        except Exception as e:
            print(f"Error running electrical rule check: {e}")
            return False
    
    def run_signal_integrity_analysis(self) -> bool:
        """
        Run signal integrity analysis.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear previous results
            self.results.signal_integrity = {}
            
            # Without a real signal integrity simulator, we'll use approximations
            
            # If we have a layout engine, analyze its nets
            if self.layout_engine:
                # Get all signal nets (exclude power/ground)
                power_nets = ["GND", "VCC", "3V3", "5V", "VBUS"]
                signal_nets = set(net.net_name for net in self.layout_engine.nets 
                                 if net.net_name not in power_nets)
                
                # Analyze each signal net
                for net_name in signal_nets:
                    # Get all traces for this net
                    net_traces = [t for t in self.layout_engine.traces if t.net_name == net_name]
                    
                    if not net_traces:
                        continue
                    
                    # Calculate approximate trace length
                    total_length = 0.0
                    for trace in net_traces:
                        dx = trace.end_point[0] - trace.start_point[0]
                        dy = trace.end_point[1] - trace.start_point[1]
                        length = math.sqrt(dx*dx + dy*dy)
                        total_length += length
                    
                    # Count vias
                    via_count = sum(1 for t in net_traces if t.via_end)
                    
                    # Calculate approximate impedance (very simplified model)
                    # In reality, this would require sophisticated field solvers
                    width = net_traces[0].width  # Use first trace's width
                    impedance = 60.0 * math.log(4.0 * 1.6 / width)  # Simplified microstrip approximation
                    
                    # Calculate delay (assuming Er = 4.5)
                    delay_per_mm = 6.67  # ps/mm for Er=4.5
                    delay = (total_length * delay_per_mm) / 1000.0  # ns
                    
                    # Estimate ringing based on via count and length
                    ringing = 5.0 + (via_count * 2.0) + (total_length / 50.0)  # % (simplified approximation)
                    
                    # Check for adjacent traces (simplified crosstalk estimation)
                    crosstalk = {}
                    for other_net_name in signal_nets:
                        if other_net_name == net_name:
                            continue
                        
                        # In a real tool, this would be a complex analysis
                        # Here we're just making a very rough approximation
                        crosstalk[other_net_name] = 10.0  # mV
                    
                    # Determine pass/fail based on simplified rules
                    pass_fail = True
                    if ringing > 20.0:
                        pass_fail = False
                    
                    # Target impedance check if available
                    if net_name in self.impedance_targets:
                        target_impedance = self.impedance_targets[net_name]
                        if abs(impedance - target_impedance) > 10.0:  # Allow 10 ohm tolerance
                            pass_fail = False
                    
                    # Create result
                    result = SignalIntegrityResult(
                        net_name=net_name,
                        impedance=impedance,
                        delay=delay,
                        ringing=ringing,
                        crosstalk=crosstalk,
                        pass_fail=pass_fail
                    )
                    
                    self.results.signal_integrity[net_name] = result
                
                return True
            
            else:
                print("No layout engine available for signal integrity analysis")
                return False
        
        except Exception as e:
            print(f"Error running signal integrity analysis: {e}")
            return False
    
    def run_power_integrity_analysis(self) -> bool:
        """
        Run power integrity analysis.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear previous results
            self.results.power_integrity = {}
            
            # Without a real power integrity simulator, we'll use approximations
            
            # If we have a layout engine, analyze its power nets
            if self.layout_engine:
                # Get all power nets
                power_nets = ["VCC", "3V3", "5V", "VBUS"]
                
                # Analyze each power net
                for net_name in power_nets:
                    # Get all traces for this net
                    net_traces = [t for t in self.layout_engine.traces if t.net_name == net_name]
                    
                    if not net_traces:
                        continue
                    
                    # Get nominal voltage
                    nominal_voltage = 5.0  # Default to 5V
                    if net_name == "3V3":
                        nominal_voltage = 3.3
                    elif net_name == "1V8":
                        nominal_voltage = 1.8
                    
                    # Estimate current (in a real tool, this would come from the design)
                    current_max = 0.5  # A (placeholder)
                    
                    # Calculate approximate trace length
                    total_length = 0.0
                    for trace in net_traces:
                        dx = trace.end_point[0] - trace.start_point[0]
                        dy = trace.end_point[1] - trace.start_point[1]
                        length = math.sqrt(dx*dx + dy*dy)
                        total_length += length
                    
                    # Count vias
                    via_count = sum(1 for t in net_traces if t.via_end)
                    
                    # Calculate IR drop (very simplified model)
                    # In reality, this would require sophisticated power analysis
                    width = 0.0
                    if net_traces:
                        width = net_traces[0].width  # Use first trace's width
                    
                    # Simple resistance calculation
                    thickness = 0.035  # mm (1oz copper)
                    resistivity = 1.68e-8  # ohm.m (copper)
                    resistance = resistivity * total_length / (width * thickness) * 1000.0  # ohm
                    
                    # IR drop
                    ir_drop = resistance * current_max * 1000.0  # mV
                    
                    # Voltage min/max
                    voltage_min = nominal_voltage - (ir_drop / 1000.0)
                    voltage_max = nominal_voltage + 0.05  # Assume 5% tolerance
                    
                    # Ripple (simplified approximation based on length and via count)
                    voltage_ripple = 5.0 + (via_count * 1.0) + (total_length / 100.0)  # mV
                    
                    # Determine pass/fail based on simplified rules
                    pass_fail = True
                    
                    # 5% voltage drop is typically max allowable
                    max_drop_percent = (ir_drop / 1000.0) / nominal_voltage * 100.0
                    if max_drop_percent > 5.0:
                        pass_fail = False
                    
                    # 50mV ripple is typically max allowable
                    if voltage_ripple > 50.0:
                        pass_fail = False
                    
                    # Create result
                    result = PowerIntegrityResult(
                        net_name=net_name,
                        voltage_min=voltage_min,
                        voltage_max=voltage_max,
                        voltage_ripple=voltage_ripple,
                        current_max=current_max,
                        ir_drop=ir_drop,
                        pass_fail=pass_fail
                    )
                    
                    self.results.power_integrity[net_name] = result
                
                return True
            
            else:
                print("No layout engine available for power integrity analysis")
                return False
        
        except Exception as e:
            print(f"Error running power integrity analysis: {e}")
            return False
    
    def run_thermal_analysis(self) -> bool:
        """
        Run thermal analysis.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear previous results
            self.results.thermal = None
            
            # Without a real thermal simulator, we'll use approximations
            
            # If we have a layout engine, analyze its components
            if self.layout_engine:
                # Component temperatures dictionary
                component_temps = {}
                
                # Ambient temperature
                ambient_temp = 25.0  # °C
                
                # Analyze each component
                for component in self.layout_engine.components:
                    # Estimate power dissipation based on component type (very simplified)
                    power = 0.1  # W (default)
                    
                    if component.reference.startswith('U'):
                        power = 0.5  # Higher power for ICs
                    elif component.reference.startswith('Q'):
                        power = 0.3  # Transistors
                    elif component.reference.startswith('R'):
                        # For resistors, estimate based on value (simplified)
                        try:
                            # Extract value from reference
                            value_str = component.reference.split('_')[1] if '_' in component.reference else "10K"
                            
                            # Parse value
                            if 'K' in value_str:
                                resistance = float(value_str.replace('K', '')) * 1000.0
                            elif 'M' in value_str:
                                resistance = float(value_str.replace('M', '')) * 1000000.0
                            else:
                                resistance = float(value_str)
                            
                            # Assume 5V across resistor as default (very simplified)
                            voltage = 5.0
                            power = voltage * voltage / resistance
                        except:
                            power = 0.1  # Default if parsing fails
                    
                    # Thermal resistance (simplified)
                    thermal_resistance = 50.0  # °C/W
                    
                    # Temperature rise
                    temp_rise = power * thermal_resistance
                    
                    # Component temperature
                    temp = ambient_temp + temp_rise
                    
                    # Store temperature
                    component_temps[component.reference] = temp
                
                # Find min and max temperatures
                if component_temps:
                    temp_min = min(component_temps.values())
                    temp_max = max(component_temps.values())
                else:
                    temp_min = ambient_temp
                    temp_max = ambient_temp
                
                # Find hotspots
                hotspots = []
                for component, temp in component_temps.items():
                    if temp > temp_max - 5.0:  # Within 5°C of max
                        # Find component location
                        for c in self.layout_engine.components:
                            if c.reference == component:
                                hotspots.append((c.position[0], c.position[1], temp))
                                break
                
                # Determine pass/fail
                pass_fail = temp_max <= self.max_temperature
                
                # Create result
                self.results.thermal = ThermalResult(
                    temperature_min=temp_min,
                    temperature_max=temp_max,
                    hotspot_locations=hotspots,
                    component_temperatures=component_temps,
                    pass_fail=pass_fail
                )
                
                return True
            
            else:
                print("No layout engine available for thermal analysis")
                return False
        
        except Exception as e:
            print(f"Error running thermal analysis: {e}")
            return False
    
    def run_emi_analysis(self) -> bool:
        """
        Run electromagnetic interference analysis.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear previous results
            self.results.emi = None
            
            # Without a real EMI simulator, we'll use approximations
            
            # If we have a layout engine, analyze its layout
            if self.layout_engine:
                # Emission hotspots
                hotspots = []
                
                # Frequency spectrum
                frequencies = []
                
                # Analyze layout for potential EMI issues
                # This is a very simplified approximation
                
                # Look for long traces (potential antennas)
                long_traces = []
                for trace in self.layout_engine.traces:
                    dx = trace.end_point[0] - trace.start_point[0]
                    dy = trace.end_point[1] - trace.start_point[1]
                    length = math.sqrt(dx*dx + dy*dy)
                    
                    if length > 50.0:  # 50mm is considered long
                        long_traces.append((trace, length))
                
                # Sort by length
                long_traces.sort(key=lambda x: x[1], reverse=True)
                
                # Add hotspots for long traces
                for trace, length in long_traces[:5]:  # Top 5 longest traces
                    # Calculate resonant frequency (simplified)
                    # f = c / (4 * l * sqrt(Er)), assuming quarter-wave antenna
                    c = 3e11  # mm/s (speed of light)
                    Er = 4.5  # Dielectric constant
                    f = c / (4 * length * math.sqrt(Er)) / 1e6  # MHz
                    
                    # Estimate amplitude (simplified)
                    amplitude = 30.0 + length / 10.0  # dBµV/m
                    
                    # Add hotspot
                    midpoint_x = (trace.start_point[0] + trace.end_point[0]) / 2
                    midpoint_y = (trace.start_point[1] + trace.end_point[1]) / 2
                    hotspots.append((midpoint_x, midpoint_y, f, amplitude))
                    
                    # Add to frequency spectrum
                    frequencies.append((f, amplitude))
                
                # Look for loops
                
                # Determine pass/fail (simplified criteria)
                pass_fail = True
                for _, _, _, amplitude in hotspots:
                    if amplitude > 50.0:  # 50 dBµV/m is a common limit
                        pass_fail = False
                        break
                
                # Create result
                self.results.emi = EMIResult(
                    emission_hotspots=hotspots,
                    frequencies=frequencies,
                    pass_fail=pass_fail
                )
                
                return True
            
            else:
                print("No layout engine available for EMI analysis")
                return False
        
        except Exception as e:
            print(f"Error running EMI analysis: {e}")
            return False
    
    def export_report(self, output_file: str) -> bool:
        """
        Export simulation results to HTML report.
        
        Args:
            output_file: Output HTML file path
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_file, 'w') as f:
                # Write HTML header
                f.write("<!DOCTYPE html>\n")
                f.write("<html>\n")
                f.write("<head>\n")
                f.write("  <title>PCB Design Simulation Report</title>\n")
                f.write("  <style>\n")
                f.write("    body { font-family: Arial, sans-serif; margin: 20px; }\n")
                f.write("    h1 { color: #333; }\n")
                f.write("    h2 { color: #666; }\n")
                f.write("    table { border-collapse: collapse; width: 100%; }\n")
                f.write("    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n")
                f.write("    th { background-color: #f2f2f2; }\n")
                f.write("    tr:nth-child(even) { background-color: #f9f9f9; }\n")
                f.write("    .error { color: red; }\n")
                f.write("    .warning { color: orange; }\n")
                f.write("    .info { color: blue; }\n")
                f.write("    .pass { color: green; }\n")
                f.write("    .fail { color: red; }\n")
                f.write("  </style>\n")
                f.write("</head>\n")
                f.write("<body>\n")
                
                # Report header
                f.write("  <h1>PCB Design Simulation Report</h1>\n")
                f.write(f"  <p>Generated on {os.popen('date').read().strip()}</p>\n")
                
                # Summary section
                f.write("  <h2>Summary</h2>\n")
                f.write("  <p>")
                f.write(self.results.summary().replace("\n", "<br>"))
                f.write("  </p>\n")
                
                # Electrical rule violations
                f.write("  <h2>Electrical Rule Check</h2>\n")
                if self.results.electrical_rule_violations:
                    f.write("  <table>\n")
                    f.write("    <tr><th>Rule</th><th>Severity</th><th>Description</th><th>Location</th><th>Component</th><th>Net</th></tr>\n")
                    for violation in self.results.electrical_rule_violations:
                        severity_class = ""
                        if violation.severity == "error":
                            severity_class = "error"
                        elif violation.severity == "warning":
                            severity_class = "warning"
                        elif violation.severity == "info":
                            severity_class = "info"
                        
                        f.write(f"    <tr>\n")
                        f.write(f"      <td>{violation.rule_name}</td>\n")
                        f.write(f"      <td class=\"{severity_class}\">{violation.severity}</td>\n")
                        f.write(f"      <td>{violation.description}</td>\n")
                        f.write(f"      <td>{str(violation.location) if violation.location else ''}</td>\n")
                        f.write(f"      <td>{violation.component or ''}</td>\n")
                        f.write(f"      <td>{violation.net or ''}</td>\n")
                        f.write(f"    </tr>\n")
                    f.write("  </table>\n")
                else:
                    f.write("  <p class=\"pass\">No electrical rule violations found.</p>\n")
                
                # Signal integrity
                f.write("  <h2>Signal Integrity Analysis</h2>\n")
                if self.results.signal_integrity:
                    f.write("  <table>\n")
                    f.write("    <tr><th>Net</th><th>Impedance (Ω)</th><th>Delay (ns)</th><th>Ringing (%)</th><th>Eye Height (mV)</th><th>Eye Width (ps)</th><th>Status</th></tr>\n")
                    for net_name, result in self.results.signal_integrity.items():
                        status_class = "pass" if result.pass_fail else "fail"
                        status_text = "PASS" if result.pass_fail else "FAIL"
                        
                        f.write(f"    <tr>\n")
                        f.write(f"      <td>{net_name}</td>\n")
                        f.write(f"      <td>{result.impedance:.2f}</td>\n")
                        f.write(f"      <td>{result.delay:.2f}</td>\n")
                        f.write(f"      <td>{result.ringing:.2f}</td>\n")
                        f.write(f"      <td>{result.eye_height:.2f if result.eye_height else ''}</td>\n")
                        f.write(f"      <td>{result.eye_width:.2f if result.eye_width else ''}</td>\n")
                        f.write(f"      <td class=\"{status_class}\">{status_text}</td>\n")
                        f.write(f"    </tr>\n")
                    f.write("  </table>\n")
                else:
                    f.write("  <p>No signal integrity analysis performed.</p>\n")
                
                # Power integrity
                f.write("  <h2>Power Integrity Analysis</h2>\n")
                if self.results.power_integrity:
                    f.write("  <table>\n")
                    f.write("    <tr><th>Net</th><th>Voltage Min (V)</th><th>Voltage Max (V)</th><th>Ripple (mV)</th><th>Current (A)</th><th>IR Drop (mV)</th><th>Status</th></tr>\n")
                    for net_name, result in self.results.power_integrity.items():
                        status_class = "pass" if result.pass_fail else "fail"
                        status_text = "PASS" if result.pass_fail else "FAIL"
                        
                        f.write(f"    <tr>\n")
                        f.write(f"      <td>{net_name}</td>\n")
                        f.write(f"      <td>{result.voltage_min:.2f}</td>\n")
                        f.write(f"      <td>{result.voltage_max:.2f}</td>\n")
                        f.write(f"      <td>{result.voltage_ripple:.2f}</td>\n")
                        f.write(f"      <td>{result.current_max:.2f}</td>\n")
                        f.write(f"      <td>{result.ir_drop:.2f}</td>\n")
                        f.write(f"      <td class=\"{status_class}\">{status_text}</td>\n")
                        f.write(f"    </tr>\n")
                    f.write("  </table>\n")
                else:
                    f.write("  <p>No power integrity analysis performed.</p>\n")
                
                # Thermal analysis
                f.write("  <h2>Thermal Analysis</h2>\n")
                if self.results.thermal:
                    status_class = "pass" if self.results.thermal.pass_fail else "fail"
                    status_text = "PASS" if self.results.thermal.pass_fail else "FAIL"
                    
                    f.write(f"  <p>Temperature range: {self.results.thermal.temperature_min:.1f}°C to {self.results.thermal.temperature_max:.1f}°C</p>\n")
                    f.write(f"  <p>Status: <span class=\"{status_class}\">{status_text}</span></p>\n")
                    
                    # Hotspots
                    if self.results.thermal.hotspot_locations:
                        f.write("  <h3>Hotspots</h3>\n")
                        f.write("  <table>\n")
                        f.write("    <tr><th>X (mm)</th><th>Y (mm)</th><th>Temperature (°C)</th></tr>\n")
                        for x, y, temp in self.results.thermal.hotspot_locations:
                            f.write(f"    <tr>\n")
                            f.write(f"      <td>{x:.2f}</td>\n")
                            f.write(f"      <td>{y:.2f}</td>\n")
                            f.write(f"      <td>{temp:.1f}</td>\n")
                            f.write(f"    </tr>\n")
                        f.write("  </table>\n")
                    
                    # Component temperatures
                    if self.results.thermal.component_temperatures:
                        f.write("  <h3>Component Temperatures</h3>\n")
                        f.write("  <table>\n")
                        f.write("    <tr><th>Component</th><th>Temperature (°C)</th></tr>\n")
                        for component, temp in self.results.thermal.component_temperatures.items():
                            temp_class = ""
                            if temp > 80.0:
                                temp_class = "error"
                            elif temp > 70.0:
                                temp_class = "warning"
                            
                            f.write(f"    <tr>\n")
                            f.write(f"      <td>{component}</td>\n")
                            f.write(f"      <td class=\"{temp_class}\">{temp:.1f}</td>\n")
                            f.write(f"    </tr>\n")
                        f.write("  </table>\n")
                else:
                    f.write("  <p>No thermal analysis performed.</p>\n")
                
                # EMI analysis
                f.write("  <h2>EMI Analysis</h2>\n")
                if self.results.emi:
                    status_class = "pass" if self.results.emi.pass_fail else "fail"
                    status_text = "PASS" if self.results.emi.pass_fail else "FAIL"
                    
                    f.write(f"  <p>Status: <span class=\"{status_class}\">{status_text}</span></p>\n")
                    
                    # Emission hotspots
                    if self.results.emi.emission_hotspots:
                        f.write("  <h3>Emission Hotspots</h3>\n")
                        f.write("  <table>\n")
                        f.write("    <tr><th>X (mm)</th><th>Y (mm)</th><th>Frequency (MHz)</th><th>Amplitude (dBµV/m)</th></tr>\n")
                        for x, y, freq, amp in self.results.emi.emission_hotspots:
                            amp_class = ""
                            if amp > 50.0:
                                amp_class = "error"
                            elif amp > 40.0:
                                amp_class = "warning"
                            
                            f.write(f"    <tr>\n")
                            f.write(f"      <td>{x:.2f}</td>\n")
                            f.write(f"      <td>{y:.2f}</td>\n")
                            f.write(f"      <td>{freq:.2f}</td>\n")
                            f.write(f"      <td class=\"{amp_class}\">{amp:.2f}</td>\n")
                            f.write(f"    </tr>\n")
                        f.write("  </table>\n")
                    
                    # Frequency spectrum
                    if self.results.emi.frequencies:
                        f.write("  <h3>Frequency Spectrum</h3>\n")
                        f.write("  <table>\n")
                        f.write("    <tr><th>Frequency (MHz)</th><th>Amplitude (dBµV/m)</th></tr>\n")
                        for freq, amp in self.results.emi.frequencies:
                            amp_class = ""
                            if amp > 50.0:
                                amp_class = "error"
                            elif amp > 40.0:
                                amp_class = "warning"
                            
                            f.write(f"    <tr>\n")
                            f.write(f"      <td>{freq:.2f}</td>\n")
                            f.write(f"      <td class=\"{amp_class}\">{amp:.2f}</td>\n")
                            f.write(f"    </tr>\n")
                        f.write("  </table>\n")
                else:
                    f.write("  <p>No EMI analysis performed.</p>\n")
                
                # Close HTML
                f.write("</body>\n")
                f.write("</html>\n")
            
            print(f"Report generated: {output_file}")
            return True
        
        except Exception as e:
            print(f"Error exporting report: {e}")
            return False

# Main function for demonstration
def demo():
    """Run a demonstration of the design simulator."""
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
    
    # Create simulator
    simulator = DesignSimulator(engine)
    
    # Set some design rules
    simulator.min_trace_width = 0.2  # mm
    simulator.min_clearance = 0.2  # mm
    simulator.max_temperature = 85.0  # °C
    
    # Set impedance targets
    simulator.impedance_targets = {
        "RESET": 50.0  # 50 ohm target for RESET net
    }
    
    # Run all simulations
    print("Running simulations...")
    results = simulator.run_all_simulations()
    
    # Print summary
    print("\nSimulation Results Summary:")
    print(results.summary())
    
    # Export report
    print("\nExporting report...")
    simulator.export_report("simulation_report.html")
    
    print("\nDemo completed.")

if __name__ == "__main__":
    demo()