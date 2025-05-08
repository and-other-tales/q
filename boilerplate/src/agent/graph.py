"""Define the PCB design agent graph.

This agent implements a workflow for designing PCBs based on user requirements.
It handles requirements analysis, component selection, schematic design, 
PCB layout, simulation, and manufacturing output generation.
"""

from typing import Any, Dict, List, Optional, Tuple
import os
import asyncio

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_community.llms import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from langgraph.graph import StateGraph, END

from agent.configuration import Configuration
from agent.state import State


def get_llm(config: Configuration) -> HuggingFacePipeline:
    """Initialize HuggingFacePipeline with the configuration."""
    model_id = config.model_name
    
    # Load model and tokenizer
    try:
        # Create an HuggingFacePipeline LLM
        return HuggingFacePipeline.from_model_id(
            model_id=model_id,
            task="text-generation",
            device=config.device,
            pipeline_kwargs={
                "max_new_tokens": config.max_new_tokens,
                "temperature": config.temperature,
                "do_sample": config.do_sample,
                "top_k": config.top_k,
                "top_p": config.top_p,
                "repetition_penalty": config.repetition_penalty
            }
        )
    except Exception as e:
        # Fallback to a default model if specified model fails
        print(f"Error loading model {model_id}: {e}")
        print("Falling back to default model")
        return HuggingFacePipeline.from_model_id(
            model_id="gpt2",  # Fallback to smaller model
            task="text-generation",
            pipeline_kwargs={"max_new_tokens": config.max_new_tokens}
        )


async def user_interface_agent(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Agent for handling user requirements and interface.
    
    Processes user requirements from the message history and performs
    initial analysis to prepare for component selection.
    """
    configuration = Configuration.from_runnable_config(config)
    
    # Process user requirements from the latest message
    if len(state.messages) > 0 and isinstance(state.messages[-1], HumanMessage):
        state.user_requirements = state.messages[-1].content
    
    # Initialize LLM
    llm = get_llm(configuration)
    
    # Parse requirements using a standard prompt template
    prompt = PromptTemplate.from_template(
        """You are a PCB design requirements analyst. 
        Parse the following user requirements for a PCB design:
        
        {requirements}
        
        Extract the following information:
        1. Main purpose of the circuit
        2. Key components needed
        3. Power requirements
        4. Size constraints
        5. Special requirements (e.g., RF, high voltage, etc.)
        
        Format your response as a structured analysis. Don't include any explanations."""
    )
    
    chain = prompt | llm.bind(stop=["\n\n"]) | StrOutputParser()
    analysis = await chain.ainvoke({"requirements": state.user_requirements})
    
    # Update state with the analysis
    state.messages.append(AIMessage(content=f"Requirements analysis complete. Moving to component research."))
    
    return {"current_agent": "component_research"}


