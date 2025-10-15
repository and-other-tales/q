# Copyright © 2025 PI & Other Tales Inc.. All Rights Reserved.
"""Comprehensive tests for advanced simulation capabilities."""

import pytest
import numpy as np
import tempfile
import os
from unittest.mock import patch, MagicMock

from src.agent.advanced_simulation import (
    AdvancedSimulationEngine, SignalIntegrityAnalyzer, PowerIntegrityAnalyzer,
    ThermalAnalyzer, EMCAnalyzer, create_simulation_engine, SimulationPoint,
    NetSegment, Component
)


class TestSignalIntegrityAnalyzer:
    """Test signal integrity analysis functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.board_config = {
            "dielectric_constant": 4.3,
            "layer_thickness": 0.1524,
            "copper_thickness": 0.035
        }
        self.analyzer = SignalIntegrityAnalyzer(self.board_config)
    
    def test_calculate_trace_impedance(self):
        """Test trace impedance calculation."""
        impedance = self.analyzer.calculate_trace_impedance(0.2, 0.035, 0.1524)
        
        # Should be approximately 50 ohms for typical microstrip
        assert 40 <= impedance <= 60, f"Impedance {impedance} outside expected range"
    
    def test_calculate_differential_impedance(self):
        """Test differential impedance calculation."""
        diff_impedance = self.analyzer.calculate_differential_impedance(0.15, 0.2, 0.1524)
        
        # Should be approximately 90-100 ohms for typical diff pair
        assert 80 <= diff_impedance <= 110, f"Differential impedance {diff_impedance} outside expected range"
    
    def test_analyze_crosstalk(self):
        """Test crosstalk analysis between net segments."""
        aggressor = NetSegment(
            start=SimulationPoint(0, 0, 1),
            end=SimulationPoint(10, 0, 1),
            width=0.2,
            impedance=50.0,
            length=10.0,
            layer=1
        )
        
        victim = NetSegment(
            start=SimulationPoint(0, 1, 1),  # 1mm away
            end=SimulationPoint(10, 1, 1),
            width=0.2,
            impedance=50.0,
            length=10.0,
            layer=1
        )
        
        crosstalk = self.analyzer.analyze_crosstalk(aggressor, victim)
        
        assert "near_end_crosstalk_db" in crosstalk
        assert "far_end_crosstalk_db" in crosstalk
        assert crosstalk["near_end_crosstalk_db"] < 0  # Should be negative dB
        assert crosstalk["distance_mm"] == 1.0
    
    def test_analyze_reflection(self):
        """Test signal reflection analysis."""
        segments = [
            NetSegment(
                start=SimulationPoint(0, 0, 1),
                end=SimulationPoint(5, 0, 1),
                width=0.2,
                impedance=50.0,
                length=5.0,
                layer=1
            ),
            NetSegment(
                start=SimulationPoint(5, 0, 1),
                end=SimulationPoint(10, 0, 1),
                width=0.3,  # Different width -> impedance mismatch
                impedance=40.0,
                length=5.0,
                layer=1
            )
        ]
        
        reflection = self.analyzer.analyze_reflection(segments)
        
        assert "reflection_points" in reflection
        assert "total_return_loss_db" in reflection
        assert len(reflection["reflection_points"]) == len(segments)
    
    def test_analyze_timing(self):
        """Test timing analysis."""
        segments = [
            NetSegment(
                start=SimulationPoint(0, 0, 1),
                end=SimulationPoint(20, 0, 1),
                width=0.2,
                impedance=50.0,
                length=20.0,
                layer=1
            )
        ]
        
        timing = self.analyzer.analyze_timing(segments, rise_time_ps=100.0)
        
        assert "total_length_mm" in timing
        assert "propagation_delay_ps" in timing
        assert "bandwidth_ghz" in timing
        assert timing["total_length_mm"] == 20.0
        assert timing["propagation_delay_ps"] > 0


class TestPowerIntegrityAnalyzer:
    """Test power integrity analysis functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.board_config = {"dielectric_constant": 4.3}
        self.analyzer = PowerIntegrityAnalyzer(self.board_config)
    
    def test_analyze_voltage_drop(self):
        """Test voltage drop analysis."""
        power_nets = [
            {
                "name": "VCC",
                "voltage": 5.0,
                "max_current": 1.0,
                "plane_thickness": 0.035,
                "area": 1000  # mm²
            }
        ]
        
        components = [
            Component(
                name="U1",
                x=10.0,
                y=10.0,
                power_dissipation=0.5,
                thermal_resistance=50.0,
                package_type="SOIC8",
                pins=["1", "2", "3", "4", "5", "6", "7", "8"]
            )
        ]
        
        voltage_drop = self.analyzer.analyze_voltage_drop(power_nets, components)
        
        assert "VCC" in voltage_drop
        vcc_analysis = voltage_drop["VCC"]
        assert "voltage_drop_percent" in vcc_analysis
        assert "worst_case_component" in vcc_analysis
        assert vcc_analysis["target_voltage"] == 5.0
    
    def test_analyze_power_plane_resonance(self):
        """Test power plane resonance analysis."""
        plane_dimensions = (0.1, 0.08)  # 100mm x 80mm in meters
        dielectric_thickness = 0.1524e-3  # mm to meters
        
        resonance = self.analyzer.analyze_power_plane_resonance(
            plane_dimensions, dielectric_thickness
        )
        
        assert "resonant_frequencies" in resonance
        assert "fundamental_frequency_ghz" in resonance
        assert len(resonance["resonant_frequencies"]) > 0
        assert resonance["fundamental_frequency_ghz"] > 0


