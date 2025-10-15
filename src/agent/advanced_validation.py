# Copyright © 2025 PI & Other Tales Inc.. All Rights Reserved.
"""Advanced design validation with SPICE simulation and S-parameter analysis.

This module provides comprehensive design validation including:
- SPICE simulation integration for circuit analysis
- S-parameter analysis for high-frequency circuits
- Crosstalk and reflection analysis
- Automated design optimization loops
"""

import os
import json
import math
import subprocess
import tempfile
import numpy as np
from typing import Dict, List, Any, Tuple, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class SpiceComponent:
    """SPICE component definition."""
    name: str
    component_type: str
    value: str
    nodes: List[str]
    model: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class SpiceNetlist:
    """Complete SPICE netlist."""
    title: str
    components: List[SpiceComponent]
    models: List[str]
    analysis: List[str]
    includes: List[str]


@dataclass
class SParameter:
    """S-parameter data point."""
    frequency: float
    s11: complex
    s12: complex
    s21: complex
    s22: complex


@dataclass
class FrequencyResponse:
    """Frequency response data."""
    frequencies: List[float]
    magnitude_db: List[float]
    phase_deg: List[float]
    group_delay_ns: List[float]


@dataclass 
class ValidationReport:
    """Validation report with summary and detailed results."""
    summary: Dict[str, Any]
    detailed_results: Dict[str, Any]
    recommendations: List[str]
    timestamp: str
    overall_grade: str


