"""SENTINEL AI - REST API Endpoint

Öncelik 5: Docker Integration
Exposes AI Orchestrator via FastAPI (Headless mode - no Qt dependencies)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn

from src.ai.schemas import IntentType
from src.ai.tool_registry import build_tool_spec, get_supported_intents, get_tool_for_intent
from src.ai.command_builder import get_command_builder

# Initialize FastAPI app
app = FastAPI(
    title="SENTINEL AI API",
    description="Security Testing Automation with AI Orchestration",
    version="2.1.0"
)

_command_builder = get_command_builder()


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
    command: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "SENTINEL AI API"}


@app.get("/api/tools", response_model=ToolStatusResponse)
async def list_tools():
    """List all available intent types"""
    intents = [intent.value for intent in get_supported_intents()]
    return {"tools": intents, "count": len(intents)}


@app.post("/api/execute", response_model=ExecuteIntentResponse)
async def execute_intent(request: ExecuteIntentRequest):
    """Prepare a command deterministically for a given intent"""
    try:
        try:
            intent_type = IntentType(request.intent_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown intent type: {request.intent_type}"
            )

        tool_spec = build_tool_spec(
            intent_type=intent_type,
            target=request.target,
            params=request.params
        )

        if tool_spec is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported intent type: {request.intent_type}"
            )

        tool_def = get_tool_for_intent(intent_type)
        explanation = tool_def.description if tool_def else ""

        command, error = _command_builder.build(tool_spec, explanation)

        if error or not command:
            raise HTTPException(
                status_code=400,
                detail=f"Command build failed: {error or 'unknown error'}"
            )

        return ExecuteIntentResponse(
            success=True,
            intent_type=request.intent_type,
            target=request.target,
            tool_started=False,
            message="Command prepared",
            command=command.model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get backend statistics"""
    try:
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
    pass


if __name__ == "__main__":
    uvicorn.run(
        "src.application.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