class TestThermalAnalyzer:
    """Test thermal analysis functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.board_config = {"ambient_temperature": 25.0}
        self.analyzer = ThermalAnalyzer(self.board_config)
    
    def test_analyze_component_temperatures(self):
        """Test component temperature analysis."""
        components = [
            Component(
                name="U1",
                x=10.0,
                y=10.0,
                power_dissipation=1.0,  # 1W
                thermal_resistance=50.0,  # 50°C/W
                package_type="QFP64",
                pins=[]
            ),
            Component(
                name="R1",
                x=20.0,
                y=20.0,
                power_dissipation=0.1,  # 0.1W
                thermal_resistance=100.0,  # 100°C/W
                package_type="0805",
                pins=[]
            )
        ]
        
        thermal_analysis = self.analyzer.analyze_component_temperatures(components)
        
        assert "component_temperatures" in thermal_analysis
        assert "thermal_hotspots" in thermal_analysis
        assert "max_temperature" in thermal_analysis
        
        # U1 should have higher temperature due to higher power
        u1_temp = thermal_analysis["component_temperatures"]["U1"]["junction_temperature"]
        r1_temp = thermal_analysis["component_temperatures"]["R1"]["junction_temperature"]
        assert u1_temp > r1_temp
        
        # Check for hotspots (>85°C)
        u1_expected_temp = 25.0 + 1.0 * 50.0  # 75°C
        assert abs(u1_temp - u1_expected_temp) < 1.0
    
    def test_calculate_thermal_vias(self):
        """Test thermal via calculation."""
        hotspot_locations = [(10.0, 10.0), (30.0, 30.0)]
        power_density = 2.0  # W
        
        via_calc = self.analyzer.calculate_thermal_vias(hotspot_locations, power_density)
        
        assert "via_recommendations" in via_calc
        assert "total_vias_needed" in via_calc
        assert len(via_calc["via_recommendations"]) == 2
        assert via_calc["total_vias_needed"] > 0


class TestEMCAnalyzer:
    """Test EMC analysis functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.board_config = {}
        self.analyzer = EMCAnalyzer(self.board_config)
    
    def test_analyze_emi_emissions(self):
        """Test EMI emissions analysis."""
        clock_frequencies = [16.0, 48.0, 100.0]  # MHz
        trace_lengths = {"CLK": 25.0, "DATA": 15.0, "USB": 10.0}  # mm
        
        emi_analysis = self.analyzer.analyze_emi_emissions(clock_frequencies, trace_lengths)
        
        assert "critical_frequencies" in emi_analysis
        assert "max_frequency_mhz" in emi_analysis
        assert "high_concern_count" in emi_analysis
        assert "recommendations" in emi_analysis
        
        # Should have multiple harmonics
        assert len(emi_analysis["critical_frequencies"]) > len(clock_frequencies)
    
    def test_analyze_esd_protection(self):
        """Test ESD protection analysis."""
        io_pins = [
            {"name": "USB_DP", "type": "usb", "voltage": 3.3},
            {"name": "GPIO1", "type": "digital_io", "voltage": 3.3},
            {"name": "ANALOG_IN", "type": "analog_input", "voltage": 5.0}
        ]
        
        esd_analysis = self.analyzer.analyze_esd_protection(io_pins)
        
        assert "pin_analysis" in esd_analysis
        assert "protection_components" in esd_analysis
        assert "high_risk_pins" in esd_analysis
        
        # USB pins should be high risk
        assert "USB_DP" in esd_analysis["high_risk_pins"]