class SpiceSimulator:
    """SPICE simulation interface."""
    
    def __init__(self, spice_executable: str = "ngspice"):
        self.spice_executable = spice_executable
        self.temp_dir = tempfile.mkdtemp()
        
    def generate_netlist(self, circuit_data: Dict[str, Any]) -> SpiceNetlist:
        """Generate SPICE netlist from circuit data."""
        components = []
        models = []
        
        # Process components
        for comp_data in circuit_data.get("components", []):
            comp = self._convert_component_to_spice(comp_data)
            if comp:
                components.append(comp)
        
        # Process nets (convert to SPICE connectivity)
        net_components = self._generate_net_components(circuit_data.get("nets", []))
        components.extend(net_components)
        
        # Add standard models
        models.extend([
            ".model NMOS NMOS (VTO=1.0 KP=120u GAMMA=0.4 PHI=0.7)",
            ".model PMOS PMOS (VTO=-1.0 KP=40u GAMMA=0.4 PHI=0.7)",
            ".model NPN NPN (BF=100 BR=1 IS=1e-14 VAF=50)",
            ".model PNP PNP (BF=100 BR=1 IS=1e-14 VAF=50)"
        ])
        
        # Define analysis
        analysis = [
            ".op",  # Operating point
            ".dc VIN 0 5 0.1",  # DC sweep
            ".ac dec 100 1 1G",  # AC analysis
            ".tran 1n 1u"  # Transient analysis
        ]
        
        return SpiceNetlist(
            title=f"PCB Design Circuit - {circuit_data.get('name', 'Unnamed')}",
            components=components,
            models=models,
            analysis=analysis,
            includes=[]
        )
    
    def _convert_component_to_spice(self, comp_data: Dict[str, Any]) -> Optional[SpiceComponent]:
        """Convert component data to SPICE component."""
        comp_type = comp_data.get("type", "").lower()
        name = comp_data.get("name", "UNKNOWN")
        value = comp_data.get("value", "1")
        pins = comp_data.get("pins", [])
        
        if len(pins) < 2:
            return None
        
        # Map component types to SPICE
        if comp_type in ["resistor", "r"]:
            return SpiceComponent(
                name=f"R{name}",
                component_type="R",
                value=str(value),
                nodes=pins[:2]
            )
        elif comp_type in ["capacitor", "c"]:
            return SpiceComponent(
                name=f"C{name}",
                component_type="C",
                value=str(value),
                nodes=pins[:2]
            )
        elif comp_type in ["inductor", "l"]:
            return SpiceComponent(
                name=f"L{name}",
                component_type="L",
                value=str(value),
                nodes=pins[:2]
            )
        elif comp_type in ["voltage_source", "vsource"]:
            return SpiceComponent(
                name=f"V{name}",
                component_type="V",
                value=f"DC {value}",
                nodes=pins[:2]
            )
        elif comp_type in ["current_source", "isource"]:
            return SpiceComponent(
                name=f"I{name}",
                component_type="I",
                value=f"DC {value}",
                nodes=pins[:2]
            )
        elif comp_type in ["diode", "d"]:
            return SpiceComponent(
                name=f"D{name}",
                component_type="D",
                value="DMOD",
                nodes=pins[:2],
                model=".model DMOD D (IS=1e-14 N=1.5)"
            )
        elif comp_type in ["transistor", "nmos"]:
            if len(pins) >= 3:
                return SpiceComponent(
                    name=f"M{name}",
                    component_type="M",
                    value="NMOS",
                    nodes=pins[:4] if len(pins) >= 4 else pins[:3] + ["0"],  # Add bulk if missing
                    model="NMOS"
                )
        elif comp_type in ["pmos"]:
            if len(pins) >= 3:
                return SpiceComponent(
                    name=f"M{name}",
                    component_type="M",
                    value="PMOS",
                    nodes=pins[:4] if len(pins) >= 4 else pins[:3] + ["VDD"],
                    model="PMOS"
                )
        
        return None
    
    def _generate_net_components(self, nets: List[Dict[str, Any]]) -> List[SpiceComponent]:
        """Generate transmission line components for nets."""
        net_components = []
        
        for net in nets:
            net_name = net.get("name", "NET")
            length = net.get("length", 10)  # mm
            impedance = net.get("impedance", 50)  # ohms
            
            if length > 5:  # Only model transmission lines > 5mm
                # Create transmission line model
                tline = SpiceComponent(
                    name=f"T{net_name}",
                    component_type="T",
                    value=f"Z0={impedance} TD={length*3.3e-3}n",  # Approximate delay
                    nodes=[f"{net_name}_start", f"{net_name}_end", "0", "0"]
                )
                net_components.append(tline)
        
        return net_components
    
    def write_netlist_file(self, netlist: SpiceNetlist, filename: str) -> str:
        """Write SPICE netlist to file."""
        filepath = os.path.join(self.temp_dir, filename)
        
        with open(filepath, 'w') as f:
            # Title
            f.write(f"{netlist.title}\n\n")
            
            # Includes
            for include in netlist.includes:
                f.write(f"{include}\n")
            f.write("\n")
            
            # Components
            for comp in netlist.components:
                nodes_str = " ".join(comp.nodes)
                if comp.model:
                    f.write(f"{comp.name} {nodes_str} {comp.value}\n")
                else:
                    f.write(f"{comp.name} {nodes_str} {comp.value}\n")
            f.write("\n")
            
            # Models
            for model in netlist.models:
                f.write(f"{model}\n")
            f.write("\n")
            
            # Analysis
            for analysis in netlist.analysis:
                f.write(f"{analysis}\n")
            
            # End
            f.write("\n.end\n")
        
        return filepath
    
    def run_simulation(self, netlist_file: str) -> Dict[str, Any]:
        """Run SPICE simulation and return results."""
        try:
            # Create command file
            cmd_file = os.path.join(self.temp_dir, "spice_commands.txt")
            with open(cmd_file, 'w') as f:
                f.write(f"source {netlist_file}\n")
                f.write("run\n")
                f.write("print all\n")
                f.write("quit\n")
            
            # Run SPICE
            result = subprocess.run(
                [self.spice_executable, "-b", cmd_file],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"SPICE simulation failed: {result.stderr}")
                return {"error": result.stderr, "status": "FAILED"}
            
            # Parse results
            simulation_results = self._parse_spice_output(result.stdout)
            simulation_results["status"] = "SUCCESS"
            
            return simulation_results
            
        except subprocess.TimeoutExpired:
            logger.error("SPICE simulation timed out")
            return {"error": "Simulation timeout", "status": "TIMEOUT"}
        except Exception as e:
            logger.error(f"SPICE simulation error: {e}")
            return {"error": str(e), "status": "ERROR"}
    
    def _parse_spice_output(self, output: str) -> Dict[str, Any]:
        """Parse SPICE simulation output."""
        results = {
            "operating_point": {},
            "dc_analysis": {},
            "ac_analysis": {},
            "transient_analysis": {}
        }
        
        lines = output.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if "Operating Point" in line:
                current_section = "operating_point"
            elif "DC Analysis" in line:
                current_section = "dc_analysis"
            elif "AC Analysis" in line:
                current_section = "ac_analysis"
            elif "Transient Analysis" in line:
                current_section = "transient_analysis"
            elif current_section and "=" in line:
                # Parse variable assignments
                parts = line.split('=')
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    var_value = parts[1].strip()
                    try:
                        results[current_section][var_name] = float(var_value)
                    except ValueError:
                        results[current_section][var_name] = var_value
        
        return results


