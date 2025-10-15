# Copyright © 2025 PI & Other Tales Inc.. All Rights Reserved.
"""Advanced simulation capabilities for PCB design validation.

This module provides comprehensive electrical, thermal, and signal integrity
analysis for PCB designs including:
- Signal integrity analysis with crosstalk and reflection analysis
- Power integrity verification with voltage drop analysis
- Thermal simulation with hotspot detection
- EMC pre-compliance testing
"""

import os
import json
import math
import math
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class SimulationPoint:
    """Represents a point in the PCB for simulation."""
    x: float
    y: float
    layer: int
    voltage: Optional[float] = None
    temperature: Optional[float] = None


@dataclass
class NetSegment:
    """Represents a trace segment in a net."""
    start: SimulationPoint
    end: SimulationPoint
    width: float
    impedance: float
    length: float
    layer: int


@dataclass
class Component:
    """Represents a component for simulation."""
    name: str
    x: float
    y: float
    power_dissipation: float
    thermal_resistance: float
    package_type: str
    pins: List[str]


@dataclass
class Via:
    """Represents a via for simulation."""
    x: float
    y: float
    start_layer: int
    end_layer: int
    diameter: float
    resistance: float


class SignalIntegrityAnalyzer:
    """Advanced signal integrity analysis engine."""
    
    def __init__(self, board_config: Dict[str, Any]):
        self.board_config = board_config
        self.dielectric_constant = board_config.get("dielectric_constant", 4.3)
        self.layer_thickness = board_config.get("layer_thickness", 0.1524)  # mm
        self.copper_thickness = board_config.get("copper_thickness", 0.035)  # mm
        
    def calculate_trace_impedance(self, width: float, thickness: float, 
                                height: float, dielectric_er: Optional[float] = None) -> float:
        """Calculate characteristic impedance of a microstrip trace."""
        if dielectric_er is None:
            dielectric_er = self.dielectric_constant
        
        # Fallback if still None
        if dielectric_er is None:
            dielectric_er = 4.3  # Default FR4 dielectric constant
            
        # Microstrip impedance calculation (Wheeler's approximation)
        if width / height >= 1:
            impedance = (87 / math.sqrt(dielectric_er + 1.41)) * math.log(5.98 * height / (0.8 * width + thickness))
        else:
            impedance = (60 / math.sqrt(dielectric_er)) * math.log(4 * height / width)
            
        return impedance
    
    def calculate_differential_impedance(self, width: float, spacing: float, 
                                       height: float, dielectric_er: Optional[float] = None) -> float:
        """Calculate differential impedance of a pair."""
        if dielectric_er is None:
            dielectric_er = self.dielectric_constant
        
        # Fallback if still None
        if dielectric_er is None:
            dielectric_er = 4.3  # Default FR4 dielectric constant
            
        # Differential pair impedance approximation
        single_ended = self.calculate_trace_impedance(width, self.copper_thickness, height, dielectric_er)
        coupling_factor = 1 - 0.48 * math.exp(-0.96 * spacing / height)
        differential_impedance = 2 * single_ended * coupling_factor
        
        return differential_impedance
    
    def analyze_crosstalk(self, aggressor_net: NetSegment, victim_net: NetSegment) -> Dict[str, float]:
        """Analyze crosstalk between two net segments."""
        # Calculate mutual inductance and capacitance
        distance = math.sqrt((aggressor_net.start.x - victim_net.start.x)**2 + 
                           (aggressor_net.start.y - victim_net.start.y)**2)
        
        if distance == 0:
            distance = 0.1  # Avoid division by zero
            
        # Simplified crosstalk calculation
        mutual_inductance = 0.2 * math.log(2 * distance / min(aggressor_net.width, victim_net.width))
        mutual_capacitance = 3.9 * 8.854e-12 * aggressor_net.length / distance
        
        # Crosstalk coefficients
        inductive_coupling = mutual_inductance / (mutual_inductance + 400e-9)  # Assume 400nH self-inductance
        capacitive_coupling = mutual_capacitance / (mutual_capacitance + 100e-12)  # Assume 100pF self-capacitance
        
        # Calculate crosstalk magnitudes
        near_end_crosstalk = abs(inductive_coupling - capacitive_coupling) / 2
        far_end_crosstalk = abs(inductive_coupling + capacitive_coupling) / 2
        
        return {
            "near_end_crosstalk_db": 20 * math.log10(max(near_end_crosstalk, 1e-6)),
            "far_end_crosstalk_db": 20 * math.log10(max(far_end_crosstalk, 1e-6)),
            "distance_mm": distance,
            "mutual_inductance_nH": mutual_inductance * 1e9,
            "mutual_capacitance_pF": mutual_capacitance * 1e12
        }
    
    def analyze_reflection(self, net_segments: List[NetSegment], source_impedance: float = 50.0, 
                         load_impedance: float = 1e6) -> Dict[str, Any]:
        """Analyze signal reflections in a net."""
        reflection_points = []
        
        for i, segment in enumerate(net_segments):
            # Calculate reflection coefficient at each impedance discontinuity
            if i == 0:
                # Source reflection
                reflection_coeff = (segment.impedance - source_impedance) / (segment.impedance + source_impedance)
            elif i == len(net_segments) - 1:
                # Load reflection
                reflection_coeff = (load_impedance - segment.impedance) / (load_impedance + segment.impedance)
            else:
                # Trace-to-trace reflection
                next_segment = net_segments[i + 1]
                reflection_coeff = (next_segment.impedance - segment.impedance) / (next_segment.impedance + segment.impedance)
            
            reflection_points.append({
                "segment_index": i,
                "reflection_coefficient": reflection_coeff,
                "reflection_db": 20 * math.log10(abs(reflection_coeff)) if reflection_coeff != 0 else -80,
                "location_mm": sum(seg.length for seg in net_segments[:i+1])
            })
        
        # Calculate total return loss
        total_reflection = sum(abs(point["reflection_coefficient"]) for point in reflection_points)
        return_loss_db = -20 * math.log10(max(total_reflection, 1e-6))
        
        return {
            "reflection_points": reflection_points,
            "total_return_loss_db": return_loss_db,
            "worst_reflection_db": min(point["reflection_db"] for point in reflection_points)
        }
    
    def analyze_timing(self, net_segments: List[NetSegment], rise_time_ps: float = 100.0) -> Dict[str, float]:
        """Analyze signal timing and propagation delay."""
        total_length = sum(segment.length for segment in net_segments)
        
        # Calculate propagation delay (approximate)
        velocity_factor = 1 / math.sqrt(self.dielectric_constant)
        propagation_delay_ps = (total_length / (3e8 * velocity_factor)) * 1e12
        
        # Calculate bandwidth based on rise time
        bandwidth_ghz = 0.35 / (rise_time_ps * 1e-12) / 1e9
        
        # Calculate skin effect losses at high frequency
        frequency_ghz = bandwidth_ghz / 2  # Use half bandwidth for analysis
        skin_depth_um = 66.1 / math.sqrt(frequency_ghz * 1000)  # Skin depth in micrometers
        resistance_per_mm = 17.2e-6 / (self.copper_thickness * 1000 * skin_depth_um * 1e-6)  # Ohms per mm
        
        total_resistance = resistance_per_mm * total_length
        insertion_loss_db = -20 * math.log10(math.exp(-total_resistance / 100))  # Approximate
        
        return {
            "total_length_mm": total_length,
            "propagation_delay_ps": propagation_delay_ps,
            "bandwidth_ghz": bandwidth_ghz,
            "insertion_loss_db": insertion_loss_db,
            "dc_resistance_ohms": total_resistance
        }


