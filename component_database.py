#!/usr/bin/env python3
"""
Component database module for the PCB design agent.
Handles component search, selection, and retrieval of datasheets.
"""

import os
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
import chromadb
from chromadb.utils import embedding_functions
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

# Define component dataclass
@dataclass
class Component:
    """Class representing an electronic component."""
    
    # Basic identification
    id: str
    name: str
    description: str
    type: str  # resistor, capacitor, IC, etc.
    manufacturer: str
    part_number: str
    
    # Technical specifications as a dictionary
    specs: Dict[str, Any] = field(default_factory=dict)
    
    # Physical properties
    package: str = ""
    footprint: str = ""
    
    # Sourcing information
    suppliers: List[Dict[str, str]] = field(default_factory=list)
    availability: bool = True
    price: float = 0.0
    price_currency: str = "USD"
    
    # Documentation
    datasheet_url: str = ""
    image_url: str = ""
    
    # PCB design specific
    pins: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Component':
        """Create from dictionary."""
        return cls(**data)
    
    def get_embedding_text(self) -> str:
        """Get text for embedding."""
        return f"{self.name} {self.description} {self.type} {self.manufacturer} {self.part_number} {' '.join(self.tags)}"

# Define embeddings function (uses ChromaDB's default if no model provided)
class ComponentEmbeddings:
    """Embeddings for component database."""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize embeddings."""
        if model_name:
            # Use specified model
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
        else:
            # Use default
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents."""
        return self.embedding_function(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed query."""
        return self.embedding_function([text])[0]

class ComponentDatabase:
    """Database for electronic components with vector search capabilities."""
    
    def __init__(self, db_path: str = "component_db", embedding_model: Optional[str] = None):
        """Initialize component database."""
        self.db_path = db_path
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Create embedding function
        ef = embedding_functions.DefaultEmbeddingFunction()
        if embedding_model:
            try:
                ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=embedding_model)
            except Exception as e:
                print(f"Failed to load embedding model {embedding_model}: {e}")
                print("Falling back to default embedding function")
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="components",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Local cache for components
        self.components: Dict[str, Component] = {}
    
    def add_component(self, component: Component) -> bool:
        """
        Add component to database.
        
        Args:
            component: Component to add
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add to vector database
            self.collection.add(
                ids=[component.id],
                documents=[component.get_embedding_text()],
                metadatas=[component.to_dict()]
            )
            
            # Add to local cache
            self.components[component.id] = component
            
            return True
        except Exception as e:
            print(f"Error adding component to database: {e}")
            return False
    
    def add_components(self, components: List[Component]) -> int:
        """
        Add multiple components to database.
        
        Args:
            components: List of components to add
        
        Returns:
            Number of components successfully added
        """
        try:
            # Prepare data for batch insertion
            ids = []
            documents = []
            metadatas = []
            
            for component in components:
                ids.append(component.id)
                documents.append(component.get_embedding_text())
                metadatas.append(component.to_dict())
                
                # Add to local cache
                self.components[component.id] = component
            
            # Add to vector database
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            return len(components)
        except Exception as e:
            print(f"Error adding components to database: {e}")
            return 0
    
    def search_components(self, query: str, n_results: int = 10, 
                          filter_dict: Optional[Dict[str, Any]] = None) -> List[Component]:
        """
        Search for components using vector similarity.
        
        Args:
            query: Search query
            n_results: Maximum number of results to return
            filter_dict: Optional dictionary of filters to apply
        
        Returns:
            List of matching components
        """
        try:
            # Perform search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_dict
            )
            
            # Convert results to components
            components = []
            if results["metadatas"]:
                for metadata in results["metadatas"][0]:
                    component = Component.from_dict(metadata)
                    components.append(component)
            
            return components
        except Exception as e:
            print(f"Error searching components: {e}")
            return []
    
    def get_component(self, component_id: str) -> Optional[Component]:
        """
        Get component by ID.
        
        Args:
            component_id: Component ID
        
        Returns:
            Component if found, None otherwise
        """
        # Check local cache first
        if component_id in self.components:
            return self.components[component_id]
        
        # Try to get from database
        try:
            result = self.collection.get(ids=[component_id])
            
            if result["metadatas"] and len(result["metadatas"]) > 0:
                component = Component.from_dict(result["metadatas"][0])
                self.components[component_id] = component
                return component
            
            return None
        except Exception as e:
            print(f"Error getting component {component_id}: {e}")
            return None
    
    def update_component(self, component: Component) -> bool:
        """
        Update existing component.
        
        Args:
            component: Component with updated values
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update in vector database
            self.collection.update(
                ids=[component.id],
                documents=[component.get_embedding_text()],
                metadatas=[component.to_dict()]
            )
            
            # Update local cache
            self.components[component.id] = component
            
            return True
        except Exception as e:
            print(f"Error updating component {component.id}: {e}")
            return False
    
    def delete_component(self, component_id: str) -> bool:
        """
        Delete component from database.
        
        Args:
            component_id: ID of component to delete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from vector database
            self.collection.delete(ids=[component_id])
            
            # Remove from local cache
            if component_id in self.components:
                del self.components[component_id]
            
            return True
        except Exception as e:
            print(f"Error deleting component {component_id}: {e}")
            return False
    
    def load_from_json(self, json_file: str) -> int:
        """
        Load components from JSON file.
        
        Args:
            json_file: Path to JSON file
        
        Returns:
            Number of components loaded
        """
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            components = []
            for item in data:
                try:
                    component = Component.from_dict(item)
                    components.append(component)
                except Exception as e:
                    print(f"Error parsing component: {e}")
            
            # Add components to database
            return self.add_components(components)
        except Exception as e:
            print(f"Error loading components from {json_file}: {e}")
            return 0
    
    def export_to_json(self, json_file: str) -> bool:
        """
        Export components to JSON file.
        
        Args:
            json_file: Path to JSON file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all components
            result = self.collection.get()
            
            components = []
            if result["metadatas"]:
                for metadata in result["metadatas"]:
                    components.append(metadata)
            
            # Write to file
            with open(json_file, 'w') as f:
                json.dump(components, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error exporting components to {json_file}: {e}")
            return False
    
    def get_component_count(self) -> int:
        """Get the number of components in the database."""
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Error getting component count: {e}")
            return 0
    
    def find_similar_components(self, component_id: str, n_results: int = 5) -> List[Component]:
        """
        Find similar components to a given component.
        
        Args:
            component_id: Component ID
            n_results: Maximum number of results to return
        
        Returns:
            List of similar components
        """
        # Get the component first
        component = self.get_component(component_id)
        if not component:
            return []
        
        # Search for similar components
        return self.search_components(
            query=component.get_embedding_text(),
            n_results=n_results + 1  # Add 1 because the component itself will be included
        )[1:]  # Exclude the first result (the component itself)

# Sample data management function
def create_sample_database(db_path: str = "component_db", load_sample_data: bool = True) -> ComponentDatabase:
    """
    Create a sample component database with some common components.
    
    Args:
        db_path: Path to store the database
        load_sample_data: Whether to load sample data
    
    Returns:
        Initialized component database
    """
    # Create database
    db = ComponentDatabase(db_path=db_path)
    
    if not load_sample_data:
        return db
    
    # Create some sample components
    components = [
        Component(
            id="res-0001",
            name="0.25W Resistor",
            description="General purpose 0.25W resistor",
            type="resistor",
            manufacturer="Various",
            part_number="Generic",
            specs={
                "resistance": 10000,  # 10k
                "tolerance": 0.05,    # 5%
                "power_rating": 0.25, # 0.25W
            },
            package="0805",
            footprint="Resistor_SMD:R_0805_2012Metric",
            tags=["resistor", "passive", "SMD", "0805"],
        ),
        Component(
            id="cap-0001",
            name="Ceramic Capacitor",
            description="General purpose ceramic capacitor",
            type="capacitor",
            manufacturer="Various",
            part_number="Generic",
            specs={
                "capacitance": 0.0000001, # 0.1uF
                "voltage_rating": 50,     # 50V
                "tolerance": 0.1,         # 10%
                "type": "X7R"
            },
            package="0805",
            footprint="Capacitor_SMD:C_0805_2012Metric",
            tags=["capacitor", "passive", "SMD", "0805", "ceramic"],
        ),
        Component(
            id="ic-0001",
            name="ATmega328P",
            description="8-bit microcontroller",
            type="microcontroller",
            manufacturer="Microchip",
            part_number="ATmega328P-AU",
            specs={
                "architecture": "AVR",
                "flash": 32768,          # 32KB
                "ram": 2048,             # 2KB
                "eeprom": 1024,          # 1KB
                "max_frequency": 20000000, # 20MHz
                "io_pins": 23,
                "adc_channels": 8
            },
            package="TQFP-32",
            footprint="Package_QFP:TQFP-32_7x7mm_P0.8mm",
            datasheet_url="https://ww1.microchip.com/downloads/en/DeviceDoc/ATmega48A-PA-88A-PA-168A-PA-328-P-DS-DS40002061A.pdf",
            tags=["microcontroller", "AVR", "Microchip", "Arduino"],
        ),
        Component(
            id="ic-0002",
            name="LM7805",
            description="5V linear voltage regulator",
            type="voltage_regulator",
            manufacturer="Texas Instruments",
            part_number="LM7805",
            specs={
                "output_voltage": 5.0,    # 5V
                "input_voltage_min": 7.0,  # 7V
                "input_voltage_max": 35.0, # 35V
                "output_current_max": 1.0, # 1A
                "dropout_voltage": 2.0,    # 2V
            },
            package="TO-220",
            footprint="Package_TO_SOT_THT:TO-220-3_Vertical",
            datasheet_url="https://www.ti.com/lit/ds/symlink/lm7805.pdf",
            tags=["voltage regulator", "linear", "5V", "power"],
        ),
        Component(
            id="ic-0003",
            name="DS18B20",
            description="1-Wire digital temperature sensor",
            type="temperature_sensor",
            manufacturer="Maxim Integrated",
            part_number="DS18B20",
            specs={
                "temperature_range_min": -55,   # -55°C
                "temperature_range_max": 125,   # 125°C
                "accuracy": 0.5,                # ±0.5°C
                "resolution": 0.0625,           # 0.0625°C
                "interface": "1-Wire"
            },
            package="TO-92",
            footprint="Package_TO_SOT_THT:TO-92_Inline",
            datasheet_url="https://datasheets.maximintegrated.com/en/ds/DS18B20.pdf",
            tags=["temperature", "sensor", "1-Wire", "digital"],
        ),
        Component(
            id="disp-0001",
            name="SSD1306 OLED Display",
            description="128x64 OLED display with SSD1306 controller",
            type="display",
            manufacturer="Various",
            part_number="SSD1306",
            specs={
                "resolution_x": 128,
                "resolution_y": 64,
                "interface": "I2C/SPI",
                "controller": "SSD1306",
                "color": "Monochrome",
                "active_area": "0.96 inch"
            },
            package="Custom",
            footprint="Display:OLED_128x64_I2C",
            datasheet_url="https://cdn-shop.adafruit.com/datasheets/SSD1306.pdf",
            tags=["display", "OLED", "I2C", "SPI", "SSD1306"],
        ),
    ]
    
    # Add to database
    db.add_components(components)
    
    print(f"Created sample database with {len(components)} components")
    return db

# Utility function to search for components by requirements
def find_components_for_requirements(db: ComponentDatabase, requirements: str) -> Dict[str, List[Component]]:
    """
    Find components matching given requirements.
    
    Args:
        db: Component database
        requirements: Natural language requirements
    
    Returns:
        Dictionary of component types to lists of matching components
    """
    # This would be enhanced with a more sophisticated component matching logic
    # For now, we'll just do a simple search
    
    # Try to identify component types needed
    component_types = ["resistor", "capacitor", "microcontroller", "voltage regulator", 
                       "temperature sensor", "display", "LED", "transistor", "diode"]
    
    results = {}
    for component_type in component_types:
        if component_type.lower() in requirements.lower():
            components = db.search_components(
                query=component_type,
                n_results=5,
                filter_dict={"type": component_type.replace(" ", "_")}
            )
            
            if components:
                results[component_type] = components
    
    return results


# If run directly, create a sample database
if __name__ == "__main__":
    # Create sample database
    db = create_sample_database()
    
    # Print statistics
    print(f"Component database created with {db.get_component_count()} components")
    
    # Example search
    results = db.search_components("microcontroller", n_results=3)
    print("\nSearch results for 'microcontroller':")
    for component in results:
        print(f"- {component.name}: {component.description} ({component.manufacturer} {component.part_number})")