class SParameterAnalyzer:
    """S-parameter analysis for high-frequency circuits."""
    
    def __init__(self):
        self.frequency_points = []
        self.s_parameters = []
        
    def calculate_s_parameters(self, circuit_data: Dict[str, Any], 
                             frequency_range: Tuple[float, float], 
                             num_points: int = 1000) -> List[SParameter]:
        """Calculate S-parameters over frequency range."""
        freq_start, freq_end = frequency_range
        frequencies = np.logspace(np.log10(freq_start), np.log10(freq_end), num_points)
        
        s_parameters = []
        
        for freq in frequencies:
            # Simplified S-parameter calculation
            # In practice, this would use full EM simulation
            s_param = self._calculate_s_parameter_at_frequency(circuit_data, freq)
            s_parameters.append(s_param)
        
        return s_parameters
    
    def _calculate_s_parameter_at_frequency(self, circuit_data: Dict[str, Any], 
                                          frequency: float) -> SParameter:
        """Calculate S-parameters at specific frequency."""
        # Simplified calculation for demonstration
        # Real implementation would use Method of Moments or FDTD
        
        # Get transmission line parameters
        nets = circuit_data.get("nets", [])
        
        if not nets:
            # No transmission lines - ideal case
            return SParameter(frequency, 0+0j, 1+0j, 1+0j, 0+0j)
        
        # Use first net for calculation
        net = nets[0]
        length = net.get("length", 10) / 1000  # Convert mm to m
        impedance = net.get("impedance", 50)
        
        # Calculate electrical length
        wavelength = 3e8 / frequency
        electrical_length = 2 * np.pi * length / wavelength
        
        # Transmission line S-parameters
        gamma = 1j * electrical_length  # Lossless line
        
        # S-parameter matrix for transmission line
        s11 = 0 + 0j  # Perfect match
        s21 = np.exp(-gamma)  # Transmission with phase delay
        s12 = s21  # Reciprocal
        s22 = 0 + 0j  # Perfect match
        
        # Add losses if specified
        if "loss_db_per_mm" in net:
            loss_db = net["loss_db_per_mm"] * length * 1000
            loss_linear = 10 ** (-loss_db / 20)
            s21 *= loss_linear
            s12 *= loss_linear
        
        return SParameter(frequency, s11, s12, s21, s22)
    
    def analyze_insertion_loss(self, s_parameters: List[SParameter]) -> FrequencyResponse:
        """Analyze insertion loss (S21) vs frequency."""
        frequencies = [sp.frequency for sp in s_parameters]
        s21_magnitude = [abs(sp.s21) for sp in s_parameters]
        s21_phase = [np.angle(sp.s21, deg=True) for sp in s_parameters]
        
        # Convert to dB
        magnitude_db = [20 * np.log10(mag) if mag > 0 else -100 for mag in s21_magnitude]
        
        # Calculate group delay
        group_delay_ns = []
        for i in range(1, len(s21_phase)):
            freq_diff = frequencies[i] - frequencies[i-1]
            phase_diff = s21_phase[i] - s21_phase[i-1]
            
            # Handle phase wrapping
            while phase_diff > 180:
                phase_diff -= 360
            while phase_diff < -180:
                phase_diff += 360
            
            group_delay = -phase_diff / (360 * freq_diff) * 1e9  # Convert to ns
            group_delay_ns.append(group_delay)
        
        group_delay_ns.insert(0, group_delay_ns[0] if group_delay_ns else 0.0)
        
        # Ensure all lists contain floats
        magnitude_db = [float(x) for x in magnitude_db]
        s21_phase = [float(x) for x in s21_phase]
        group_delay_ns = [float(x) for x in group_delay_ns]
        
        return FrequencyResponse(frequencies, magnitude_db, s21_phase, group_delay_ns)
    
    def analyze_return_loss(self, s_parameters: List[SParameter]) -> FrequencyResponse:
        """Analyze return loss (S11) vs frequency."""
        frequencies = [sp.frequency for sp in s_parameters]
        s11_magnitude = [abs(sp.s11) for sp in s_parameters]
        s11_phase = [np.angle(sp.s11, deg=True) for sp in s_parameters]
        
        # Convert to dB (return loss is negative of reflection in dB)
        magnitude_db = [-20 * np.log10(mag) if mag > 0 else 100 for mag in s11_magnitude]
        
        # Ensure all lists contain floats
        magnitude_db = [float(x) for x in magnitude_db]
        s11_phase = [float(x) for x in s11_phase]
        zero_list = [0.0] * len(frequencies)
        
        return FrequencyResponse(frequencies, magnitude_db, s11_phase, zero_list)
    
    def calculate_vswr(self, s_parameters: List[SParameter]) -> List[float]:
        """Calculate VSWR from S11."""
        vswr_values = []
        
        for sp in s_parameters:
            reflection_coeff = abs(sp.s11)
            if reflection_coeff < 1.0:
                vswr = (1 + reflection_coeff) / (1 - reflection_coeff)
            else:
                vswr = float('inf')
            
            vswr_values.append(vswr)
        
        return vswr_values


