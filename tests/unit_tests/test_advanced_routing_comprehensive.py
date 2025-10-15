"""Comprehensive tests for advanced routing functionality."""

import pytest
import math
from typing import List, Dict, Any

from src.agent.advanced_routing import (
    Point, RouteSegment, Via, ViaType, DifferentialPair, RoutingConstraint,
    RoutingGrid, AStarRouter, DifferentialPairRouter, ViaOptimizer, 
    PowerPlaneRouter, AdvancedRoutingEngine, create_routing_engine
)


class TestPoint:
    """Test Point class functionality."""
    
    def test_point_creation(self):
        """Test Point creation and basic properties."""
        p = Point(10.0, 20.0, 1)
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.layer == 1
    
    def test_point_distance(self):
        """Test distance calculation."""
        p1 = Point(0.0, 0.0, 0)
        p2 = Point(3.0, 4.0, 0)
        
        distance = p1.distance_to(p2)
        assert abs(distance - 5.0) < 0.001  # 3-4-5 triangle
    
    def test_point_equality(self):
        """Test point equality comparison."""
        p1 = Point(10.0, 20.0, 1)
        p2 = Point(10.0, 20.0, 1)
        p3 = Point(10.0, 20.0, 2)
        
        assert p1 == p2
        assert p1 != p3


class TestRoutingGrid:
    """Test routing grid functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.grid = RoutingGrid(
            width=100.0,
            height=80.0,
            layers=4,
            resolution=0.1
        )
    
    def test_grid_creation(self):
        """Test routing grid creation."""
        assert self.grid.width == 100.0
        assert self.grid.height == 80.0
        assert self.grid.layers == 4
        assert self.grid.resolution == 0.1
    
    def test_grid_coordinates(self):
        """Test coordinate conversion."""
        point = Point(50.0, 40.0, 1)
        grid_coords = self.grid.to_grid_coords(point)
        
        # Check grid coordinates are within bounds
        assert 0 <= grid_coords[0] < self.grid.grid_width
        assert 0 <= grid_coords[1] < self.grid.grid_height
        assert 0 <= grid_coords[2] < self.grid.layers
    
    def test_mark_blocked_region(self):
        """Test blocked region management."""
        region = {
            "x1": 10.0, "y1": 10.0,
            "x2": 20.0, "y2": 20.0,
            "layer": 1
        }
        self.grid.mark_blocked(region)
        
        # Test that region is marked as blocked
        test_point = Point(15.0, 15.0, 1)
        x, y, z = self.grid.to_grid_coords(test_point)
        assert self.grid.grid[x][y][z].blocked
    
    def test_physical_coordinates(self):
        """Test coordinate conversion back to physical."""
        point = self.grid.to_physical_coords(10, 20, 1)
        
        assert point.x == 10 * self.grid.resolution
        assert point.y == 20 * self.grid.resolution
        assert point.layer == 1


class TestDifferentialPairRouter:
    """Test differential pair routing functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.grid = RoutingGrid(100.0, 80.0, 4, 0.1)
        self.router = DifferentialPairRouter(self.grid)
    
    def test_differential_spacing_calculation(self):
        """Test differential spacing calculation."""
        spacing = self.router.calculate_differential_spacing(
            impedance=90.0,
            trace_width=0.15,
            dielectric_height=0.1524,
            dielectric_er=4.3
        )
        
        assert spacing > 0
        assert spacing >= 0.15 * 2  # Minimum 2x trace width
    
    def test_differential_pair_creation(self):
        """Test DifferentialPair dataclass."""
        diff_pair = DifferentialPair(
            positive_net="USB_DP",
            negative_net="USB_DN",
            target_impedance=90.0,
            max_length_mismatch=0.1,
            coupling_spacing=0.2,
            trace_width=0.15
        )
        
        assert diff_pair.positive_net == "USB_DP"
        assert diff_pair.negative_net == "USB_DN"
        assert diff_pair.target_impedance == 90.0


