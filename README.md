# PCB Design Agent

An intelligent agent system that automates PCB design using LangChain/LangGraph and KiCad. This system takes user requirements in natural language, searches for component documentation, designs and routes PCB layouts, performs simulations, and generates manufacturing files.

## Overview

This project creates an AI-powered workflow that:

1. Interprets natural language PCB design requirements
2. Researches and selects appropriate components
3. Creates circuit schematics
4. Designs PCB layouts with proper routing and ground planes
5. Simulates and validates the design
6. Generates manufacturing files (Gerber files, BOM)

## System Components

The PCB Design Agent is composed of several key modules:

- **PCB Design System** (`pcb_design_system.py`): Main entry point that orchestrates the entire workflow
- **Component Database** (`component_database.py`): Manages components and their specifications
- **Schematic Generator** (`schematic_generator.py`): Creates circuit schematics from requirements
- **PCB Layout Engine** (`pcb_layout_engine.py`): Places components and routes traces
- **Design Simulator** (`design_simulator.py`): Performs electrical, thermal, and EMI simulations
- **Manufacturing Output Generator** (`manufacturing_output.py`): Creates Gerber files and other outputs
- **KiCad Helpers** (`kicad_helpers.py`): Utilities for working with the KiCad Python API

## Installation

### Prerequisites

- Python 3.9+
- KiCad 6.0+ installed with Python API available (optional but recommended)
- API key for Claude or another compatible LLM

### Setup

1. Clone this repository
2. Run the setup script to create a virtual environment and install dependencies:

```bash
chmod +x setup.sh
./setup.sh
```

3. Set up environment variables:

```bash
# Create a .env file with your API key
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
```

## Usage

### Basic Usage

Run the PCB design system with command-line requirements:

```bash
source venv/bin/activate
python pcb_design_system.py --requirements-text "I need a temperature monitoring system with two DS18B20 sensors, an OLED display, and a status LED."
```

### Advanced Usage

You can also provide a requirements file:

```bash
python pcb_design_system.py --requirements requirements.txt --output-dir my_design
```

To get a detailed explanation of the design choices:

```bash
python pcb_design_system.py --requirements-text "Your requirements here" --explain
```

For all options:

```bash
python pcb_design_system.py --help
```

### Example Requirements

The system works best with detailed requirements. Here's an example:

```
I need a PCB for a temperature monitoring system with the following features:
1. Arduino-compatible microcontroller (ATmega328P)
2. Two DS18B20 temperature sensor inputs
3. OLED display (128x64, I2C interface)
4. Status LED
5. Power from USB or external 9V power supply
6. Reset button
7. Mounting holes for enclosure
8. Maximum board size: 100mm x 80mm
```

## Output Files

The system generates the following outputs:

- Schematic file (`.kicad_sch`)
- PCB layout file (`.kicad_pcb`)
- Gerber files for manufacturing
- Bill of Materials (BOM) in CSV and HTML formats
- Pick-and-place files for assembly
- Assembly drawings
- Fabrication notes
- Simulation reports
- Design summary

## KiCad Integration

The system interfaces with KiCad through its Python API:

- `pcbnew` module for PCB design
- `eeschema` module for schematic creation (when available)

If KiCad is not installed or its Python API is not available, the system will run in simulation mode, generating placeholder files that demonstrate the workflow.

## Architecture

The system uses a multi-agent approach with specialized components for each step of the PCB design process:

1. **User Interface Processing**: Handles natural language input and requirement analysis
2. **Component Research**: Searches for and selects appropriate components
3. **Schematic Design**: Creates circuit schematics
4. **PCB Layout**: Places components and routes traces
5. **Simulation**: Validates the design against electrical rules
6. **Manufacturing Output**: Generates Gerber files and BOM

See `design_agent_architecture.md` for detailed architecture information.

## Key Features

- **Natural Language Processing**: Interpret PCB design requirements in plain English
- **Component Selection**: Find components matching requirements from a database
- **Automated Schematic Creation**: Generate circuit schematics based on selected components
- **Auto-placement**: Intelligently place components on the PCB
- **Auto-routing**: Generate traces between components with proper clearances
- **Design Rule Checking**: Validate the design against electrical and manufacturing rules
- **Signal Integrity Analysis**: Estimate impedance, delay, and signal quality
- **Thermal Analysis**: Identify potential hotspots and thermal issues
- **Manufacturing Outputs**: Generate industry-standard files for fabrication and assembly

## Technical Highlights

- **Vector Database**: Uses ChromaDB for component search and retrieval
- **Layout Algorithms**: Implements force-directed placement and A* routing algorithms
- **KiCad Integration**: Seamlessly works with KiCad's Python API when available
- **Simulation**: Includes electrical rule checking, signal integrity, power integrity, thermal, and EMI analysis
- **Manufacturing**: Generates complete manufacturing package including Gerber files, drill files, BOM, and assembly documentation

## Limitations

- The current implementation has limited automation for complex routing scenarios
- Component selection relies on a simplified component database
- Not all KiCad features are fully supported
- Simulation models are approximate rather than using industry-standard solvers
- The agent may require human guidance for complex design decisions

## Future Improvements

- Integration with component supplier APIs for real-time availability checking
- Enhanced auto-routing capabilities for high-speed and RF designs
- Support for multi-layer boards with complex stackups
- Integration with advanced simulation tools
- Web interface for design visualization
- Collaborative design with multiple agents specializing in different domains

## License

MIT