class CrosstalkAnalyzer:
    """Crosstalk analysis between signal nets."""
    
    def __init__(self):
        pass
        
    def analyze_crosstalk_matrix(self, nets: List[Dict[str, Any]], 
                               board_stackup: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze crosstalk between all net pairs."""
        n_nets = len(nets)
        
        # Initialize crosstalk matrices
        near_end_crosstalk = np.zeros((n_nets, n_nets))
        far_end_crosstalk = np.zeros((n_nets, n_nets))
        
        for i in range(n_nets):
            for j in range(i + 1, n_nets):
                net1 = nets[i]
                net2 = nets[j]
                
                crosstalk = self._calculate_crosstalk_coupling(net1, net2, board_stackup)
                
                near_end_crosstalk[i][j] = crosstalk["near_end_db"]
                near_end_crosstalk[j][i] = crosstalk["near_end_db"]
                
                far_end_crosstalk[i][j] = crosstalk["far_end_db"]
                far_end_crosstalk[j][i] = crosstalk["far_end_db"]
        
        # Find critical crosstalk pairs
        critical_pairs = []
        threshold_db = -40  # dB
        
        for i in range(n_nets):
            for j in range(i + 1, n_nets):
                if (near_end_crosstalk[i][j] > threshold_db or 
                    far_end_crosstalk[i][j] > threshold_db):
                    critical_pairs.append({
                        "aggressor": nets[i]["name"],
                        "victim": nets[j]["name"],
                        "near_end_crosstalk_db": near_end_crosstalk[i][j],
                        "far_end_crosstalk_db": far_end_crosstalk[i][j],
                        "severity": "HIGH" if max(near_end_crosstalk[i][j], far_end_crosstalk[i][j]) > -20 else "MEDIUM"
                    })
        
        return {
            "near_end_matrix": near_end_crosstalk.tolist(),
            "far_end_matrix": far_end_crosstalk.tolist(),
            "critical_pairs": critical_pairs,
            "max_near_end_crosstalk": np.max(near_end_crosstalk),
            "max_far_end_crosstalk": np.max(far_end_crosstalk),
            "net_names": [net["name"] for net in nets]
        }
    
    def _calculate_crosstalk_coupling(self, net1: Dict[str, Any], 
                                    net2: Dict[str, Any], 
                                    stackup: Dict[str, Any]) -> Dict[str, float]:
        """Calculate crosstalk coupling between two nets."""
        # Extract geometric parameters
        spacing = self._calculate_net_spacing(net1, net2)
        length = min(net1.get("length", 10), net2.get("length", 10))
        width1 = net1.get("width", 0.2)
        width2 = net2.get("width", 0.2)
        
        # Stackup parameters
        dielectric_height = stackup.get("dielectric_height", 0.1)  # mm
        dielectric_er = stackup.get("dielectric_constant", 4.3)
        
        # Calculate mutual inductance and capacitance
        mutual_inductance = self._calculate_mutual_inductance(spacing, dielectric_height, length)
        mutual_capacitance = self._calculate_mutual_capacitance(spacing, width1, width2, dielectric_er, length)
        
        # Self inductance and capacitance (approximate)
        self_inductance = 400e-9 * length / 1000  # nH (rough approximation)
        self_capacitance = 100e-12 * length / 1000  # pF (rough approximation)
        
        # Coupling coefficients
        inductive_coupling = mutual_inductance / self_inductance
        capacitive_coupling = mutual_capacitance / self_capacitance
        
        # Crosstalk calculations
        near_end_crosstalk = abs(inductive_coupling - capacitive_coupling) / 2
        far_end_crosstalk = abs(inductive_coupling + capacitive_coupling) / 2
        
        return {
            "near_end_db": 20 * np.log10(max(near_end_crosstalk, 1e-6)),
            "far_end_db": 20 * np.log10(max(far_end_crosstalk, 1e-6)),
            "mutual_inductance_nh": mutual_inductance * 1e9,
            "mutual_capacitance_pf": mutual_capacitance * 1e12,
            "spacing_mm": spacing
        }
    
    def _calculate_net_spacing(self, net1: Dict[str, Any], net2: Dict[str, Any]) -> float:
        """Calculate average spacing between two nets."""
        # Simplified - assume parallel routing
        # Real implementation would analyze actual geometry
        
        # Use routing coordinates if available
        if "route_points" in net1 and "route_points" in net2:
            points1 = net1["route_points"]
            points2 = net2["route_points"]
            
            distances = []
            for p1 in points1:
                for p2 in points2:
                    dist = np.sqrt((p1["x"] - p2["x"])**2 + (p1["y"] - p2["y"])**2)
                    distances.append(dist)
            
            return float(np.mean(distances)) if distances else 1.0
        
        # Default spacing
        return 0.5  # mm
    
    def _calculate_mutual_inductance(self, spacing: float, height: float, length: float) -> float:
        """Calculate mutual inductance between parallel traces."""
        # Neumann's formula approximation
        if spacing <= 0:
            return 0
        
        # Convert to meters
        s_m = spacing / 1000
        h_m = height / 1000
        l_m = length / 1000
        
        # Mutual inductance (simplified)
        mu0 = 4 * np.pi * 1e-7  # H/m
        
        if s_m > h_m:
            mutual_l = (mu0 / (2 * np.pi)) * l_m * np.log(1 + h_m / s_m)
        else:
            mutual_l = (mu0 / (2 * np.pi)) * l_m * (h_m / s_m)
        
        return mutual_l
    
    def _calculate_mutual_capacitance(self, spacing: float, width1: float, 
                                    width2: float, er: float, length: float) -> float:
        """Calculate mutual capacitance between parallel traces."""
        # Convert to meters
        s_m = spacing / 1000
        w1_m = width1 / 1000
        w2_m = width2 / 1000
        l_m = length / 1000
        
        # Mutual capacitance (simplified)
        epsilon0 = 8.854e-12  # F/m
        epsilon = epsilon0 * er
        
        # Approximate for parallel strips
        avg_width = (w1_m + w2_m) / 2
        capacitance = epsilon * l_m * avg_width / s_m
        
        return capacitance


class DesignOptimizer:
    """Automated design optimization loops."""
    
    def __init__(self, simulator: SpiceSimulator, s_param_analyzer: SParameterAnalyzer):
        self.simulator = simulator
        self.s_param_analyzer = s_param_analyzer
        self.optimization_history = []
        
    def optimize_impedance_matching(self, circuit_data: Dict[str, Any], 
                                  target_impedance: float = 50.0) -> Dict[str, Any]:
        """Optimize trace widths for impedance matching."""
        def objective_function(trace_widths):
            # Update circuit with new trace widths
            modified_circuit = circuit_data.copy()
            nets = modified_circuit.get("nets", [])
            
            for i, width in enumerate(trace_widths):
                if i < len(nets):
                    nets[i]["width"] = width
                    # Recalculate impedance based on width
                    nets[i]["impedance"] = self._calculate_impedance_from_width(width)
            
            # Calculate impedance error
            total_error = 0
            for net in nets:
                error = abs(net["impedance"] - target_impedance)
                total_error += error**2
            
            return np.sqrt(total_error)
        
        # Initial trace widths
        nets = circuit_data.get("nets", [])
        initial_widths = [net.get("width", 0.2) for net in nets]
        
        if not initial_widths:
            return {"error": "No nets to optimize"}
        
        # Optimization bounds (trace width limits)
        bounds = [(0.1, 2.0) for _ in initial_widths]  # 0.1mm to 2.0mm
        
        # Simple grid search optimization (replacement for scipy minimize)
        best_widths = initial_widths[:]
        best_score = objective_function(initial_widths)
        
        # Grid search with small steps
        for step in [0.1, 0.05, 0.01]:
            improved = True
            while improved:
                improved = False
                for i in range(len(best_widths)):
                    # Try increasing width
                    test_widths = best_widths[:]
                    test_widths[i] = min(bounds[i][1], test_widths[i] + step)
                    test_score = objective_function(test_widths)
                    if test_score < best_score:
                        best_widths = test_widths
                        best_score = test_score
                        improved = True
                        continue
                    
                    # Try decreasing width
                    test_widths = best_widths[:]
                    test_widths[i] = max(bounds[i][0], test_widths[i] - step)
                    test_score = objective_function(test_widths)
                    if test_score < best_score:
                        best_widths = test_widths
                        best_score = test_score
                        improved = True
        
        # Apply optimized widths
        optimized_circuit = circuit_data.copy()
        for i, width in enumerate(best_widths):
            if i < len(optimized_circuit.get("nets", [])):
                optimized_circuit["nets"][i]["width"] = width
                optimized_circuit["nets"][i]["impedance"] = self._calculate_impedance_from_width(width)
        
        optimization_result = {
            "status": "SUCCESS",
            "original_widths": initial_widths,
            "optimized_widths": best_widths,
            "impedance_error_reduction": objective_function(initial_widths) - best_score,
            "optimized_circuit": optimized_circuit,
            "iterations": len(best_widths) * 3  # Approximate iteration count
        }
        
        self.optimization_history.append(optimization_result)
        return optimization_result
    
    def _calculate_impedance_from_width(self, width: float, 
                                      height: float = 0.1524, 
                                      er: float = 4.3) -> float:
        """Calculate characteristic impedance from trace width."""
        # Microstrip impedance formula
        if width / height >= 1:
            impedance = (87 / np.sqrt(er + 1.41)) * np.log(5.98 * height / (0.8 * width + 0.035))
        else:
            impedance = (60 / np.sqrt(er)) * np.log(4 * height / width)
        
        return impedance
    
    def optimize_power_distribution(self, circuit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize power distribution network."""
        power_nets = circuit_data.get("power_nets", [])
        components = circuit_data.get("components", [])
        
        if not power_nets or not components:
            return {"error": "Insufficient data for power optimization"}
        
        optimization_results = {}
        
        for power_net in power_nets:
            net_name = power_net["name"]
            target_voltage = power_net["voltage"]
            max_voltage_drop_percent = power_net.get("max_voltage_drop_percent", 5.0)
            
            # Calculate current distribution
            total_current = sum(comp.get("power", 1.0) / target_voltage 
                              for comp in components if comp.get("power_pin") == net_name)
            
            # Optimize trace widths for current carrying capacity
            optimized_widths = self._optimize_power_trace_widths(
                power_net, components, total_current, max_voltage_drop_percent
            )
            
            optimization_results[net_name] = {
                "total_current": total_current,
                "optimized_trace_widths": optimized_widths,
                "voltage_drop_analysis": self._analyze_power_voltage_drop(
                    power_net, optimized_widths, total_current
                )
            }
        
        return {
            "status": "SUCCESS",
            "power_net_optimizations": optimization_results,
            "recommendations": self._generate_power_optimization_recommendations(optimization_results)
        }
    
    def _optimize_power_trace_widths(self, power_net: Dict[str, Any], 
                                   components: List[Dict[str, Any]], 
                                   total_current: float, 
                                   max_voltage_drop_percent: float) -> Dict[str, float]:
        """Optimize trace widths for power distribution."""
        # IPC-2221 current capacity calculation
        def calculate_min_width(current, temp_rise=10):
            # I = k * (dT^b) * (A^c)
            k = 0.048  # Internal layers
            b = 0.44
            c = 0.725
            
            area_sq_mils = (current / (k * (temp_rise ** b))) ** (1 / c)
            width_mils = area_sq_mils / 1.4  # 1 oz copper
            return width_mils * 0.0254  # Convert to mm
        
        optimized_widths = {}
        
        # Calculate minimum width for total current
        min_width_total = calculate_min_width(total_current)
        
        # Distribution to individual components
        for component in components:
            if component.get("power_pin") == power_net["name"]:
                comp_current = component.get("power", 1.0) / power_net["voltage"]
                min_width_comp = calculate_min_width(comp_current)
                
                optimized_widths[component["name"]] = max(min_width_comp, 0.2)  # Minimum 0.2mm
        
        # Main power distribution
        optimized_widths["main_distribution"] = max(min_width_total, 0.5)  # Minimum 0.5mm
        
        return optimized_widths
    
    def _analyze_power_voltage_drop(self, power_net: Dict[str, Any], 
                                  trace_widths: Dict[str, float], 
                                  total_current: float) -> Dict[str, Any]:
        """Analyze voltage drop in optimized power distribution."""
        # Simplified voltage drop calculation
        target_voltage = power_net["voltage"]
        
        # Estimate total resistance
        avg_trace_length = 20  # mm (rough estimate)
        avg_trace_width = np.mean(list(trace_widths.values()))
        copper_resistivity = 1.72e-8  # Ohm*m
        copper_thickness = 0.035e-3  # m
        
        total_resistance = (copper_resistivity * avg_trace_length * 1e-3) / (avg_trace_width * 1e-3 * copper_thickness)
        
        voltage_drop = total_current * total_resistance
        voltage_drop_percent = (voltage_drop / target_voltage) * 100
        
        return {
            "voltage_drop": voltage_drop,
            "voltage_drop_percent": voltage_drop_percent,
            "total_resistance_mohms": total_resistance * 1000,
            "efficiency_percent": ((target_voltage - voltage_drop) / target_voltage) * 100,
            "status": "PASS" if voltage_drop_percent < 5.0 else "FAIL"
        }
    
    def _generate_power_optimization_recommendations(self, optimization_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on power optimization results."""
        recommendations = []
        
        for net_name, results in optimization_results.items():
            voltage_drop = results["voltage_drop_analysis"]
            
            if voltage_drop["status"] == "FAIL":
                recommendations.append(f"Increase trace width for {net_name} power net")
                recommendations.append(f"Consider using power planes for {net_name}")
            
            if voltage_drop["voltage_drop_percent"] > 3.0:
                recommendations.append(f"Add decoupling capacitors near high-current components on {net_name}")
            
            if results["total_current"] > 1.0:
                recommendations.append(f"Consider thermal vias for {net_name} high-current traces")
        
        if not recommendations:
            recommendations.append("Power distribution optimization is adequate")
        
        return recommendations


class AdvancedValidationEngine:
    """Main validation engine that orchestrates all validation types."""
    
    def __init__(self, spice_executable: str = "ngspice"):
        self.spice_sim = SpiceSimulator(spice_executable)
        self.s_param_analyzer = SParameterAnalyzer()
        self.crosstalk_analyzer = CrosstalkAnalyzer()
        self.optimizer = DesignOptimizer(self.spice_sim, self.s_param_analyzer)
        
    def run_comprehensive_validation(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive design validation."""
        results = {
            "validation_timestamp": "2025-01-01T00:00:00Z",
            "design_data": design_data,
            "validation_results": {}
        }
        
        try:
            # SPICE simulation
            if design_data.get("components"):
                spice_results = self._run_spice_validation(design_data)
                results["validation_results"]["spice_simulation"] = spice_results
            
            # S-parameter analysis
            if design_data.get("nets"):
                s_param_results = self._run_s_parameter_analysis(design_data)
                results["validation_results"]["s_parameters"] = s_param_results
            
            # Crosstalk analysis
            if len(design_data.get("nets", [])) > 1:
                crosstalk_results = self._run_crosstalk_analysis(design_data)
                results["validation_results"]["crosstalk"] = crosstalk_results
            
            # Design optimization
            optimization_results = self._run_design_optimization(design_data)
            results["validation_results"]["optimization"] = optimization_results
            
            # Overall assessment
            results["overall_validation_status"] = self._assess_validation_status(results["validation_results"])
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            results["error"] = str(e)
            results["overall_validation_status"] = "ERROR"
        
        return results
    
    def _run_spice_validation(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run SPICE simulation validation."""
        try:
            # Generate netlist
            netlist = self.spice_sim.generate_netlist(design_data)
            
            # Write netlist file
            netlist_file = self.spice_sim.write_netlist_file(netlist, "validation.cir")
            
            # Run simulation
            sim_results = self.spice_sim.run_simulation(netlist_file)
            
            return {
                "netlist_generation": "SUCCESS",
                "simulation_results": sim_results,
                "component_count": len(netlist.components),
                "analysis_types": len(netlist.analysis)
            }
            
        except Exception as e:
            return {
                "netlist_generation": "FAILED",
                "error": str(e)
            }
    
    def _run_s_parameter_analysis(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run S-parameter analysis."""
        try:
            # Calculate S-parameters
            s_params = self.s_param_analyzer.calculate_s_parameters(
                design_data, 
                (1e6, 1e9),  # 1 MHz to 1 GHz
                100
            )
            
            # Analyze insertion loss
            insertion_loss = self.s_param_analyzer.analyze_insertion_loss(s_params)
            
            # Analyze return loss
            return_loss = self.s_param_analyzer.analyze_return_loss(s_params)
            
            # Calculate VSWR
            vswr = self.s_param_analyzer.calculate_vswr(s_params)
            
            return {
                "frequency_points": len(s_params),
                "insertion_loss": {
                    "max_loss_db": max(insertion_loss.magnitude_db),
                    "loss_at_1ghz_db": insertion_loss.magnitude_db[-1] if insertion_loss.magnitude_db else 0
                },
                "return_loss": {
                    "min_return_loss_db": min(return_loss.magnitude_db),
                    "return_loss_at_1ghz_db": return_loss.magnitude_db[-1] if return_loss.magnitude_db else 0
                },
                "vswr": {
                    "max_vswr": max(vswr),
                    "vswr_at_1ghz": vswr[-1] if vswr else 1.0
                },
                "status": "PASS" if max(vswr) < 2.0 else "FAIL"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "ERROR"
            }
    
    def _run_crosstalk_analysis(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run crosstalk analysis."""
        try:
            nets = design_data.get("nets", [])
            stackup = design_data.get("stackup", {
                "dielectric_height": 0.1524,
                "dielectric_constant": 4.3
            })
            
            crosstalk_results = self.crosstalk_analyzer.analyze_crosstalk_matrix(nets, stackup)
            
            return {
                "net_count": len(nets),
                "critical_pairs": len(crosstalk_results["critical_pairs"]),
                "max_near_end_crosstalk_db": crosstalk_results["max_near_end_crosstalk"],
                "max_far_end_crosstalk_db": crosstalk_results["max_far_end_crosstalk"],
                "critical_crosstalk_pairs": crosstalk_results["critical_pairs"],
                "status": "PASS" if crosstalk_results["max_near_end_crosstalk"] < -30 else "FAIL"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "ERROR"
            }
    
    def _run_design_optimization(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run design optimization."""
        try:
            results = {}
            
            # Impedance optimization
            if design_data.get("nets"):
                impedance_opt = self.optimizer.optimize_impedance_matching(design_data)
                results["impedance_optimization"] = impedance_opt
            
            # Power optimization
            if design_data.get("power_nets"):
                power_opt = self.optimizer.optimize_power_distribution(design_data)
                results["power_optimization"] = power_opt
            
            return results
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "ERROR"
            }
    
    def _assess_validation_status(self, validation_results: Dict[str, Any]) -> str:
        """Assess overall validation status."""
        issues = []
        
        # Check SPICE results
        spice_results = validation_results.get("spice_simulation", {})
        if spice_results.get("simulation_results", {}).get("status") == "FAILED":
            issues.append("SPICE simulation failed")
        
        # Check S-parameters
        s_param_results = validation_results.get("s_parameters", {})
        if s_param_results.get("status") == "FAIL":
            issues.append("S-parameter analysis failed")
        
        # Check crosstalk
        crosstalk_results = validation_results.get("crosstalk", {})
        if crosstalk_results.get("status") == "FAIL":
            issues.append("Excessive crosstalk detected")
        
        # Check optimization
        optimization_results = validation_results.get("optimization", {})
        if "error" in optimization_results:
            issues.append("Design optimization failed")
        
        if not issues:
            return "PASS"
        elif len(issues) <= 2:
            return "PASS_WITH_WARNINGS"
        else:
            return "FAIL"


def create_validation_engine(config: Optional[Dict[str, Any]] = None) -> AdvancedValidationEngine:
    """Factory function to create validation engine."""
    if config is None:
        config = {}
    
    spice_executable = config.get("spice_executable", "ngspice")
    return AdvancedValidationEngine(spice_executable)