# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
"""
FastAPI web service for PCB design agent.
Provides RESTful API endpoints for web interface integration.
"""

import asyncio
import os
import uuid
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import tempfile
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from agent.state import State
from agent.graph import graph
from agent.component_db import get_component_database, Component
from agent.configuration import Configuration


# Pydantic models for API
class PCBDesignRequest(BaseModel):
    """Request model for PCB design."""
    requirements: str = Field(..., description="Natural language requirements for the PCB design")
    config: Optional[Dict[str, Any]] = Field(default={}, description="Configuration parameters")


class PCBDesignResponse(BaseModel):
    """Response model for PCB design."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current status of the design job")
    message: str = Field(..., description="Status message")


class JobStatus(BaseModel):
    """Model for job status."""
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float  # 0.0 to 1.0
    current_stage: str
    message: str
    created_at: datetime
    updated_at: datetime
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ComponentSearchRequest(BaseModel):
    """Request model for component search."""
    query: str = Field(..., description="Search query for components")
    category: Optional[str] = Field(None, description="Component category filter")


class ComponentSearchResponse(BaseModel):
    """Response model for component search."""
    components: List[Dict[str, Any]] = Field(..., description="List of matching components")
    total_count: int = Field(..., description="Total number of matching components")


# Global job storage (in production, use Redis or database)
jobs: Dict[str, JobStatus] = {}
connected_websockets: Dict[str, WebSocket] = {}


# Create FastAPI app
app = FastAPI(
    title="Othertales Q PCB Design API",
    description="RESTful API for automated PCB design using AI agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Background task for running PCB design
async def run_pcb_design_task(job_id: str, requirements: str, config_dict: Dict[str, Any]):
    """Background task to run PCB design workflow."""
    
    job = jobs[job_id]
    
    try:
        # Update job status
        job.status = "running"
        job.current_stage = "Initializing"
        job.updated_at = datetime.now()
        await broadcast_job_update(job_id, job)
        
        # Create temporary output directory
        output_dir = tempfile.mkdtemp(prefix=f"pcb_design_{job_id}_")
        
        # Setup configuration
        config_dict.update({"output_dir": output_dir})
        config = RunnableConfig(configurable=config_dict)
        
        # Create initial state
        state = State()
        state.messages.append(HumanMessage(content=requirements))
        
        # Track progress through workflow stages
        stages = [
            "user_interface",
            "component_research", 
            "schematic_design",
            "pcb_layout",
            "simulation",
            "manufacturing_output"
        ]
        current_stage_index = 0
        
        # Custom callback to track progress
        class ProgressCallback:
            def __init__(self, job_id: str):
                self.job_id = job_id
                
            async def on_agent_start(self, agent_name: str):
                nonlocal current_stage_index
                if agent_name in stages:
                    current_stage_index = stages.index(agent_name)
                
                job = jobs[self.job_id]
                job.current_stage = agent_name.replace("_", " ").title()
                job.progress = current_stage_index / len(stages)
                job.updated_at = datetime.now()
                await broadcast_job_update(self.job_id, job)
        
        callback = ProgressCallback(job_id)
        
        # Run the PCB design workflow
        await callback.on_agent_start("user_interface")
        
        # Execute workflow
        result = await graph.ainvoke(state, config=config)
        
        # Final update
        job.status = "completed"
        job.progress = 1.0
        job.current_stage = "Completed"
        job.result = {
            "design_complete": result.get("design_complete", False),
            "schematic_file": result.get("schematic_file", ""),
            "pcb_file": result.get("pcb_file", ""),
            "manufacturing_files": result.get("manufacturing_files", []),
            "simulation_results": result.get("simulation_results", {}),
            "components": result.get("components", []),
            "output_directory": output_dir,
            "message_count": len(result.get("messages", []))
        }
        job.updated_at = datetime.now()
        
        await broadcast_job_update(job_id, job)
        
    except Exception as e:
        # Handle errors
        job.status = "failed"
        job.error = str(e)
        job.updated_at = datetime.now()
        await broadcast_job_update(job_id, job)


async def broadcast_job_update(job_id: str, job: JobStatus):
    """Broadcast job updates to connected WebSocket clients."""
    message = {
        "type": "job_update",
        "job_id": job_id,
        "status": job.status,
        "progress": job.progress,
        "current_stage": job.current_stage,
        "message": job.message,
        "updated_at": job.updated_at.isoformat(),
        "result": job.result,
        "error": job.error
    }
    
    # Send to all connected WebSocket clients
    disconnected_clients = []
    for client_id, websocket in connected_websockets.items():
        try:
            await websocket.send_text(json.dumps(message))
        except:
            disconnected_clients.append(client_id)
    
    # Clean up disconnected clients
    for client_id in disconnected_clients:
        connected_websockets.pop(client_id, None)


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Othertales Q PCB Design API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/design/start", response_model=PCBDesignResponse)
async def start_pcb_design(request: PCBDesignRequest, background_tasks: BackgroundTasks):
    """Start a new PCB design job."""
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Create job status
    job = JobStatus(
        job_id=job_id,
        status="pending",
        progress=0.0,
        current_stage="Queued",
        message="PCB design job created",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    jobs[job_id] = job
    
    # Start background task
    background_tasks.add_task(
        run_pcb_design_task,
        job_id,
        request.requirements,
        request.config if request.config is not None else {}
    )
    
    return PCBDesignResponse(
        job_id=job_id,
        status="pending",
        message="PCB design job started"
    )


@app.get("/api/design/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a PCB design job."""
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "current_stage": job.current_stage,
        "message": job.message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "result": job.result,
        "error": job.error
    }


