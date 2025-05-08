#!/usr/bin/env python3
"""
Main entry point for the PCB Design Agent System.
Integrates all components of the system into a complete workflow.
"""

import os
import sys
import argparse
import time
import logging
from typing import Dict, List, Any, Optional
import json

# Import LangChain and LangGraph components
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END

# Import our modules
import component_database as cdb
import schematic_generator as sg
import pcb_layout_engine as ple
import design_simulator as ds
import manufacturing_output as mo
import kicad_helpers as kh

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pcb_design_system.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("PCBDesignSystem")

class PCBDesignSystem:
    """Main PCB design system that integrates all components."""
    
    def __init__(self, api_key: Optional[str] = None, output_dir: str = "output"):
        """
        Initialize the PCB design system.
        
        Args:
            api_key: Anthropic API key (optional, will use environment variable if not provided)
            output_dir: Directory for output files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize LLM
        self.llm = self._initialize_llm(api_key)
        
        # Initialize component database
        self.component_db = cdb.create_sample_database()
        
        # Initialize other sub-systems
        self.schematic_generator = sg.SchematicGenerator(output_dir=output_dir)
        self.layout_engine = ple.PCBLayoutEngine()
        self.simulator = ds.DesignSimulator()
        self.manufacturing_generator = mo.ManufacturingOutputGenerator(output_dir=output_dir)
        
        # State tracking
        self.user_requirements = ""
        self.component_selections = {}
        self.schematic_file = ""
        self.pcb_file = ""
        self.manufacturing_files = []
        self.workflow_complete = False
    
    def _initialize_llm(self, api_key: Optional[str] = None) -> Any:
        """
        Initialize the language model.
        
        Args:
            api_key: Anthropic API key
        
        Returns:
            Initialized LLM
        """
        # If API key is provided, use it
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        
        # Try to initialize Claude
        try:
            llm = ChatAnthropic(model="claude-3-sonnet-20240229")
            return llm
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            logger.error("Falling back to stub LLM for demonstration")
            
            # Create a stub LLM for demonstration
            class StubLLM:
                def invoke(self, messages):
                    return {"content": "This is a stub LLM response for demonstration purposes."}
            
            return StubLLM()
    
    def process_requirements(self, requirements: str) -> Dict[str, Any]:
        """
        Process user requirements and extract structured data.
        
        Args:
            requirements: User requirements as text
        
        Returns:
            Dictionary with structured requirements
        """
        logger.info("Processing user requirements")
        
        # Store requirements
        self.user_requirements = requirements
        
        # Create prompt for requirements analysis
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are a PCB design analyzer that extracts structured requirements from text. "
                "Identify the following aspects from the user's PCB design requirements:\n"
                "1. Main purpose of the circuit\n"
                "2. Key components needed\n"
                "3. Power requirements\n"
                "4. Size constraints\n"
                "5. Environmental requirements\n"
                "6. Performance requirements\n"
                "7. Special requirements (RF, high-speed, etc.)"
            )),
            HumanMessage(content=requirements)
        ])
        
        # Extract structured data from requirements
        output_parser = JsonOutputParser()
        
        chain = prompt | self.llm | output_parser
        
        try:
            # Try to parse requirements as structured data
            result = chain.invoke({})
            
            logger.info(f"Requirements processed: {result.keys()}")
            return result
        except Exception as e:
            logger.error(f"Error processing requirements: {e}")
            
            # Return basic structure if parsing fails
            return {
                "main_purpose": "Unknown",
                "components": [],
                "power_requirements": "Unknown",
                "size_constraints": "Unknown",
                "environmental_requirements": "Unknown",
                "performance_requirements": "Unknown",
                "special_requirements": "Unknown"
            }
    
    def select_components(self, requirements: Dict[str, Any]) -> Dict[str, List[cdb.Component]]:
        """
        Select components based on requirements.
        
        Args:
            requirements: Structured requirements
        
        Returns:
            Dictionary of selected components by category
        """
        logger.info("Selecting components based on requirements")
        
        # Extract components list from requirements
        components_needed = []
        if "components" in requirements and isinstance(requirements["components"], list):
            components_needed = requirements["components"]
        
        # If components list is empty, extract from main text
        if not components_needed and self.user_requirements:
            # Create prompt to extract component list
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=(
                    "Extract a list of electronic components needed for the following PCB design. "
                    "Return the result as a JSON array of strings."
                )),
                HumanMessage(content=self.user_requirements)
            ])
            
            output_parser = JsonOutputParser()
            chain = prompt | self.llm | output_parser
            
            try:
                components_needed = chain.invoke({})
                if not isinstance(components_needed, list):
                    components_needed = []
            except Exception as e:
                logger.error(f"Error extracting components: {e}")
                components_needed = []
        
        # Search for each component in the database
        selected_components = {}
        
        for component_name in components_needed:
            # Search the component database
            components = self.component_db.search_components(component_name, n_results=3)
            
            if components:
                category = components[0].type
                if category not in selected_components:
                    selected_components[category] = []
                
                selected_components[category].extend(components)
        
        # If no components found, add some defaults for demonstration
        if not selected_components:
            # Add a microcontroller
            microcontroller = self.component_db.search_components("microcontroller", n_results=1)
            if microcontroller:
                selected_components["microcontroller"] = microcontroller
            
            # Add some basic components
            resistors = self.component_db.search_components("resistor", n_results=2)
            if resistors:
                selected_components["resistor"] = resistors
            
            capacitors = self.component_db.search_components("capacitor", n_results=2)
            if capacitors:
                selected_components["capacitor"] = capacitors
        
        # Store component selections
        self.component_selections = selected_components
        
        logger.info(f"Selected {sum(len(components) for components in selected_components.values())} components "
                   f"in {len(selected_components)} categories")
        
        return selected_components
    
    def create_schematic(self, components: Dict[str, List[cdb.Component]]) -> str:
        """
        Create a schematic using selected components.
        
        Args:
            components: Dictionary of selected components by category
        
        Returns:
            Path to the created schematic file
        """
        logger.info("Creating schematic")
        
        # Create a new schematic generator
        self.schematic_generator = sg.SchematicGenerator(output_dir=self.output_dir)
        
        # Determine if this is an Arduino shield from requirements
        is_arduino_shield = False
        if "arduino" in self.user_requirements.lower() and "shield" in self.user_requirements.lower():
            is_arduino_shield = True
            logger.info("Detected Arduino shield requirements")
        
        # If it's an Arduino shield, use the shield template
        if is_arduino_shield:
            self.schematic_generator.create_arduino_shield_template()
        
        # Add components to the schematic
        for category, component_list in components.items():
            for component in component_list:
                # Add the component to the schematic
                symbol = self.schematic_generator.add_component(
                    component_type=category,
                    value=component.name,
                    footprint=component.footprint,
                    properties={"Manufacturer": component.manufacturer, 
                               "PartNumber": component.part_number}
                )
        
        # For the demonstration, add some basic connections
        # In a real implementation, this would analyze the requirements and create appropriate connections
        
        # Connect power and ground
        for i, component in enumerate(self.schematic_generator.symbols):
            if i > 0 and "VCC" not in component.reference:
                # Connect to power for components that might need it
                self.schematic_generator.add_power_net(component.reference, "1", "VCC")
            
            if i > 0 and "GND" not in component.reference:
                # Connect to ground for components that might need it
                self.schematic_generator.add_power_net(component.reference, "2", "GND")
        
        # Generate schematic file
        schematic_filename = "pcb_design"
        success = self.schematic_generator.generate_schematic(schematic_filename)
        
        if success:
            self.schematic_file = os.path.join(self.output_dir, f"{schematic_filename}.kicad_sch")
            logger.info(f"Schematic created: {self.schematic_file}")
        else:
            logger.error("Failed to create schematic")
        
        return self.schematic_file
    
    def create_pcb_layout(self, schematic_file: str) -> str:
        """
        Create a PCB layout from the schematic.
        
        Args:
            schematic_file: Path to the schematic file
        
        Returns:
            Path to the created PCB file
        """
        logger.info("Creating PCB layout")
        
        # Create a new PCB layout engine
        self.layout_engine = ple.PCBLayoutEngine()
        
        # Set board outline based on requirements
        # In a real implementation, this would analyze the size constraints from requirements
        # For demonstration, we'll use a default size
        self.layout_engine.set_board_outline(100.0, 80.0)  # 100x80mm board
        
        # Add components from the schematic
        if self.schematic_generator and self.schematic_generator.symbols:
            for symbol in self.schematic_generator.symbols:
                # Add the component to the layout
                component = ple.ComponentPlacement(
                    component_id=f"{symbol.reference}_{symbol.value}",
                    reference=symbol.reference,
                    footprint_name=symbol.footprint.split(':')[-1] if ':' in symbol.footprint else symbol.footprint,
                    position=(0, 0),  # Initial position will be updated by auto-placement
                    rotation=0.0,
                    layer="top"
                )
                
                self.layout_engine.add_component(component)
        else:
            # If no schematic, add some demo components
            logger.info("No schematic available, adding demo components")
            
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
                    component_id="C1_100n",
                    reference="C1",
                    footprint_name="C_0805_2012Metric",
                    position=(60.0, 30.0),
                    rotation=90.0,
                    layer="top"
                )
            ]
            
            for component in components:
                self.layout_engine.add_component(component)
        
        # Create nets from schematic connections
        if self.schematic_generator and self.schematic_generator.wires:
            # In a real implementation, this would trace the actual nets from the schematic
            # For demonstration, we'll create some basic nets
            
            # Find components for demonstration nets
            components = {}
            for component in self.layout_engine.components:
                components[component.reference] = component
            
            # Create some example nets
            nets = []
            
            for ref1, component1 in components.items():
                for ref2, component2 in components.items():
                    if ref1 != ref2 and ref1 < ref2:  # Avoid duplicates
                        # Create a connection between these components
                        net = ple.NetConnection(
                            net_name=f"Net_{ref1}_{ref2}",
                            source_component=ref1,
                            source_pad="1",
                            target_component=ref2,
                            target_pad="1"
                        )
                        
                        nets.append(net)
                        
                        # Limit to a reasonable number of nets for demonstration
                        if len(nets) >= 5:
                            break
                
                if len(nets) >= 5:
                    break
            
            self.layout_engine.nets = nets
        
        # Auto-place components
        logger.info("Auto-placing components")
        self.layout_engine.auto_place_components()
        
        # Auto-route connections
        logger.info("Auto-routing nets")
        self.layout_engine.auto_route_all_nets()
        
        # Add ground plane
        logger.info("Adding ground plane")
        self.layout_engine.add_ground_plane()
        
        # Export to KiCad if available
        pcb_filename = os.path.join(self.output_dir, "pcb_design.kicad_pcb")
        
        if kh.KICAD_AVAILABLE:
            logger.info("Exporting to KiCad PCB file")
            success = self.layout_engine.export_to_kicad(pcb_filename)
            
            if success:
                self.pcb_file = pcb_filename
                logger.info(f"PCB layout created: {self.pcb_file}")
            else:
                logger.error("Failed to export to KiCad PCB file")
        else:
            # Create a dummy PCB file for demonstration
            with open(pcb_filename, 'w') as f:
                f.write("(kicad_pcb (version 20211014) (generator pcbnew)\n")
                f.write("  (general\n")
                f.write("    (thickness 1.6)\n")
                f.write("  )\n")
                f.write(")\n")
            
            self.pcb_file = pcb_filename
            logger.info(f"Simulated PCB layout created: {self.pcb_file}")
        
        return self.pcb_file
    
    def run_simulations(self, pcb_file: str) -> ds.SimulationResults:
        """
        Run simulations on the PCB layout.
        
        Args:
            pcb_file: Path to the PCB file
        
        Returns:
            Simulation results
        """
        logger.info("Running simulations")
        
        # Set up simulator with our layout engine
        self.simulator = ds.DesignSimulator(self.layout_engine)
        
        # Run all simulations
        results = self.simulator.run_all_simulations()
        
        # Export simulation report
        report_file = os.path.join(self.output_dir, "simulation_report.html")
        self.simulator.export_report(report_file)
        
        logger.info(f"Simulation report generated: {report_file}")
        logger.info(results.summary())
        
        return results
    
    def generate_manufacturing_files(self, pcb_file: str) -> List[str]:
        """
        Generate manufacturing files from the PCB layout.
        
        Args:
            pcb_file: Path to the PCB file
        
        Returns:
            List of generated file paths
        """
        logger.info("Generating manufacturing files")
        
        # Set up manufacturing generator with our layout engine
        self.manufacturing_generator = mo.ManufacturingOutputGenerator(output_dir=self.output_dir)
        self.manufacturing_generator.set_layout_engine(self.layout_engine)
        
        # Generate complete manufacturing package
        package_file = self.manufacturing_generator.generate_manufacturing_package(include_source_files=True)
        
        if package_file:
            self.manufacturing_files.append(package_file)
            logger.info(f"Manufacturing package generated: {package_file}")
        else:
            logger.error("Failed to generate manufacturing package")
            
            # Generate individual files as fallback
            gerber_files = self.manufacturing_generator.generate_gerber_files()
            self.manufacturing_files.extend(gerber_files)
            
            bom_file = self.manufacturing_generator.generate_bom("csv")
            if bom_file:
                self.manufacturing_files.append(bom_file)
            
            pnp_file = self.manufacturing_generator.generate_pick_and_place("csv")
            if pnp_file:
                self.manufacturing_files.append(pnp_file)
        
        return self.manufacturing_files
    
    def generate_documentation(self) -> List[str]:
        """
        Generate documentation for the PCB design.
        
        Returns:
            List of generated file paths
        """
        logger.info("Generating documentation")
        
        documentation_files = []
        
        # Generate assembly drawings
        assembly_files = self.manufacturing_generator.generate_assembly_drawings()
        documentation_files.extend(assembly_files)
        
        # Generate fabrication notes
        fab_notes = self.manufacturing_generator.generate_fabrication_notes()
        if fab_notes:
            documentation_files.append(fab_notes)
        
        # Generate summary report
        summary_file = os.path.join(self.output_dir, "design_summary.txt")
        
        try:
            with open(summary_file, 'w') as f:
                f.write("PCB Design Summary\n")
                f.write("=================\n\n")
                f.write(f"Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("User Requirements:\n")
                f.write("-----------------\n")
                f.write(self.user_requirements)
                f.write("\n\n")
                
                f.write("Selected Components:\n")
                f.write("-------------------\n")
                for category, components in self.component_selections.items():
                    f.write(f"{category}:\n")
                    for component in components:
                        f.write(f"- {component.name} ({component.manufacturer} {component.part_number})\n")
                f.write("\n")
                
                f.write("Generated Files:\n")
                f.write("---------------\n")
                if self.schematic_file:
                    f.write(f"Schematic: {os.path.basename(self.schematic_file)}\n")
                if self.pcb_file:
                    f.write(f"PCB Layout: {os.path.basename(self.pcb_file)}\n")
                for file_path in self.manufacturing_files:
                    f.write(f"Manufacturing: {os.path.basename(file_path)}\n")
                
                f.write("\n")
                
                # Include simulation results if available
                if hasattr(self, "simulator") and hasattr(self.simulator, "results"):
                    f.write("Simulation Results:\n")
                    f.write("------------------\n")
                    f.write(self.simulator.results.summary())
                    f.write("\n\n")
            
            documentation_files.append(summary_file)
            logger.info(f"Design summary generated: {summary_file}")
        
        except Exception as e:
            logger.error(f"Error generating design summary: {e}")
        
        return documentation_files
    
    def run_complete_workflow(self, requirements: str) -> Dict[str, Any]:
        """
        Run the complete PCB design workflow from requirements to manufacturing files.
        
        Args:
            requirements: User requirements as text
        
        Returns:
            Dictionary with results and file paths
        """
        logger.info("Starting complete PCB design workflow")
        
        # Process requirements
        structured_requirements = self.process_requirements(requirements)
        
        # Select components
        selected_components = self.select_components(structured_requirements)
        
        # Create schematic
        schematic_file = self.create_schematic(selected_components)
        
        # Create PCB layout
        pcb_file = self.create_pcb_layout(schematic_file)
        
        # Run simulations
        simulation_results = self.run_simulations(pcb_file)
        
        # Generate manufacturing files
        manufacturing_files = self.generate_manufacturing_files(pcb_file)
        
        # Generate documentation
        documentation_files = self.generate_documentation()
        
        # Mark workflow as complete
        self.workflow_complete = True
        
        # Return results
        results = {
            "requirements": structured_requirements,
            "schematic_file": schematic_file,
            "pcb_file": pcb_file,
            "manufacturing_files": manufacturing_files,
            "documentation_files": documentation_files,
            "simulation_summary": simulation_results.summary()
        }
        
        logger.info("PCB design workflow completed successfully")
        
        return results
    
    def explain_design(self) -> str:
        """
        Generate an explanation of the design choices.
        
        Returns:
            Explanation text
        """
        # Create prompt for design explanation
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are a PCB design expert. Explain the design choices made for this PCB based on the "
                "user's requirements. Focus on component selection, layout considerations, and key design decisions."
            )),
            HumanMessage(content=(
                f"Requirements: {self.user_requirements}\n\n"
                f"Selected components: {json.dumps([c.to_dict() for components in self.component_selections.values() for c in components])}"
            ))
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            explanation = chain.invoke({})
            return explanation
        except Exception as e:
            logger.error(f"Error generating design explanation: {e}")
            return "Could not generate design explanation due to an error."

def main():
    """Main entry point for the PCB design system."""
    parser = argparse.ArgumentParser(description="PCB Design Agent System")
    parser.add_argument("--requirements", "-r", help="Path to requirements text file")
    parser.add_argument("--requirements-text", "-t", help="Requirements as text")
    parser.add_argument("--output-dir", "-o", default="output", help="Output directory for generated files")
    parser.add_argument("--api-key", "-k", help="Anthropic API key (optional, defaults to environment variable)")
    parser.add_argument("--explain", "-e", action="store_true", help="Generate design explanation")
    
    args = parser.parse_args()
    
    # Get requirements
    requirements = ""
    
    if args.requirements_text:
        requirements = args.requirements_text
    elif args.requirements:
        try:
            with open(args.requirements, 'r') as f:
                requirements = f.read()
        except Exception as e:
            print(f"Error reading requirements file: {e}")
            return 1
    else:
        # Example requirements
        requirements = """
        I need a PCB for a temperature monitoring system with the following features:
        1. Arduino-compatible microcontroller (ATmega328P)
        2. Two DS18B20 temperature sensor inputs
        3. OLED display (128x64, I2C interface)
        4. Status LED
        5. Power from USB or external 9V power supply
        6. Reset button
        7. Mounting holes for enclosure
        8. Maximum board size: 100mm x 80mm
        """
    
    # Create PCB design system
    design_system = PCBDesignSystem(api_key=args.api_key, output_dir=args.output_dir)
    
    # Run complete workflow
    results = design_system.run_complete_workflow(requirements)
    
    # Print summary
    print("\nPCB Design Workflow Completed")
    print("===========================")
    print(f"Schematic: {os.path.basename(results['schematic_file'])}")
    print(f"PCB Layout: {os.path.basename(results['pcb_file'])}")
    print("Manufacturing Files:")
    for file_path in results['manufacturing_files']:
        print(f"- {os.path.basename(file_path)}")
    print("Documentation Files:")
    for file_path in results['documentation_files']:
        print(f"- {os.path.basename(file_path)}")
    print("\nSimulation Summary:")
    print(results["simulation_summary"])
    
    # Generate explanation if requested
    if args.explain:
        explanation = design_system.explain_design()
        print("\nDesign Explanation:")
        print("==================")
        print(explanation)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())