class TestAdvancedSimulationEngine:
    """Test the main simulation engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.board_config = {
            "dielectric_constant": 4.3,
            "layer_thickness": 0.1524,
            "copper_thickness": 0.035,
            "ambient_temperature": 25.0,
            "thermal_conductivity": 0.3
        }
        self.engine = AdvancedSimulationEngine(self.board_config)
    
    def test_run_comprehensive_analysis(self):
        """Test comprehensive simulation analysis."""
        design_data = {
            "name": "Test Design",
            "components": [
                {
                    "name": "U1",
                    "type": "microcontroller",
                    "value": "STM32F4",
                    "power_dissipation": 0.5,
                    "thermal_resistance": 40.0,
                    "package_type": "LQFP64",
                    "pins": ["1", "2"],
                    "x": 10.0,
                    "y": 10.0,
                    "width": 10.0,
                    "height": 10.0
                }
            ],
            "nets": [
                {
                    "name": "CLK",
                    "length": 20.0,
                    "width": 0.2,
                    "impedance": 50.0
                }
            ],
            "clock_frequencies": [16.0],
            "io_pins": [
                {"name": "GPIO1", "type": "digital_io", "voltage": 3.3}
            ],
            "power_nets": [
                {"name": "VCC", "voltage": 3.3, "max_current": 0.5}
            ]
        }
        
        results = self.engine.run_comprehensive_analysis(design_data)
        
        assert "simulation_timestamp" in results
        assert "analysis_results" in results
        assert "overall_status" in results
        
        analysis = results["analysis_results"]
        
        # Check that all analysis types are present
        expected_analyses = ["signal_integrity", "power_integrity", "thermal", "emc"]
        for analysis_type in expected_analyses:
            if analysis_type in analysis:
                assert isinstance(analysis[analysis_type], dict)
    
    def test_assess_overall_status(self):
        """Test overall status assessment."""
        # Test PASS case
        analysis_results = {
            "signal_integrity": {"NET1": {"reflections": {"worst_reflection_db": -20}}},
            "power_integrity": {"VCC": {"status": "PASS"}},
            "thermal": {"thermal_hotspots": []},
            "emc": {"high_concern_count": 0}
        }
        
        status = self.engine._assess_overall_status(analysis_results)
        assert status == "PASS"
        
        # Test FAIL case
        analysis_results["power_integrity"]["VCC"]["status"] = "FAIL"
        analysis_results["thermal"]["thermal_hotspots"] = [{"component": "U1"}]
        
        status = self.engine._assess_overall_status(analysis_results)
        assert status == "FAIL"


class TestSimulationEngineIntegration:
    """Integration tests for simulation engine."""
    
    def test_create_simulation_engine(self):
        """Test factory function."""
        engine = create_simulation_engine()
        assert isinstance(engine, AdvancedSimulationEngine)
        
        # Test with custom config
        custom_config = {"dielectric_constant": 3.0}
        engine = create_simulation_engine(custom_config)
        assert engine.board_config["dielectric_constant"] == 3.0
    
    @pytest.mark.asyncio
    async def test_simulation_engine_with_large_dataset(self):
        """Test simulation engine with large dataset."""
        engine = create_simulation_engine()
        
        # Create large design
        design_data = {
            "name": "Large Design",
            "components": [
                {
                    "name": f"R{i}",
                    "type": "resistor",
                    "value": "1k",
                    "power_dissipation": 0.1,
                    "thermal_resistance": 100.0,
                    "package_type": "0805",
                    "pins": ["1", "2"],
                    "x": float(i % 10 * 5),
                    "y": float(i // 10 * 5),
                    "width": 2.0,
                    "height": 1.0
                } for i in range(50)  # 50 components
            ],
            "nets": [
                {
                    "name": f"NET_{i}",
                    "length": 10.0 + i,
                    "width": 0.2,
                    "impedance": 50.0
                } for i in range(20)  # 20 nets
            ],
            "clock_frequencies": [16.0, 48.0, 100.0],
            "io_pins": [],
            "power_nets": [{"name": "VCC", "voltage": 5.0, "max_current": 2.0}]
        }
        
        results = engine.run_comprehensive_analysis(design_data)
        
        assert results["overall_status"] in ["PASS", "PASS_WITH_WARNINGS", "FAIL"]
        assert "analysis_results" in results


if __name__ == "__main__":
    pytest.main([__file__])