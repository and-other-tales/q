"""Comprehensive tests for advanced validation functionality."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

from src.agent.advanced_validation import (
    SpiceNetlist, SpiceComponent, SParameter, FrequencyResponse,
    ValidationReport, SpiceSimulator, SParameterAnalyzer, CrosstalkAnalyzer,
    DesignOptimizer, AdvancedValidationEngine, create_validation_engine
)


class TestSpiceNetlist:
    """Test SPICE netlist functionality."""
    
    def test_netlist_creation(self):
        """Test SpiceNetlist creation."""
        components = [
            SpiceComponent(name="R1", component_type="R", value="1k", nodes=["1", "2"]),
            SpiceComponent(name="C1", component_type="C", value="100n", nodes=["2", "0"])
        ]
        
        netlist = SpiceNetlist(
            title="Test Circuit",
            components=components,
            models=[".model NMOS NMOS"],
            analysis=[".ac dec 100 1 1G"],
            includes=[]
        )
        
        assert netlist.title == "Test Circuit"
        assert len(netlist.components) == 2
        assert netlist.components[0].name == "R1"
        assert netlist.components[1].component_type == "C"
    
    def test_netlist_generation(self):
        """Test netlist string generation."""
        components = [
            SpiceComponent(name="R1", component_type="R", value="1k", nodes=["1", "0"])
        ]
        
        netlist = SpiceNetlist(
            title="Simple RC",
            components=components,
            models=[],
            analysis=[".op"],
            includes=[]
        )
        
        netlist_str = netlist.generate()
        
        assert "Simple RC" in netlist_str
        assert "R1 1 0 1k" in netlist_str
        assert ".op" in netlist_str
        assert ".end" in netlist_str


class TestSpiceComponent:
    """Test SPICE component functionality."""
    
    def test_component_creation(self):
        """Test SpiceComponent creation."""
        component = SpiceComponent(
            name="R1",
            component_type="R",
            value="10k",
            nodes=["VCC", "OUT"]
        )
        
        assert component.name == "R1"
        assert component.component_type == "R"
        assert component.value == "10k"
        assert component.nodes == ["VCC", "OUT"]
    
    def test_component_line_generation(self):
        """Test component SPICE line generation."""
        component = SpiceComponent(
            name="C1",
            component_type="C",
            value="1u",
            nodes=["IN", "GND"]
        )
        
        line = component.to_spice_line()
        
        assert line == "C1 IN GND 1u"


class TestFrequencyResponse:
    """Test frequency response functionality."""
    
    def test_frequency_response_creation(self):
        """Test FrequencyResponse creation."""
        response = FrequencyResponse(
            frequencies=[1e3, 1e4, 1e5],
            magnitude=[0.0, -3.0, -20.0],
            phase=[0.0, -45.0, -90.0]
        )
        
        assert len(response.frequencies) == 3
        assert response.magnitude[1] == -3.0
        assert response.phase[2] == -90.0


class TestSpiceSimulator:
    """Test SPICE simulator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.simulator = SpiceSimulator("ngspice")
    
    def test_simulator_creation(self):
        """Test SpiceSimulator creation."""
        assert self.simulator.spice_executable == "ngspice"
        assert hasattr(self.simulator, 'temp_dir')
    
    def test_netlist_generation(self):
        """Test netlist generation from circuit data."""
        circuit_data = {
            "name": "Test Circuit",
            "components": [
                {
                    "name": "R1",
                    "type": "resistor",
                    "value": "1k",
                    "pins": ["1", "2"]
                },
                {
                    "name": "C1",
                    "type": "capacitor",
                    "value": "100n",
                    "pins": ["2", "0"]
                }
            ],
            "nets": []
        }
        
        netlist = self.simulator.generate_netlist(circuit_data)
        
        assert isinstance(netlist, SpiceNetlist)
        assert "Test Circuit" in netlist.title
        assert len(netlist.components) >= 2
        
        # Check that components were converted properly
        component_names = [comp.name for comp in netlist.components]
        assert any("R" in name for name in component_names)
        assert any("C" in name for name in component_names)


class TestSParameterAnalyzer:
    """Test S-parameter analysis functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = SParameterAnalyzer()
    
    def test_analyzer_creation(self):
        """Test SParameterAnalyzer creation."""
        assert isinstance(self.analyzer, SParameterAnalyzer)
    
    def test_s_parameter_creation(self):
        """Test SParameter creation."""
        s_param = SParameter(
            frequency=1e9,
            s11=complex(0.1, 0.05),
            s12=complex(0.8, -0.2),
            s21=complex(0.8, -0.2),
            s22=complex(0.1, 0.05)
        )
        
        assert s_param.frequency == 1e9
        assert s_param.s11.real == 0.1
        assert s_param.s21.imag == -0.2


class TestCrosstalkAnalyzer:
    """Test crosstalk analysis functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = CrosstalkAnalyzer()
    
    def test_analyzer_creation(self):
        """Test CrosstalkAnalyzer creation."""
        assert isinstance(self.analyzer, CrosstalkAnalyzer)


