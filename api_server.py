"""SENTINEL AI - REST API Endpoint

Öncelik 5: Docker Integration
Exposes AI Orchestrator via FastAPI (Headless mode - no Qt dependencies)
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai.orchestrator import AIOrchestrator
from src.ai.schemas import Intent, IntentType

# Initialize FastAPI app
app = FastAPI(
    title="SENTINEL AI API",
    description="Security Testing Automation with AI Orchestration",
    version="2.1.0"
)

# Initialize orchestrator (no coordinator needed for API mode)
orchestrator = AIOrchestrator(model="whiterabbitneo")



# Request/Response Models
class ExecuteIntentRequest(BaseModel):
    intent_type: str
    target: str
    params: Optional[Dict[str, Any]] = {}


class ToolStatusResponse(BaseModel):
    tools: List[str]
    count: int


class ExecuteIntentResponse(BaseModel):
    success: bool
    intent_type: str
    target: str
    tool_started: bool
    message: str


# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "SENTINEL AI API"}


@app.get("/api/tools", response_model=ToolStatusResponse)
async def list_tools():
    """List all available security tools"""
    # List of 10 available tools
    tools = [
        "ping", "ping_sweep", "port_scan", "service_detection", 
        "vuln_scan", "dns_lookup", "ssl_scan", "web_dir_enum",
        "subdomain_enum", "web_vuln_scan"
    ]
    return {"tools": tools, "count": len(tools)}


@app.post("/api/execute", response_model=ExecuteIntentResponse)
async def execute_intent(request: ExecuteIntentRequest):
    """Execute security testing intent"""
    try:
        # Map string to IntentType enum
        intent_type_map = {
            "ping": IntentType.PING,
            "ping_sweep": IntentType.PING_SWEEP,
            "port_scan": IntentType.PORT_SCAN,
            "service_detection": IntentType.SERVICE_DETECTION,
            "vuln_scan": IntentType.VULN_SCAN,
            "dns_lookup": IntentType.DNS_LOOKUP,
            "ssl_scan": IntentType.SSL_SCAN,
            "web_dir_enum": IntentType.WEB_DIR_ENUM,
            "subdomain_enum": IntentType.SUBDOMAIN_ENUM,
            "web_vuln_scan": IntentType.WEB_VULN_SCAN
        }
        
        if request.intent_type not in intent_type_map:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown intent type: {request.intent_type}"
            )
        
        # Create intent object
        intent = Intent(
            intent_type=intent_type_map[request.intent_type],
            target=request.target,
            params=request.params
        )
        
        # Execute via orchestrator
        result = orchestrator.execute_intent(intent)
        
        return ExecuteIntentResponse(
            success=result.get("tool_started", False),
            intent_type=request.intent_type,
            target=request.target,
            tool_started=result.get("tool_started", False),
            message=result.get("message", "Intent executed")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get backend statistics"""
    try:
        # Return basic stats
        return {
            "success": True,
            "stats": {
                "service": "SENTINEL AI API",
                "version": "2.1.0",
                "status": "operational"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Cleanup execution manager if needed
    pass


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
