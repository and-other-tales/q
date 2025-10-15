<!-- Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved. -->
# Enhanced Component Database & Datasheet Analysis

## Overview

The PCB Design Agent now includes a comprehensive component sourcing and datasheet analysis system that:

1. **Searches real-time component databases** from major distributors (Digi-Key, Mouser, LCSC, Octopart, Arrow)
2. **Downloads and analyzes manufacturer datasheets** automatically
3. **Extracts PCB layout requirements** from datasheet specifications
4. **Generates routing recommendations** based on component characteristics
5. **Provides component availability and pricing** information

## Component Sourcing Workflow

### 1. Multi-Distributor Search
```python
# Search across multiple distributors simultaneously
sourcer = ComponentSourcer()
components = await sourcer.search_components(
    query="STM32F405 ARM Cortex-M4",
    category="Microcontroller",
    limit=50
)
```

The system searches:
- **Digi-Key API** - Comprehensive component database
- **Mouser API** - Global electronic components
- **LCSC API** - Cost-effective Asian components
- **Octopart API** - Aggregated component search
- **Arrow API** - Enterprise component sourcing

### 2. Datasheet Analysis Pipeline

When a component is selected, the system:

1. **Downloads the manufacturer datasheet** (PDF format)
2. **Caches the datasheet** locally for future use
3. **Extracts text content** using PyPDF2
4. **Parses key information** using regex patterns and NLP
5. **Generates structured analysis** for PCB design

### 3. Information Extraction

From each datasheet, the system extracts:

#### Pin Configuration
```python
pin_configuration = {
    "1": {
        "name": "VDD",
        "description": "Power supply pin",
        "type": "power"
    },
    "2": {
        "name": "PA0",
        "description": "General purpose I/O pin",
        "type": "bidirectional"
    }
    # ... more pins
}
```

#### Electrical Characteristics
```python
electrical_characteristics = {
    "supply_voltage": "3.3",
    "supply_voltage_unit": "V",
    "operating_current": "150",
    "operating_current_unit": "mA",
    "max_frequency": "168",
    "max_frequency_unit": "MHz"
}
```

#### Package Dimensions
```python
package_dimensions = {
    "length_mm": 10.0,
    "width_mm": 10.0,
    "height_mm": 1.6,
    "pitch_mm": 0.5
}
```

#### Layout Recommendations
```python
recommended_layout = {
    "requires_ground_plane": True,
    "requires_power_plane": True,
    "has_differential_pairs": True,
    "required_impedance": 90  # ohms
}
```

## PCB Layout Generation

### 1. Component-Driven Layout Rules

The system analyzes all components in a project and generates:

- **Layer count recommendations** based on component complexity
- **Ground/power plane requirements** from high-speed components
- **Controlled impedance specifications** for critical signals
- **Thermal management zones** for power components
- **Signal integrity rules** extracted from datasheets

### 2. Example Layout Analysis

```python
layout_recommendations = {
    "layer_count": 4,  # Minimum required layers
    "requires_ground_plane": True,
    "requires_power_plane": True,
    "controlled_impedance_nets": [
        {
            "component": "STM32F405RGT6",
            "impedance": 90,  # USB differential pairs
            "nets": ["USB_DP", "USB_DN"]
        }
    ],
    "signal_integrity_rules": [
        "Keep high-speed digital traces away from analog circuits",
        "Use ground plane for return paths on high-frequency signals",
        "Maintain 90Ω impedance for USB differential pairs"
    ],
    "thermal_zones": [
        {
            "component": "LDO_Regulator",
            "requires_thermal_vias": True,
            "copper_pour_recommended": True
        }
    ]
}
```

### 3. Routing Integration

The extracted information directly feeds into the PCB routing engine:

- **Trace width calculations** based on current requirements
- **Via sizing** from thermal and electrical specifications  
- **Component placement constraints** from package dimensions
- **EMI/EMC considerations** from signal integrity notes

## API Integration

### Supported Distributors

1. **Digi-Key**
   - API: https://developer.digikey.com/
   - Coverage: 13+ million components
   - Features: Real-time inventory, pricing, parametric search

2. **Mouser Electronics**  
   - API: https://www.mouser.com/api-hub/
   - Coverage: 6+ million components
   - Features: Global inventory, lifecycle status

3. **LCSC (JLCPCB)**
   - API: Public component database
   - Coverage: 500k+ components
   - Features: PCB assembly integration, cost-effective parts

4. **Octopart**
   - API: https://octopart.com/api/
   - Coverage: Aggregated distributor data
   - Features: Price comparison, availability across vendors

5. **Arrow Electronics**
   - API: https://developers.arrow.com/
   - Coverage: Enterprise components
   - Features: Long-tail availability, authorized distribution

### Configuration

Create a `.env` file with your API keys:

```bash
# Distributor API Keys
DIGIKEY_API_KEY=your_digikey_key
MOUSER_API_KEY=your_mouser_key
OCTOPART_API_KEY=your_octopart_key
ARROW_API_KEY=your_arrow_key

# Cache Settings
COMPONENT_CACHE_DIR=component_cache
DATASHEET_CACHE_DIR=datasheet_cache
DATASHEET_TIMEOUT_SECONDS=30

# Analysis Settings
ENABLE_DATASHEET_ANALYSIS=true
ANALYSIS_CACHE_DURATION_DAYS=7
```

## Usage Examples

### Basic Component Search

```python
from agent.enhanced_component_db import get_enhanced_component_database

# Initialize enhanced database
db = get_enhanced_component_database()

# Search with datasheet analysis
results = await db.search_and_analyze_components(
    query="Arduino microcontroller development board",
    category="Microcontroller",
    analyze_datasheets=True
)

for component, analysis in results:
    print(f"Found: {component.part_number}")
    if analysis:
        print(f"  Pins: {len(analysis.pin_configuration)}")
        print(f"  Layout requirements: {analysis.recommended_layout}")
```

### Project-Level Analysis

```python
# Analyze complete project
project_components = [arduino, regulator, connector, sensor]

# Get layout recommendations for entire project
layout_rec = db.get_layout_recommendations_for_project(project_components)

print(f"Recommended layers: {layout_rec['layer_count']}")
print(f"Ground plane: {layout_rec['requires_ground_plane']}")
print(f"Impedance control: {layout_rec['controlled_impedance_nets']}")
```

### Agent Integration

The enhanced component database integrates seamlessly with the PCB design agent workflow:

1. **Requirements Analysis** → Component category identification
2. **Component Research** → Multi-distributor search + datasheet analysis  
3. **Schematic Design** → Pin configuration and electrical constraints
4. **PCB Layout** → Physical dimensions and routing requirements
5. **Manufacturing** → Availability and supply chain information

## Benefits

### For PCB Designers
- **Accurate component information** directly from manufacturer datasheets
- **Automated layout rule generation** based on component specifications
- **Real-time availability and pricing** from multiple distributors
- **Reduced design errors** through datasheet-driven constraints

### For Automated Design
- **Intelligent component selection** based on actual specifications
- **Layout optimization** using manufacturer recommendations
- **Supply chain awareness** for manufacturable designs
- **Compliance checking** against electrical and thermal limits

### For Manufacturing
- **Component availability verification** before design finalization
- **Alternative component suggestions** for supply chain resilience
- **Cost optimization** through distributor price comparison
- **Assembly compatibility** checking for pick-and-place operations

## Future Enhancements

- **Machine learning models** for component recommendation
- **Parametric optimization** for multi-objective component selection
- **Supply chain risk analysis** and mitigation suggestions
- **Automated compliance checking** for regulatory standards
- **Integration with PLM systems** for enterprise workflows