class PowerIntegrityAnalyzer:
    """Power integrity analysis for voltage drop and power distribution."""
    
    def __init__(self, board_config: Dict[str, Any]):
        self.board_config = board_config
        self.copper_resistivity = 1.72e-8  # Ohm*m
        
    def analyze_voltage_drop(self, power_nets: List[Dict[str, Any]], 
                           components: List[Component]) -> Dict[str, Any]:
        """Analyze voltage drop across power distribution network."""
        results = {}
        
        for power_net in power_nets:
            net_name = power_net["name"]
            target_voltage = power_net["voltage"]
            max_current = power_net["max_current"]
            
            # Calculate resistance of power plane
            plane_thickness = power_net.get("plane_thickness", 0.035)  # mm
            plane_area = power_net.get("area", 1000)  # mm²
            plane_resistance = (self.copper_resistivity * 0.001) / (plane_thickness * 1e-3 * plane_area * 1e-6)
            
            # Calculate voltage drop
            voltage_drop = max_current * plane_resistance
            voltage_drop_percent = (voltage_drop / target_voltage) * 100
            
            # Find worst-case component
            worst_component = None
            max_drop = 0
            
            for component in components:
                # Estimate resistance from power source to component
                distance_estimate = math.sqrt(component.x**2 + component.y**2) / 1000  # Convert to meters
                trace_resistance = (self.copper_resistivity * distance_estimate) / (0.1e-3 * 0.035e-3)  # 0.1mm width, 0.035mm thickness
                
                component_current = component.power_dissipation / target_voltage
                component_drop = component_current * (plane_resistance + trace_resistance)
                
                if component_drop > max_drop:
                    max_drop = component_drop
                    worst_component = component.name
            
            results[net_name] = {
                "target_voltage": target_voltage,
                "plane_resistance_mohms": plane_resistance * 1000,
                "max_voltage_drop": voltage_drop,
                "voltage_drop_percent": voltage_drop_percent,
                "worst_case_drop": max_drop,
                "worst_case_component": worst_component,
                "status": "PASS" if voltage_drop_percent < 5.0 else "FAIL"
            }
        
        return results
    
    def analyze_power_plane_resonance(self, plane_dimensions: Tuple[float, float], 
                                    dielectric_thickness: float) -> Dict[str, Any]:
        """Analyze power plane resonance frequencies."""
        width, height = plane_dimensions
        
        # Calculate resonant frequencies for rectangular cavity
        c = 3e8  # Speed of light
        er = self.board_config.get("dielectric_constant", 4.3)
        
        resonant_frequencies = []
        for m in range(1, 4):  # First few modes
            for n in range(1, 4):
                freq = (c / (2 * math.sqrt(er))) * math.sqrt((m/width)**2 + (n/height)**2)
                resonant_frequencies.append({
                    "mode": f"TM{m}{n}",
                    "frequency_ghz": freq / 1e9
                })
        
        # Sort by frequency
        resonant_frequencies.sort(key=lambda x: x["frequency_ghz"])
        
        return {
            "resonant_frequencies": resonant_frequencies[:10],  # Top 10 modes
            "fundamental_frequency_ghz": resonant_frequencies[0]["frequency_ghz"] if resonant_frequencies else 0,
            "plane_dimensions_mm": [width * 1000, height * 1000]
        }


