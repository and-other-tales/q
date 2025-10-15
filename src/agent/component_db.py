# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""
Component database for PCB design.
Provides component search, selection, and management capabilities.
"""

from typing import Dict, List, Any, Optional
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Component:
    """Represents an electronic component with specifications."""
    name: str
    category: str
    manufacturer: str
    part_number: str
    description: str
    package: str
    voltage_rating: Optional[str] = None
    current_rating: Optional[str] = None
    power_rating: Optional[str] = None
    tolerance: Optional[str] = None
    value: Optional[str] = None
    footprint: Optional[str] = None
    datasheet_url: Optional[str] = None
    price_usd: Optional[float] = None
    availability: str = "Available"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert component to dictionary."""
        return asdict(self)


class ComponentDatabase:
    """Component database for searching and managing electronic components."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize component database."""
        self.db_path = db_path or "component_db.json"
        self.components: List[Component] = []
        self._load_or_create_database()
    
    def _load_or_create_database(self):
        """Load existing database or create default components."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    self.components = [Component(**comp) for comp in data]
            except Exception as e:
                print(f"Error loading component database: {e}")
                self._create_default_database()
        else:
            self._create_default_database()
    
    def _create_default_database(self):
        """Create default component database with common components."""
        default_components = [
            # Microcontrollers
            Component(
                name="Arduino Uno R3",
                category="Microcontroller",
                manufacturer="Arduino",
                part_number="A000066",
                description="8-bit AVR microcontroller board",
                package="DIP-28",
                voltage_rating="5V",
                current_rating="50mA",
                footprint="Arduino_Uno_R3",
                datasheet_url="https://docs.arduino.cc/hardware/uno-rev3",
                price_usd=25.50,
                availability="Available"
            ),
            Component(
                name="STM32F405RGT6",
                category="Microcontroller",
                manufacturer="STMicroelectronics",
                part_number="STM32F405RGT6",
                description="32-bit ARM Cortex-M4 MCU",
                package="LQFP-64",
                voltage_rating="3.3V",
                current_rating="150mA",
                footprint="LQFP-64_10x10mm_P0.5mm",
                datasheet_url="https://www.st.com/resource/en/datasheet/stm32f405rg.pdf",
                price_usd=8.45,
                availability="Available"
            ),
            
            # Resistors
            Component(
                name="Resistor 1kΩ",
                category="Resistor",
                manufacturer="Yageo",
                part_number="RC0805FR-071KL",
                description="Thick film resistor",
                package="0805",
                voltage_rating="150V",
                power_rating="0.125W",
                tolerance="1%",
                value="1kΩ",
                footprint="Resistor_SMD:R_0805_2012Metric",
                price_usd=0.02,
                availability="Available"
            ),
            Component(
                name="Resistor 10kΩ",
                category="Resistor", 
                manufacturer="Yageo",
                part_number="RC0805FR-0710KL",
                description="Thick film resistor",
                package="0805",
                voltage_rating="150V",
                power_rating="0.125W",
                tolerance="1%",
                value="10kΩ",
                footprint="Resistor_SMD:R_0805_2012Metric",
                price_usd=0.02,
                availability="Available"
            ),
            
            # Capacitors
            Component(
                name="Capacitor 100nF",
                category="Capacitor",
                manufacturer="Murata",
                part_number="GRM21BR71C104KA01L",
                description="Ceramic capacitor",
                package="0805",
                voltage_rating="16V",
                tolerance="10%",
                value="100nF",
                footprint="Capacitor_SMD:C_0805_2012Metric",
                price_usd=0.05,
                availability="Available"
            ),
            Component(
                name="Capacitor 10µF",
                category="Capacitor",
                manufacturer="Samsung",
                part_number="CL21A106KAYNNNE",
                description="Ceramic capacitor",
                package="0805",
                voltage_rating="25V",
                tolerance="10%",
                value="10µF",
                footprint="Capacitor_SMD:C_0805_2012Metric",
                price_usd=0.12,
                availability="Available"
            ),
            
            # LEDs
            Component(
                name="LED Red 5mm",
                category="LED",
                manufacturer="Kingbright",
                part_number="WP7113ID",
                description="Red LED indicator",
                package="5mm",
                voltage_rating="2.0V",
                current_rating="20mA",
                footprint="LED_THT:LED_D5.0mm",
                price_usd=0.15,
                availability="Available"
            ),
            
            # Connectors
            Component(
                name="USB-C Connector",
                category="Connector",
                manufacturer="JAE",
                part_number="DX07S024WJ1R1500",
                description="USB Type-C receptacle",
                package="SMD",
                voltage_rating="20V",
                current_rating="3A",
                footprint="Connector_USB:USB_C_Receptacle_JAE_DX07S024WJ1R1500",
                price_usd=1.25,
                availability="Available"
            ),
            
            # Power Management
            Component(
                name="LDO Regulator 3.3V",
                category="Power Management",
                manufacturer="Texas Instruments",
                part_number="TPS73233DBVR",
                description="Low-dropout linear regulator",
                package="SOT-23-5",
                voltage_rating="5.5V",
                current_rating="250mA",
                footprint="Package_TO_SOT_SMD:SOT-23-5",
                price_usd=0.85,
                availability="Available"
            ),
            
            # Sensors
            Component(
                name="Temperature Sensor",
                category="Sensor",
                manufacturer="Texas Instruments",
                part_number="TMP36GT9Z",
                description="Analog temperature sensor",
                package="TO-92",
                voltage_rating="5.5V",
                current_rating="50µA",
                footprint="Package_TO_SOT_THT:TO-92_Inline",
                price_usd=1.50,
                availability="Available"
            ),
        ]
        
        self.components = default_components
        self.save_database()
    
    def save_database(self):
        """Save component database to file."""
        try:
            with open(self.db_path, 'w') as f:
                json.dump([comp.to_dict() for comp in self.components], f, indent=2)
        except Exception as e:
            print(f"Error saving component database: {e}")
    
    def search_components(self, query: str, category: Optional[str] = None) -> List[Component]:
        """Search components by name, description, or part number."""
        query = query.lower()
        results = []
        
        for component in self.components:
            # Search in multiple fields
            searchable_text = " ".join([
                component.name.lower(),
                component.description.lower(),
                component.part_number.lower(),
                component.category.lower(),
                component.manufacturer.lower(),
                component.value or "",
            ])
            
            # Category filter
            if category and component.category.lower() != category.lower():
                continue
            
            # Text search
            if query in searchable_text:
                results.append(component)
        
        return results
    
    def get_components_by_category(self, category: str) -> List[Component]:
        """Get all components in a specific category."""
        return [comp for comp in self.components if comp.category.lower() == category.lower()]
    
    def get_component_by_part_number(self, part_number: str) -> Optional[Component]:
        """Get component by exact part number match."""
        for component in self.components:
            if component.part_number == part_number:
                return component
        return None
    
    def add_component(self, component: Component):
        """Add a new component to the database."""
        self.components.append(component)
        self.save_database()
    
    def get_all_categories(self) -> List[str]:
        """Get all unique component categories."""
        categories = set(comp.category for comp in self.components)
        return sorted(list(categories))
    
    def suggest_components_for_circuit(self, requirements: str) -> List[Component]:
        """Suggest components based on circuit requirements."""
        suggestions = []
        requirements_lower = requirements.lower()
        
        # Define component suggestions based on keywords
        if any(word in requirements_lower for word in ["arduino", "microcontroller", "mcu"]):
            suggestions.extend(self.get_components_by_category("Microcontroller"))
        
        if any(word in requirements_lower for word in ["led", "light", "indicator"]):
            suggestions.extend(self.get_components_by_category("LED"))
        
        if any(word in requirements_lower for word in ["resistor", "resistance", "current limit"]):
            suggestions.extend(self.get_components_by_category("Resistor"))
        
        if any(word in requirements_lower for word in ["capacitor", "decoupling", "filter"]):
            suggestions.extend(self.get_components_by_category("Capacitor"))
        
        if any(word in requirements_lower for word in ["usb", "connector", "interface"]):
            suggestions.extend(self.get_components_by_category("Connector"))
        
        if any(word in requirements_lower for word in ["power", "regulator", "voltage"]):
            suggestions.extend(self.get_components_by_category("Power Management"))
        
        if any(word in requirements_lower for word in ["sensor", "temperature", "measurement"]):
            suggestions.extend(self.get_components_by_category("Sensor"))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for comp in suggestions:
            if comp.part_number not in seen:
                seen.add(comp.part_number)
                unique_suggestions.append(comp)
        
        return unique_suggestions[:10]  # Return top 10 suggestions


# Global component database instance
_component_db = None

def get_component_database(db_path: Optional[str] = None) -> ComponentDatabase:
    """Get global component database instance."""
    global _component_db
    if _component_db is None:
        _component_db = ComponentDatabase(db_path)
    return _component_db