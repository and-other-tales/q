# Othertales Q: Agent-Based PCB Design Automation Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
![Research Status: Experimental](https://img.shields.io/badge/research%20status-experimental-orange)

## Abstract

Othertales Q is a research framework for autonomous agent-based printed circuit board (PCB) design, incorporating advanced natural language processing, hardware knowledge representation, and automated design rule verification. This framework implements a multi-agent approach to traverse the entire PCB design workflow—from requirement analysis and component selection through schematic capture, physical layout, and manufacturing output generation. By leveraging transformer-based language models coupled with domain-specific optimization algorithms, Othertales Q demonstrates a novel approach to hardware-aware AI design systems that can reason about electrical, mechanical, and thermal constraints while generating manufacturable PCB designs.

## Research Objectives

1. Explore the efficacy of transformer-based language models in translating natural language PCB requirements into actionable design specifications
2. Develop a specialized agent architecture optimized for hardware design tasks using multi-agent collaboration
3. Implement and validate algorithms for automatic component placement and trace routing that respect complex electrical constraints
4. Evaluate the framework's performance against traditional manual PCB design methodologies across metrics of design time, error rates, and manufacturability
5. Create novel approaches to integrate design rule checking (DRC) and signal integrity analysis within the AI-driven design loop

## System Architecture

The system is architected as a directed graph of specialized agents that process and transform the design state:

```
User Requirements → Requirements Analysis → Component Selection → Schematic Capture 
                 → PCB Layout (Placement) → PCB Layout (Routing) → DRC/Signal Analysis 
                 → Manufacturing Output Generation
```

Each node in this workflow is managed by a specialized agent:

### 1. Requirements Analysis Agent

Extracts structured design parameters from natural language specifications:
- Circuit purpose and functional requirements
- Operating conditions (voltage, current, frequency ranges)
- Environmental constraints (temperature, humidity, vibration)
- Physical form factor limitations
- Performance requirements (speed, power, noise)
- Regulatory compliance needs (EMC, safety standards)

### 2. Component Selection Agent

Selects optimal components based on requirements and constraints:
- Component matching algorithm using vector-based similarity search
- Automated BOM optimization for cost, size, and availability
- Supply chain risk assessment
- Part interchangeability analysis
- Thermal compatibility verification

### 3. Schematic Capture Agent

Designs logical circuit connections:
- Automated creation of hierarchical schematics
- Signal path optimization
- Power delivery network design
- Component interconnectivity based on datasheet specifications
- Design-for-test integration
- Reference designation standardization

### 4. PCB Layout Agent (Placement)

Optimizes component placement on the board:
- Multi-objective placement optimization (thermal, signal integrity, EMI)
- Layer stackup optimization
- Power/ground plane design
- Mechanical constraint satisfaction
- Thermal zone management
- Component clearance enforcement

### 5. PCB Layout Agent (Routing)

Implements intelligent trace routing:
- Differential pair handling with impedance matching
- Length-matched routing for high-speed signals
- Via minimization algorithms
- Topology optimization for power distribution networks
- Controlled impedance trace calculation and verification
- EMI-aware routing heuristics

### 6. Simulation Agent

Performs electrical and thermal analysis:
- Design rule checking (DRC)
- Signal integrity analysis (crosstalk, reflection, attenuation)
- Power integrity verification
- Thermal simulation
- EMC pre-compliance testing
- Stress and vibration modeling

### 7. Manufacturing Output Agent

Generates fabrication and assembly files:
- Gerber file generation (RS-274X format)
- NC drill file creation
- Pick-and-place position files
- Bill of materials (BOM) with vendor information
- Assembly drawings and documentation
- Quality control test specifications

## Technical Implementation Details

### Language Model Architecture

The framework utilizes Hugging Face's transformer models with specialized modifications:
- Model: Llama 3.3 70B model (othertales.ai/q-llama3.3-70B-pcb) trained on PCB and hardware design
- Context window: 8192 tokens standard, extendable to 16384 tokens with context compression
- Training: Extensively trained on PCB design documentation, component datasheets, and design examples
- Temperature parameter: Customizable (0.7 default) to balance creativity/precision
- Token generation limits: Configurable to match design complexity
- Domain-specific training: Specialized knowledge of electrical engineering principles, component characteristics, and PCB design rules

### Hardware Knowledge Representation

Component database using specialized embeddings:
- High-dimensional vector representation (768d) of component properties
- Hierarchical clustering of functionally similar components
- Dynamic electrical compatibility matrix
- Thermal profile modeling
- Parametric search capability

### Routing Algorithm

Multi-objective routing system implementing:
- A* pathfinding with custom cost functions
- Lee algorithm for maze routing with modifications
- Multi-layer via cost optimization
- Topological autorouting for buses and related signals
- Differential pair co-routing with gap control
- Length matching with serpentine pattern generation

### Design Rule Implementation

Comprehensive rule system for validation:
- Minimum trace width and spacing (adaptive to copper weight)
- Pad-to-trace clearances
- Via annular ring requirements
- Silkscreen clearances
- Solder mask tolerances
- Board edge clearances
- Controlled impedance verification
- High-voltage isolation requirements

### Simulation Integration

Circuit simulation through:
- SPICE-compatible netlists generation
- S-parameter analysis for high-frequency circuits
- Power delivery network impedance analysis
- Thermal resistance modeling
- Frequency domain reflection analysis
- Time domain signal integrity verification

## Installation and Configuration

### System Requirements

- Python 3.9 or higher
- CUDA-compatible GPU (optional, for accelerated inference)
- 8GB+ RAM (16GB+ recommended for complex designs)
- 20GB disk space for model storage and design files

### Installation

```bash
# Clone the repository
git clone https://github.com/othertales/othertales-q.git
cd othertales-q

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .
```

### Configuration

The framework can be configured through the Configuration class:

```python
from agent.configuration import Configuration

config = {
    "configurable": {
        # Model configuration
        "model_name": "othertales.ai/q-llama3.3-70B-pcb",  # Default PCB-specialized LLM
        "max_new_tokens": 1024,       # Maximum token generation
        "temperature": 0.7,           # Temperature parameter (0.0-1.0)
        "top_p": 0.95,                # Nucleus sampling parameter
        "repetition_penalty": 1.2,    # Repetition penalty
        
        # Hardware acceleration
        "device": 0,                  # GPU device ID (-1 for CPU)
        
        # Design constraints
        "output_dir": "designs/project_name",
        "default_board_width": 100.0,  # mm
        "default_board_height": 80.0,  # mm
        
        # Simulation parameters
        "run_simulations": True,
        "simulation_detail_level": "standard"  # basic, standard, detailed
    }
}
```

## Usage & Integration

### Basic Usage

```python
from othertales_q import graph
from agent.state import State
from langchain_core.messages import HumanMessage

# Initialize state with detailed requirements
state = State()
state.messages.append(HumanMessage(content="""
Design a 4-layer PCB for a microcontroller-based data acquisition system with the following specifications:
- STM32F4 series MCU (LQFP package)
- Dual-channel 16-bit ADC with programmable gain amplifier frontend
- USB 2.0 Full Speed interface for data transfer
- microSD card slot for local data storage
- Power supply: 5V input with 3.3V and 1.8V regulated outputs
- Maximum board dimensions: 80mm x 50mm
- Operating temperature range: -20°C to +85°C
- 4-layer stackup with internal ground and power planes
- Controlled impedance required for USB differential pairs (90Ω ±10%)
"""))

# Execute the design pipeline
result = graph.invoke(state)

# Access results
print(f"Design complete: {result.design_complete}")
print(f"Schematic file: {result.schematic_file}")
print(f"PCB file: {result.pcb_file}")
print(f"Manufacturing files: {', '.join(result.manufacturing_files)}")
print(f"Simulation results: {result.simulation_results}")
```

### Advanced Usage: Design Constraints

```python
from othertales_q import graph
from agent.state import State
from langchain_core.messages import HumanMessage

# Initialize with very specific constraints
state = State()
state.user_requirements = """
Design a 6-layer PCB for a high-speed FPGA-based signal processing board:
- Xilinx Artix-7 FPGA (XC7A100T) in FGG484 package
- 4 channels of 14-bit ADC at 250 MSPS (AD9680)
- DDR3 SDRAM (2 x 4Gb)
- PCIe x4 edge connector for host communication
- Clock distribution network with jitter cleaner (AD9523-1)
- Layer stack-up must be:
  * Top: Signal + components
  * Layer 2: Ground
  * Layer 3: Power planes (1.0V, 1.8V, 2.5V, 3.3V)
  * Layer 4: Signal
  * Layer 5: Ground
  * Bottom: Signal + components
- Impedance requirements:
  * 100Ω differential for PCIe and ADC LVDS pairs
  * 50Ω single-ended for clock lines
- Maximum board dimensions: 170mm x 110mm
- Must include proper power sequencing for FPGA
- Thermal considerations for FPGA (include thermal vias)
"""

result = graph.invoke(state)
```

### Advanced Usage: Custom Component Database Integration

```python
import json
from othertales_q import graph
from agent.configuration import Configuration
from agent.state import State
from component_database import ComponentDatabase, Component

# Load custom component database
db = ComponentDatabase(db_path="custom_components")
db.load_from_json("custom_components.json")
db.add_component(Component(
    id="custom-ic-001",
    name="XYZ123 Specialized ADC",
    description="24-bit 1MSPS ADC with integrated PGA",
    type="adc",
    manufacturer="XYZ Semiconductors",
    part_number="XYZ123",
    specs={
        "resolution": 24,
        "channels": 8,
        "sampling_rate": 1000000,
        "interface": "SPI"
    },
    package="TQFP-48",
    footprint="Package_QFP:TQFP-48_7x7mm_P0.5mm"
))

# Configure framework to use custom database
config = {
    "configurable": {
        "component_db_path": "custom_components"
    }
}

# Initialize and run
state = State()
state.user_requirements = "Design a sensor interface board using the XYZ123 ADC..."
result = graph.invoke(state, config=config)
```

## Limitations & Future Research Directions

Current limitations of the framework include:

1. **Complex RF Design**: Limited capabilities for RF circuits above 2.4GHz
2. **Advanced Packaging**: Partial support for BGA fanout optimization
3. **3D Integration**: Currently limited to 2D planar designs
4. **Regulatory Compliance**: Limited autonomous reasoning about regional compliance requirements
5. **Supply Chain Integration**: Static component database without real-time availability

Future research directions:

1. Integration of electromagnetic field simulation for antenna design and EMC compliance
2. Advanced optimization techniques for multi-board assemblies
3. Implementation of generative design for mechanical enclosures
4. Development of transfer learning techniques between different hardware domains
5. Integration of reinforcement learning for adaptive routing strategies
6. Extension to flexible and rigid-flex PCB design

## Contributing

Research contributions are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-contribution`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-contribution`)
5. Open a Pull Request

## Citing this Work

If you use Othertales Q in your research, please cite:

```
@software{othertales_q_2025,
  author = {James, David},
  title = {Othertales Q: Agent-Based PCB Design Automation Framework},
  url = {https://github.com/othertales/othertales-q},
  version = {0.1.0},
  year = {2025},
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

This research was made possible through the integration of several open-source frameworks and methodologies:

- LangGraph for agent orchestration and workflow management
- Hugging Face Transformers for language model implementation
- KiCad for schematic and PCB file format compatibility
- Open source EDA algorithms for routing and placement optimization

## Contact

David James - david@othertales.co

Project Link: [https://github.com/othertales/othertales-q](https://github.com/othertales/othertales-q)
Copyright © 2025 Adventures of the Persistently Impaired (...and Other Tales) Limited of 85 Great Portland Street, London W1W 7LT under exclusive license to Other Tales LLC of 8 The Green, Suite B, Dover DE 19901 United States.