class ThermalAnalyzer:
    """Thermal simulation and analysis."""
    
    def __init__(self, board_config: Dict[str, Any]):
        self.board_config = board_config
        self.ambient_temperature = board_config.get("ambient_temperature", 25.0)  # °C
        self.board_thermal_conductivity = board_config.get("thermal_conductivity", 0.3)  # W/m·K
        
    def analyze_component_temperatures(self, components: List[Component], 
                                     board_area: float = 1000.0) -> Dict[str, Any]:
        """Analyze component temperatures and thermal hotspots."""
        results = {}
        hotspots = []
        
        for component in components:
            # Calculate component temperature rise
            theta_ja = component.thermal_resistance  # °C/W (junction to ambient)
            temp_rise = component.power_dissipation * theta_ja
            junction_temp = self.ambient_temperature + temp_rise
            
            # Check for thermal hotspots
            if junction_temp > 85.0:  # Common thermal limit
                hotspots.append({
                    "component": component.name,
                    "temperature": junction_temp,
                    "power": component.power_dissipation,
                    "location": [component.x, component.y]
                })
            
            results[component.name] = {
                "junction_temperature": junction_temp,
                "temperature_rise": temp_rise,
                "power_dissipation": component.power_dissipation,
                "thermal_resistance": theta_ja,
                "status": "OK" if junction_temp < 85.0 else "HOT"
            }
        
        # Calculate board average temperature
        total_power = sum(comp.power_dissipation for comp in components)
        board_temp_rise = total_power * (1.0 / (board_area * 1e-6 * 20))  # Rough approximation
        average_board_temp = self.ambient_temperature + board_temp_rise
        
        return {
            "component_temperatures": results,
            "thermal_hotspots": hotspots,
            "total_power_dissipation": total_power,
            "average_board_temperature": average_board_temp,
            "max_temperature": max([comp["junction_temperature"] for comp in results.values()]) if results else self.ambient_temperature,
            "thermal_margin": 85.0 - max([comp["junction_temperature"] for comp in results.values()]) if results else 85.0
        }
    
    def calculate_thermal_vias(self, hotspot_locations: List[Tuple[float, float]], 
                             power_density: float) -> Dict[str, Any]:
        """Calculate thermal via requirements for hotspot cooling."""
        via_recommendations = []
        
        for x, y in hotspot_locations:
            # Calculate required thermal vias
            thermal_power = power_density * 25  # Assume 5x5mm hotspot area
            via_thermal_resistance = 50.0  # °C/W per via (typical)
            required_vias = max(1, int(thermal_power / (2.0 * via_thermal_resistance)))  # Target 2°C reduction per W
            
            # Calculate via pattern
            via_spacing = max(0.5, min(2.0, 10 / math.sqrt(required_vias)))  # mm
            pattern_size = via_spacing * math.ceil(math.sqrt(required_vias))
            
            via_recommendations.append({
                "location": [x, y],
                "recommended_vias": required_vias,
                "via_spacing_mm": via_spacing,
                "pattern_size_mm": pattern_size,
                "thermal_improvement": thermal_power * via_thermal_resistance / required_vias
            })
        
        return {
            "via_recommendations": via_recommendations,
            "total_vias_needed": sum(rec["recommended_vias"] for rec in via_recommendations)
        }