class TestViaOptimizer:
    """Test via optimization functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.grid = RoutingGrid(100.0, 80.0, 4, 0.1)
        self.optimizer = ViaOptimizer(self.grid)
    
    def test_via_creation(self):
        """Test Via dataclass creation."""
        via = Via(
            position=Point(10, 10, 1),
            start_layer=1,
            end_layer=3,
            drill_size=0.2,
            via_type=ViaType.THROUGH,
            net_name="TEST_NET"
        )
        
        assert via.position.x == 10
        assert via.position.y == 10
        assert via.start_layer == 1
        assert via.end_layer == 3
        assert via.drill_size == 0.2
        assert via.via_type == ViaType.THROUGH
        assert via.net_name == "TEST_NET"
    
    def test_via_optimization(self):
        """Test via optimization with route segments."""
        # Create some test segments
        segments = [
            RouteSegment(
                start=Point(10, 10, 0),
                end=Point(10, 10, 1),
                width=0.2,
                layer=0,
                net_name="TEST_NET"
            ),
            RouteSegment(
                start=Point(10, 10, 1),
                end=Point(20, 10, 1),
                width=0.2,
                layer=1,
                net_name="TEST_NET"
            )
        ]
        
        vias = self.optimizer.optimize_via_placement(segments)
        
        # Should return a list of vias
        assert isinstance(vias, list)


class TestPowerPlaneRouter:
    """Test power plane routing functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.grid = RoutingGrid(100.0, 80.0, 4, 0.1)
        self.router = PowerPlaneRouter(self.grid)
    
    def test_power_router_creation(self):
        """Test PowerPlaneRouter creation."""
        assert self.router.grid == self.grid


class TestAdvancedRoutingEngine:
    """Test complete routing engine integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = create_routing_engine(100.0, 80.0, 4, 0.1)
    
    def test_engine_creation(self):
        """Test routing engine creation via factory."""
        assert self.engine.grid.width == 100.0
        assert self.engine.grid.height == 80.0
        assert self.engine.grid.layers == 4
    
    def test_design_routing_basic(self):
        """Test basic design routing."""
        design_data = {
            "nets": [
                {
                    "name": "TEST_NET",
                    "pins": [
                        {"x": 10, "y": 10, "layer": 0},
                        {"x": 50, "y": 50, "layer": 0}
                    ]
                }
            ],
            "components": [],
            "differential_pairs": [],
            "routing_constraints": []
        }
        
        result = self.engine.route_design(design_data)
        
        # Check that result contains expected fields
        assert "routing_timestamp" in result
        assert "design_data" in result
        assert "routing_results" in result


class TestRoutingConstraints:
    """Test routing constraint functionality."""
    
    def test_routing_constraint_creation(self):
        """Test RoutingConstraint dataclass."""
        constraint = RoutingConstraint(
            net_name="CLK",
            min_width=0.1,
            max_width=0.3,
            min_spacing=0.1,
            max_length=50.0,
            target_impedance=50.0
        )
        
        assert constraint.net_name == "CLK"
        assert constraint.min_width == 0.1
        assert constraint.target_impedance == 50.0


class TestFactoryFunctions:
    """Test factory functions and module-level utilities."""
    
    def test_create_routing_engine(self):
        """Test routing engine factory function."""
        engine = create_routing_engine(
            board_width=120.0,
            board_height=100.0,
            layers=6,
            resolution=0.05
        )
        
        assert isinstance(engine, AdvancedRoutingEngine)
        assert engine.grid.width == 120.0
        assert engine.grid.height == 100.0
        assert engine.grid.layers == 6
        assert engine.grid.resolution == 0.05


class TestIntegrationTests:
    """Integration tests combining multiple components."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.engine = create_routing_engine(100.0, 80.0, 4)
    
    def test_basic_workflow_integration(self):
        """Test basic routing workflow."""
        # Create a simple design with components and nets
        design_data = {
            "nets": [
                {
                    "name": "VCC",
                    "pins": [{"x": 10, "y": 10, "layer": 0}, {"x": 90, "y": 70, "layer": 0}]
                },
                {
                    "name": "GND", 
                    "pins": [{"x": 15, "y": 15, "layer": 0}, {"x": 85, "y": 65, "layer": 0}]
                }
            ],
            "components": [
                {
                    "name": "U1",
                    "x": 50, "y": 40,
                    "width": 5.0, "height": 3.0
                }
            ],
            "differential_pairs": [],
            "routing_constraints": []
        }
        
        # Route the design
        result = self.engine.route_design(design_data)
        
        # Verify basic result structure
        assert isinstance(result, dict)
        assert "routing_results" in result
        assert "design_data" in result
        
        # Verify design data is preserved
        assert result["design_data"] == design_data