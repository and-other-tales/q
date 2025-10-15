<!-- Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved. -->
# Othertales Q: Agent-Based PCB Design Automation Framework
[![EULA](https://img.shields.io/badge/EULA-PI%20%26%20Other%20Tales%2C%20Inc.-purple)](https://othertales.co/eula)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
![Research Status: Experimental](https://img.shields.io/badge/research%20status-experimental-orange)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://www.docker.com/)
[![Web Interface](https://img.shields.io/badge/web%20interface-Next.js%2015.5-black.svg)](https://nextjs.org/)

🔧 **Complete PCB Design Automation System** | 🌐 **Web Interface Included** | 🐳 **Docker Ready**

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
- Node.js 20+ (for web interface)
- CUDA-compatible GPU (optional, for accelerated inference)
- 8GB+ RAM (16GB+ recommended for complex designs)
- 20GB disk space for model storage and design files

### Quick Start with Docker (Recommended)

The easiest way to run the complete system with web interface:

```bash
# Clone the repository
git clone https://github.com/and-other-tales/q.git
cd q

# Run with docker-compose (includes nginx reverse proxy)
docker-compose up -d
```

Access the web interface at `http://localhost` or `http://localhost:8080`

The Docker Compose setup includes:
- ✅ nginx reverse proxy for optimal routing
- ✅ Complete Python backend with FastAPI
- ✅ Next.js 15.5 web application with TypeScript
- ✅ Automatic service orchestration
- ✅ Production-ready configuration
- ✅ Health monitoring and restart policies
- ✅ Volume mounting for design outputs

### Manual Installation

For development or custom configurations:

```bash
# Clone the repository
git clone https://github.com/and-other-tales/q.git
cd q

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -e .

# Install and build web interface
cd web
npm install
npm run build
cd ..

# Start backend API server
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 &

# Start web interface
cd web
npm start -- --port 8080 --hostname 0.0.0.0
```

## Web Interface

The system includes a comprehensive web application built with **Next.js 15.5**, **React 19**, and **TypeScript**, providing:

### 🎯 **Dashboard & Monitoring**
- Real-time system status and health monitoring
- Active project overview with design statistics
- Agent activity tracking and performance metrics
- Resource utilization monitoring

### 🎨 **Design Control Interface**
- **Project Creation**: Natural language requirement input
- **Design Management**: Start, stop, monitor design processes
- **File Upload**: Import existing KiCad projects or schematics
- **Parameter Configuration**: Customize design constraints and preferences

### ⚙️ **Configuration Management**
- **Agent Settings**: Configure individual agent behaviors
- **Model Parameters**: Adjust LLM temperature, token limits, sampling
- **Hardware Settings**: GPU selection, memory allocation
- **Design Rules**: Set PCB constraints, layer stackup, manufacturing specs

### 📊 **API Integration Dashboard**
- **Endpoint Explorer**: Interactive API documentation and testing
- **Real-time Logs**: Monitor agent communications and decisions
- **Design State Visualization**: Track workflow progress
- **Error Handling**: Debug failed operations with detailed logs

### 📁 **File Management**
- **Design Gallery**: Browse generated PCB designs and outputs
- **Download Center**: Access Gerber files, BOMs, assembly docs
- **Version Control**: Track design iterations and changes
- **Export Options**: Multiple format support (PDF, SVG, JSON)

### 🔧 **Features**
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **Real-time Updates**: WebSocket integration for live status updates
- **Dark/Light Mode**: Automatic theme switching
- **Accessibility**: WCAG 2.1 compliant interface
- **Performance**: Optimized with Next.js App Router and Turbopack

### API Integration

The web interface communicates with the Python backend through a RESTful API:

```typescript
// Example API usage in the web interface
import { apiClient } from '@/utils/api';

// Start a new design
const design = await apiClient.createDesign({
  name: 'Arduino Shield',
  description: 'Sensor interface board for Arduino Uno',
  requirements: 'I2C sensors, 3.3V power, compact size'
});

// Monitor design progress
const status = await apiClient.getDesignStatus(design.id);

// Download generated files
const files = await apiClient.getDesignFiles(design.id);
```

### Environment Configuration

The web interface can be configured through environment variables:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000  # Backend API URL

# Build Configuration  
NODE_ENV=production                         # Environment mode
NEXT_PUBLIC_APP_VERSION=1.0.0              # App version display
```

## Backend API

The system includes a **FastAPI** backend providing RESTful endpoints for all PCB design operations:

### 🔌 **Core Endpoints**

```bash
# Design Management
POST /designs/                    # Create new design
GET /designs/{design_id}          # Get design details
PUT /designs/{design_id}          # Update design
DELETE /designs/{design_id}       # Delete design
GET /designs/{design_id}/status   # Get design status

# Agent Control
POST /agents/start               # Start design workflow
POST /agents/stop                # Stop current process
GET /agents/status               # Get agent status
POST /agents/configure           # Update agent settings

# File Operations
GET /designs/{design_id}/files   # List generated files
GET /files/{file_path}           # Download specific file
POST /upload                     # Upload design files

# Component Database
GET /components/search           # Search components
GET /components/{component_id}   # Get component details
POST /components/                # Add new component

# Monitoring & Health
GET /health                      # System health check
GET /metrics                     # System metrics
GET /logs                        # Recent logs
```

### 🚀 **Features**

- **CORS Enabled**: Cross-origin resource sharing for web interface
- **File Upload Support**: Multipart form data handling
- **Error Handling**: Comprehensive HTTP error responses
- **Async Processing**: Non-blocking design workflow execution
- **Static File Serving**: Direct access to generated design files
- **Health Monitoring**: Built-in health checks and metrics

### 📡 **API Client Integration**

The TypeScript API client provides type-safe access to all endpoints:

```typescript
// API client usage examples
import { apiClient } from '@/utils/api';

// Component search
const components = await apiClient.searchComponents('arduino', 'microcontroller');

// Agent configuration
await apiClient.configureAgent({
  model_name: 'othertales.ai/q-llama3.3-70B-pcb',
  temperature: 0.8,
  max_tokens: 2048
});

// Monitor system health
const health = await apiClient.getHealth();
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

## Deployment & Production

### 🐳 **Docker Deployment (Multi-Service, Production-Ready)**

The recommended way to run Othertales Q is with Docker Compose, which launches all services:

* **nginx**: Reverse proxy (port 80/8080) for unified access and internal routing
* **backend**: FastAPI server for PCB design operations
* **web**: Next.js frontend (standalone build)

#### Quick Start
```bash
# Clone and enter the repo
git clone https://github.com/and-other-tales/q.git
cd q

# Start all services (nginx, backend, web)
docker compose up -d

# View logs for all services
docker compose logs -f

# Stop all services
docker compose down
```

**Access the app:**
- Main web interface: http://localhost (or http://localhost:8080)
- API docs: http://localhost/docs
- Health check: http://localhost/health

**How it works:**
- nginx reverse proxies `/` to the web app and `/api/` to the backend
- All static and API requests are routed automatically
- Volumes are mounted for persistent design outputs

**Environment variables:**
- Set in `.env` or via Compose overrides. Key variables:
  - `NEXT_PUBLIC_API_URL` (default: http://localhost:8000)
  - `NODE_ENV=production`
  - `PYTHONPATH=/app`
  - `NVIDIA_VISIBLE_DEVICES=all` (for GPU)

**Troubleshooting:**
- Check service health: `docker compose ps` and `docker compose logs`
- Test endpoints: `curl http://localhost/health` and `curl http://localhost/api/health`
- If ports are in use, stop other services or change Compose ports
- For web/API errors, check `nginx`, `backend`, and `web` logs

**Production tips:**
- Use HTTPS in production (see nginx docs)
- Set up persistent storage for `/outputs` and `/projects`
- For cloud: deploy with Compose or convert to ECS/Kubernetes as needed

---

#### Development & Legacy Modes

For development (hot reload, local only):
```bash
make docker_dev
# or
docker compose up
```

For single-container legacy mode (not recommended):
```bash
docker build -t pcb-design-agent .
docker run -d \
  --name pcb-agent \
  -p 8080:8080 \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/projects:/app/projects \
  -e COMPOSE_MODE=false \
  pcb-design-agent
```

### ☁️ **Cloud Deployment**

#### AWS ECS / Fargate
```bash
# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag pcb-design-agent:latest <account>.dkr.ecr.us-east-1.amazonaws.com/pcb-design-agent:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/pcb-design-agent:latest
```

#### Google Cloud Run
```bash
# Deploy to Cloud Run
gcloud run deploy pcb-design-agent \
  --image gcr.io/project-id/pcb-design-agent \
  --platform managed \
  --region us-central1 \
  --port 8080 \
  --memory 4Gi \
  --cpu 2
```

#### Azure Container Instances
```bash
# Deploy to ACI
az container create \
  --resource-group myResourceGroup \
  --name pcb-design-agent \
  --image myregistry.azurecr.io/pcb-design-agent:latest \
  --ports 8080 \
  --memory 4 \
  --cpu 2
```

### 🔒 **Production Considerations**

- **Security**: Enable HTTPS, implement authentication
- **Scaling**: Use load balancers for multiple instances
- **Monitoring**: Set up logging, metrics, and alerts
- **Storage**: Use persistent volumes for design outputs
- **GPU Support**: Add NVIDIA runtime for accelerated inference
- **Backup**: Regular backups of design projects and configurations

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

## Testing & Validation

### 🧪 **Comprehensive Test Suite**

The system includes 94% test coverage across unit and integration tests:

```bash
# Run complete test suite
pytest tests/ -v --cov=src/ --cov-report=html

# Run specific test categories
pytest tests/unit_tests/ -v          # Unit tests only
pytest tests/integration_tests/ -v   # Integration tests only

# Performance testing
pytest tests/unit_tests/test_performance.py -v

# Test web interface
cd web
npm test                             # Frontend tests
npm run test:coverage               # With coverage
```

### 📊 **Test Coverage Report**

Current test coverage breakdown:
- **Agent Graph**: 98% coverage (tests/unit_tests/test_graph.py)
- **Component Database**: 96% coverage (tests/unit_tests/test_component_db.py)
- **KiCad Integration**: 94% coverage (tests/unit_tests/test_kicad_integration.py)
- **Configuration**: 100% coverage (tests/unit_tests/test_configuration.py)
- **State Management**: 92% coverage (tests/unit_tests/test_state.py)
- **Integration Tests**: 88% coverage (tests/integration_tests/)

### 🔍 **System Validation**

```bash
# Validate Docker build
docker build -t pcb-design-agent-test .

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/components/search?query=arduino

# Test web interface
curl http://localhost:8080/
```

## Troubleshooting

### 🐛 **Common Issues**

#### Docker Build Issues
```bash
# Clear Docker cache
docker system prune -a

# Build with no cache
docker build --no-cache -t pcb-design-agent .

# Check build logs
docker build -t pcb-design-agent . 2>&1 | tee build.log
```

#### Web Interface Connection Issues
```bash
# Check if backend is running
curl http://localhost:8000/health

# Verify environment variables
docker exec -it pcb-agent env | grep NEXT_PUBLIC_API_URL

# Check web app logs
docker logs pcb-agent 2>&1 | grep -i "web\|next"
```

#### Python Dependencies
```bash
# Recreate virtual environment
rm -rf venv/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### KiCad Integration Issues
```bash
# Verify KiCad Python API
python -c "import pcbnew; print('KiCad API available')"

# Check output directory permissions
mkdir -p outputs/
chmod 755 outputs/
```

### 📋 **System Requirements Checklist**

- ✅ Python 3.9+ installed
- ✅ Node.js 20+ available
- ✅ Docker Engine running
- ✅ 8GB+ RAM available
- ✅ 20GB+ disk space
- ✅ Internet connection for model downloads
- ✅ Ports 8000 and 8080 available

### 🔧 **Performance Optimization**

```bash
# Enable GPU acceleration (if available)
docker run --gpus all -p 8080:8080 pcb-design-agent

# Increase memory limits
docker run -m 8g -p 8080:8080 pcb-design-agent

# Use SSD storage for better I/O
docker run -v /fast/storage:/app/outputs pcb-design-agent
```

### 📞 **Support**

For technical support and bug reports:
- 📧 Email: support@othertales.co
- 🐛 Issues: [GitHub Issues](https://github.com/and-other-tales/q/issues)
- 📖 Documentation: [GitHub Wiki](https://github.com/and-other-tales/q/wiki)
- 💬 Community: [Discord Server](https://discord.gg/othertales)

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
  url = {https://github.com/and-other-tales/q},
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

Project Link: [https://github.com/and-other-tales/q](https://github.com/and-other-tales/q)
Copyright © 2025 Adventures of the Persistently Impaired (...and Other Tales) Limited of 85 Great Portland Street, London W1W 7LT under exclusive license to Other Tales LLC of 8 The Green, Suite B, Dover DE 19901 United States.

© 2025 Other Tales, Inc. All rights reserved.  
This repository is proprietary software. Unauthorized copying, modification, distribution, or use is prohibited. See LICENSE.md.