class EMCAnalyzer:
    """EMC pre-compliance analysis."""
    
    def __init__(self, board_config: Dict[str, Any]):
        self.board_config = board_config
        
    def analyze_emi_emissions(self, clock_frequencies: List[float], 
                            trace_lengths: Dict[str, float]) -> Dict[str, Any]:
        """Analyze potential EMI emissions."""
        emi_analysis = {}
        critical_frequencies = []
        
        for freq_mhz in clock_frequencies:
            # Calculate harmonics
            harmonics = []
            for harmonic in range(1, 11):  # First 10 harmonics
                harmonic_freq = freq_mhz * harmonic
                if harmonic_freq > 30:  # EMI concerns start at 30 MHz
                    harmonics.append(harmonic_freq)
            
            # Estimate radiation efficiency based on trace lengths
            max_trace_length = max(trace_lengths.values()) if trace_lengths else 10
            wavelength_mm = 300000 / freq_mhz  # mm
            radiation_efficiency = min(0.1, (max_trace_length / wavelength_mm) ** 2)
            
            critical_frequencies.extend([
                {
                    "frequency_mhz": h_freq,
                    "harmonic_order": harmonics.index(h_freq) + 1,
                    "fundamental_mhz": freq_mhz,
                    "radiation_efficiency": radiation_efficiency,
                    "concern_level": "HIGH" if h_freq > 1000 else "MEDIUM" if h_freq > 100 else "LOW"
                }
                for h_freq in harmonics[:5]  # Top 5 harmonics
            ])
        
        # Sort by frequency
        critical_frequencies.sort(key=lambda x: x["frequency_mhz"])
        
        return {
            "critical_frequencies": critical_frequencies,
            "max_frequency_mhz": max(cf["frequency_mhz"] for cf in critical_frequencies) if critical_frequencies else 0,
            "high_concern_count": len([cf for cf in critical_frequencies if cf["concern_level"] == "HIGH"]),
            "recommendations": self._generate_emi_recommendations(critical_frequencies)
        }
    
    def _generate_emi_recommendations(self, critical_frequencies: List[Dict]) -> List[str]:
        """Generate EMI mitigation recommendations."""
        recommendations = []
        
        high_freq_count = len([cf for cf in critical_frequencies if cf["frequency_mhz"] > 1000])
        if high_freq_count > 0:
            recommendations.append("Consider spread spectrum clocking for high-frequency signals")
            recommendations.append("Implement proper ground plane stitching")
            recommendations.append("Add ferrite beads on high-frequency lines")
        
        medium_freq_count = len([cf for cf in critical_frequencies if 100 < cf["frequency_mhz"] <= 1000])
        if medium_freq_count > 0:
            recommendations.append("Minimize loop areas in critical signal paths")
            recommendations.append("Use differential signaling where possible")
        
        if not recommendations:
            recommendations.append("EMI risk appears minimal for current design")
        
        return recommendations
    
    def analyze_esd_protection(self, io_pins: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze ESD protection requirements."""
        esd_analysis = {}
        protection_needed = []
        
        for pin in io_pins:
            pin_name = pin["name"]
            pin_type = pin.get("type", "digital")
            voltage_level = pin.get("voltage", 3.3)
            
            # Determine ESD risk level
            if pin_type in ["usb", "ethernet", "external_connector"]:
                risk_level = "HIGH"
                protection_needed.append({
                    "pin": pin_name,
                    "protection_type": "TVS_diode",
                    "voltage_rating": voltage_level * 1.2
                })
            elif pin_type in ["digital_io", "analog_input"]:
                risk_level = "MEDIUM"
                protection_needed.append({
                    "pin": pin_name,
                    "protection_type": "series_resistor",
                    "resistance": 100
                })
            else:
                risk_level = "LOW"
            
            esd_analysis[pin_name] = {
                "risk_level": risk_level,
                "voltage_level": voltage_level,
                "pin_type": pin_type
            }
        
        return {
            "pin_analysis": esd_analysis,
            "protection_components": protection_needed,
            "high_risk_pins": [pin for pin, data in esd_analysis.items() if data["risk_level"] == "HIGH"]
        }


class AdvancedSimulationEngine:
    """Main simulation engine that orchestrates all analysis types."""
    
    def __init__(self, board_config: Dict[str, Any]):
        self.board_config = board_config
        self.signal_analyzer = SignalIntegrityAnalyzer(board_config)
        self.power_analyzer = PowerIntegrityAnalyzer(board_config)
        self.thermal_analyzer = ThermalAnalyzer(board_config)
        self.emc_analyzer = EMCAnalyzer(board_config)
        
    def run_comprehensive_analysis(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive simulation analysis on PCB design."""
        results = {
            "simulation_timestamp": "2025-01-01T00:00:00Z",
            "design_data": design_data,
            "analysis_results": {}
        }
        
        try:
            # Extract design data
            components = [Component(**comp) for comp in design_data.get("components", [])]
            nets = design_data.get("nets", [])
            clock_frequencies = design_data.get("clock_frequencies", [100.0])  # MHz
            io_pins = design_data.get("io_pins", [])
            power_nets = design_data.get("power_nets", [])
            
            # Signal integrity analysis
            if nets:
                signal_results = {}
                for net in nets[:10]:  # Analyze first 10 nets for demo
                    net_name = net.get("name", f"NET_{nets.index(net)}")
                    
                    # Create simplified net segments for analysis
                    segments = [
                        NetSegment(
                            start=SimulationPoint(0, 0, 1),
                            end=SimulationPoint(net.get("length", 10), 0, 1),
                            width=net.get("width", 0.2),
                            impedance=net.get("impedance", 50),
                            length=net.get("length", 10),
                            layer=1
                        )
                    ]
                    
                    timing_analysis = self.signal_analyzer.analyze_timing(segments)
                    reflection_analysis = self.signal_analyzer.analyze_reflection(segments)
                    
                    signal_results[net_name] = {
                        "timing": timing_analysis,
                        "reflections": reflection_analysis,
                        "impedance": net.get("impedance", 50)
                    }
                
                results["analysis_results"]["signal_integrity"] = signal_results
            
            # Power integrity analysis
            if power_nets:
                power_results = self.power_analyzer.analyze_voltage_drop(power_nets, components)
                results["analysis_results"]["power_integrity"] = power_results
            
            # Thermal analysis
            if components:
                thermal_results = self.thermal_analyzer.analyze_component_temperatures(components)
                results["analysis_results"]["thermal"] = thermal_results
            
            # EMC analysis
            emc_results = self.emc_analyzer.analyze_emi_emissions(
                clock_frequencies, 
                {net.get("name", f"NET_{i}"): net.get("length", 10) for i, net in enumerate(nets)}
            )
            results["analysis_results"]["emc"] = emc_results
            
            # ESD analysis
            if io_pins:
                esd_results = self.emc_analyzer.analyze_esd_protection(io_pins)
                results["analysis_results"]["esd"] = esd_results
            
            # Overall assessment
            results["overall_status"] = self._assess_overall_status(results["analysis_results"])
            
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            results["error"] = str(e)
            results["overall_status"] = "ERROR"
        
        return results
    
    def _assess_overall_status(self, analysis_results: Dict[str, Any]) -> str:
        """Assess overall design status based on all analyses."""
        issues = []
        
        # Check signal integrity
        signal_results = analysis_results.get("signal_integrity", {})
        for net_name, net_data in signal_results.items():
            if net_data.get("reflections", {}).get("worst_reflection_db", 0) > -10:
                issues.append(f"Poor reflection performance on {net_name}")
        
        # Check power integrity
        power_results = analysis_results.get("power_integrity", {})
        for net_name, net_data in power_results.items():
            if net_data.get("status") == "FAIL":
                issues.append(f"Voltage drop issues on {net_name}")
        
        # Check thermal
        thermal_results = analysis_results.get("thermal", {})
        if thermal_results.get("thermal_hotspots"):
            issues.append("Thermal hotspots detected")
        
        # Check EMC
        emc_results = analysis_results.get("emc", {})
        if emc_results.get("high_concern_count", 0) > 0:
            issues.append("High EMI risk frequencies detected")
        
        if not issues:
            return "PASS"
        elif len(issues) <= 2:
            return "PASS_WITH_WARNINGS"
        else:
            return "FAIL"


def create_simulation_engine(board_config: Optional[Dict[str, Any]] = None) -> AdvancedSimulationEngine:
    """Factory function to create simulation engine with default config."""
    if board_config is None:
        board_config = {
            "dielectric_constant": 4.3,
            "layer_thickness": 0.1524,  # mm
            "copper_thickness": 0.035,  # mm
            "ambient_temperature": 25.0,  # °C
            "thermal_conductivity": 0.3  # W/m·K
        }
    
    return AdvancedSimulationEngine(board_config)