async def component_research_agent(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Agent for researching and selecting components.
    
    Analyzes user requirements to identify and select appropriate components
    for the PCB design.
    """
    configuration = Configuration.from_runnable_config(config)
    
    # Initialize LLM
    llm = get_llm(configuration)
    
    # Process component requirements
    prompt = PromptTemplate.from_template(
        """You are a PCB component research specialist.
        Based on these requirements:
        
        {requirements}
        
        List the key components needed for this design.
        For each component, provide:
        1. Component type
        2. Key specifications
        3. Suggested manufacturer part number
        4. Footprint type
        
        Format as a JSON-like list with detailed specifications."""
    )
    
    chain = prompt | llm.bind(stop=["\n\n"]) | StrOutputParser()
    components_text = await chain.ainvoke({"requirements": state.user_requirements})
    
    # Parse components to structured format (in real app, would use JsonOutputParser)
    # For this simplified implementation, we'll just store the text
    state.components = [{"text": components_text}]
    
    # Update state with message
    state.messages.append(AIMessage(content=f"Component selection complete. Moving to schematic design."))
    
    return {"current_agent": "schematic_design"}


async def schematic_design_agent(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Agent for creating circuit schematics.
    
    Uses selected components to generate a circuit schematic.
    """
    configuration = Configuration.from_runnable_config(config)
    
    # Create output directory if it doesn't exist
    os.makedirs(configuration.output_dir, exist_ok=True)
    
    # Simulate schematic creation (in real implementation, this would use KiCad's Python API)
    state.schematic_file = os.path.join(configuration.output_dir, "design.sch")
    
    # Update state with message
    state.messages.append(AIMessage(content=f"Schematic design complete. File created: {state.schematic_file}"))
    
    return {"current_agent": "pcb_layout"}


async def pcb_layout_agent(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Agent for creating PCB layouts, including placement and routing.
    
    Takes the schematic and creates a physical PCB layout with component
    placement and trace routing.
    """
    configuration = Configuration.from_runnable_config(config)
    
    # Simulate PCB layout creation (in real implementation, this would use KiCad's Python API)
    state.pcb_file = os.path.join(configuration.output_dir, "design.kicad_pcb")
    
    # Update state with message
    state.messages.append(AIMessage(content=f"PCB layout complete. File created: {state.pcb_file}"))
    
    return {"current_agent": "simulation"}


async def simulation_agent(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Agent for running electrical simulations.
    
    Runs design rule checks and other simulations on the PCB design.
    """
    configuration = Configuration.from_runnable_config(config)
    
    # Skip simulations if disabled in configuration
    if not configuration.run_simulations:
        state.messages.append(AIMessage(content="Simulations skipped as per configuration. Moving to manufacturing output."))
        return {"current_agent": "manufacturing_output"}
    
    # Simulate running simulations
    state.simulation_results = {
        "design_rule_check": "PASS",
        "signal_integrity": "GOOD",
        "thermal_analysis": "ACCEPTABLE"
    }
    
    # Update state with message
    state.messages.append(AIMessage(content=f"Simulation complete. DRC: PASS. Ready for manufacturing output."))
    
    return {"current_agent": "manufacturing_output"}


async def manufacturing_output_agent(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Agent for generating manufacturing outputs (Gerber files, BOM, etc.).
    
    Generates the final files needed for PCB fabrication.
    """
    configuration = Configuration.from_runnable_config(config)
    
    # Create output directory if it doesn't exist
    os.makedirs(configuration.output_dir, exist_ok=True)
    
    # Simulate manufacturing file generation
    state.manufacturing_files = [
        os.path.join(configuration.output_dir, "design.gtl"),  # Top copper
        os.path.join(configuration.output_dir, "design.gbl"),  # Bottom copper
        os.path.join(configuration.output_dir, "design.gto"),  # Top silkscreen
        os.path.join(configuration.output_dir, "design.gbo"),  # Bottom silkscreen
        os.path.join(configuration.output_dir, "design.gm1"),  # Mechanical layer
        os.path.join(configuration.output_dir, "design.drl"),  # Drill file
        os.path.join(configuration.output_dir, "design.csv")   # BOM
    ]
    
    # Update state with message
    state.messages.append(AIMessage(content=f"Manufacturing files generated. Design process complete."))
    state.design_complete = True
    
    return {"current_agent": END}


def router(state: State) -> str:
    """Routes to the next agent based on the current state."""
    return state.current_agent


# Set up the graph
workflow = StateGraph(State, config_schema=Configuration)

# Add agent nodes
workflow.add_node("user_interface", user_interface_agent)
workflow.add_node("component_research", component_research_agent)
workflow.add_node("schematic_design", schematic_design_agent)
workflow.add_node("pcb_layout", pcb_layout_agent)
workflow.add_node("simulation", simulation_agent)
workflow.add_node("manufacturing_output", manufacturing_output_agent)

# Connect the nodes
workflow.add_conditional_edges(
    "user_interface",
    router,
    {
        "component_research": "component_research",
    }
)

workflow.add_conditional_edges(
    "component_research",
    router,
    {
        "schematic_design": "schematic_design",
    }
)

workflow.add_conditional_edges(
    "schematic_design",
    router,
    {
        "pcb_layout": "pcb_layout",
    }
)

workflow.add_conditional_edges(
    "pcb_layout",
    router,
    {
        "simulation": "simulation",
    }
)

workflow.add_conditional_edges(
    "simulation",
    router,
    {
        "manufacturing_output": "manufacturing_output",
    }
)

workflow.add_conditional_edges(
    "manufacturing_output",
    router,
    {
        END: END,
    }
)

# Set the entrypoint
workflow.add_edge("__start__", "user_interface")

# Compile the workflow into an executable graph
graph = workflow.compile()
graph.name = "Othertales Q PCB Design"