@app.get("/api/design/jobs")
async def list_jobs():
    """List all PCB design jobs."""
    
    job_list = []
    for job in jobs.values():
        job_list.append({
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "current_stage": job.current_stage,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()
        })
    
    return {"jobs": job_list}


@app.delete("/api/design/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a PCB design job."""
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Clean up output directory if it exists
    job = jobs[job_id]
    if job.result and "output_directory" in job.result:
        output_dir = job.result["output_directory"]
        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
    
    del jobs[job_id]
    
    return {"message": "Job deleted successfully"}


@app.post("/api/components/search", response_model=ComponentSearchResponse)
async def search_components(request: ComponentSearchRequest):
    """Search for electronic components."""
    
    component_db = get_component_database()
    
    # Perform search
    components = component_db.search_components(request.query, request.category)
    
    # Convert to dict format
    component_dicts = [comp.to_dict() for comp in components]
    
    return ComponentSearchResponse(
        components=component_dicts,
        total_count=len(component_dicts)
    )


@app.get("/api/components/categories")
async def get_component_categories():
    """Get all component categories."""
    
    component_db = get_component_database()
    categories = component_db.get_all_categories()
    
    return {"categories": categories}


@app.get("/api/components/suggest")
async def suggest_components(requirements: str):
    """Get component suggestions based on requirements."""
    
    component_db = get_component_database()
    suggestions = component_db.suggest_components_for_circuit(requirements)
    
    # Convert to dict format
    suggestion_dicts = [comp.to_dict() for comp in suggestions]
    
    return {"suggestions": suggestion_dicts}


@app.get("/api/files/download/{job_id}/{file_type}")
async def download_file(job_id: str, file_type: str):
    """Download design files."""
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    if not job.result:
        raise HTTPException(status_code=400, detail="Job not completed")
    
    # Get file path based on type
    file_path = None
    
    if file_type == "schematic":
        file_path = job.result.get("schematic_file")
    elif file_type == "pcb":
        file_path = job.result.get("pcb_file")
    elif file_type in ["gerber", "manufacturing"]:
        # Return a zip file of all manufacturing files
        manufacturing_files = job.result.get("manufacturing_files", [])
        if manufacturing_files:
            # Create zip file
            import zipfile
            output_dir = job.result.get("output_directory", "")
            zip_path = os.path.join(output_dir, "manufacturing_files.zip")
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path in manufacturing_files:
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
            
            file_path = zip_path
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        filename=os.path.basename(file_path),
        media_type="application/octet-stream"
    )


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates."""
    
    await websocket.accept()
    connected_websockets[client_id] = websocket
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            
            # Echo back for ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        connected_websockets.pop(client_id, None)


# Mount static files (for serving web interface if needed)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")