class TestDesignOptimizer:
    """Test design optimization functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        spice_sim = SpiceSimulator()
        s_param_analyzer = SParameterAnalyzer()
        self.optimizer = DesignOptimizer(spice_sim, s_param_analyzer)
    
    def test_optimizer_creation(self):
        """Test DesignOptimizer creation."""
        assert isinstance(self.optimizer, DesignOptimizer)
        assert hasattr(self.optimizer, 'spice_sim')
        assert hasattr(self.optimizer, 's_param_analyzer')


class TestAdvancedValidationEngine:
    """Test advanced validation engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = AdvancedValidationEngine("ngspice")
    
    def test_engine_creation(self):
        """Test AdvancedValidationEngine creation."""
        assert isinstance(self.engine, AdvancedValidationEngine)
        assert hasattr(self.engine, 'spice_sim')
        assert hasattr(self.engine, 's_param_analyzer')
        assert hasattr(self.engine, 'crosstalk_analyzer')
        assert hasattr(self.engine, 'optimizer')
    
    def test_comprehensive_validation(self):
        """Test comprehensive design validation."""
        design_data = {
            "name": "Test PCB",
            "components": [
                {
                    "name": "R1",
                    "type": "resistor",
                    "value": "1k",
                    "pins": ["VCC", "OUT"]
                }
            ],
            "nets": [
                {
                    "name": "VCC",
                    "length": 10.0,
                    "width": 0.2,
                    "impedance": 50.0
                }
            ]
        }
        
        result = self.engine.run_comprehensive_validation(design_data)
        
        assert "validation_timestamp" in result
        assert "design_data" in result
        assert "validation_results" in result
        assert "overall_validation_status" in result
        
        # Verify the design data is preserved
        assert result["design_data"] == design_data


class TestValidationReport:
    """Test validation report functionality."""
    
    def test_report_creation(self):
        """Test ValidationReport creation."""
        report = ValidationReport(
            design_name="Test Design",
            validation_status="PASS",
            summary="All tests passed",
            details={"spice": "OK", "s_parameters": "OK"}
        )
        
        assert report.design_name == "Test Design"
        assert report.validation_status == "PASS"
        assert report.summary == "All tests passed"
        assert report.details["spice"] == "OK"


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_validation_engine(self):
        """Test validation engine factory function."""
        engine = create_validation_engine()
        
        assert isinstance(engine, AdvancedValidationEngine)
    
    def test_create_validation_engine_with_config(self):
        """Test validation engine factory with custom config."""
        config = {
            "spice_executable": "ltspice"
        }
        
        engine = create_validation_engine(config)
        
        assert isinstance(engine, AdvancedValidationEngine)


class TestIntegrationTests:
    """Integration tests combining validation components."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.engine = create_validation_engine()
    
    def test_validation_workflow(self):
        """Test complete validation workflow."""
        # Create a realistic design for validation
        design_data = {
            "name": "USB Interface PCB",
            "components": [
                {
                    "name": "R1",
                    "type": "resistor",
                    "value": "90",
                    "pins": ["USB_DP", "USB_DP_OUT"]
                },
                {
                    "name": "R2", 
                    "type": "resistor",
                    "value": "90",
                    "pins": ["USB_DN", "USB_DN_OUT"]
                },
                {
                    "name": "C1",
                    "type": "capacitor", 
                    "value": "22p",
                    "pins": ["USB_DP", "GND"]
                }
            ],
            "nets": [
                {
                    "name": "USB_DP",
                    "length": 15.0,
                    "width": 0.15,
                    "impedance": 90.0
                },
                {
                    "name": "USB_DN",
                    "length": 15.2,
                    "width": 0.15, 
                    "impedance": 90.0
                }
            ],
            "clock_frequencies": [48.0],  # MHz
            "io_pins": [
                {"name": "USB_DP", "type": "usb", "voltage": 3.3},
                {"name": "USB_DN", "type": "usb", "voltage": 3.3}
            ]
        }
        
        # Run validation
        result = self.engine.run_comprehensive_validation(design_data)
        
        # Verify the result structure
        assert isinstance(result, dict)
        assert "validation_results" in result
        assert "overall_validation_status" in result
        
        # Should not error out
        assert result["overall_validation_status"] != "ERROR"
        
        # Should have at least some validation results
        validation_results = result["validation_results"]
        assert isinstance(validation_results, dict)
        
        # Results may include spice simulation, s-parameters, etc.
        # depending on what was actually executed