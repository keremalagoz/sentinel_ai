"""SENTINEL AI - REST API Endpoint

Öncelik 5: Docker Integration
Exposes AI Orchestrator via FastAPI (Headless mode - no Qt dependencies)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn

from src.ai.schemas import IntentType
from src.ai.orchestrator import AIOrchestrator
from src.ai.tool_registry import (
    build_tool_spec,
    get_supported_intents,
    get_tool_for_intent,
    get_execution_tool_id,
    build_execution_kwargs,
)
from src.ai.command_builder import get_command_builder
from src.ai.schemas import FinalCommand
from src.core.sentinel_coordinator import SentinelCoordinator

# Initialize FastAPI app
app = FastAPI(
    title="SENTINEL AI API",
    description="Security Testing Automation with AI Orchestration",
    version="2.1.0"
)

_command_builder = get_command_builder()
_api_coordinator = SentinelCoordinator(db_path=":memory:")
_orchestrator = AIOrchestrator(coordinator=_api_coordinator)


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


class CreateSessionRequest(BaseModel):
    session_id: Optional[str] = None


class CreateSessionResponse(BaseModel):
    success: bool
    session_id: str


class ChatTurnRequest(BaseModel):
    session_id: str
    message: str
    target: Optional[str] = None
    memory_turn_limit: int = 6


class ChatTurnResponse(BaseModel):
    success: bool
    session_id: str
    message: str
    needs_clarification: bool
    requires_approval: bool
    intent_type: Optional[str] = None
    confidence: Optional[float] = None
    command: Optional[Dict[str, Any]] = None
    agent_observation: Optional[str] = None


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

        command = None
        error = None

        try:
            exec_tool_id = get_execution_tool_id(intent_type)
            exec_kwargs = build_execution_kwargs(intent_type, request.target, request.params)
            if exec_tool_id and exec_kwargs:
                integrated_tool = _api_coordinator.manager.get_tool(exec_tool_id)
                if integrated_tool is not None:
                    cmd_list = integrated_tool.tool.build_command(**exec_kwargs)
                    if cmd_list:
                        command = FinalCommand(
                            executable=cmd_list[0],
                            arguments=cmd_list[1:],
                            requires_root=tool_spec.requires_root,
                            risk_level=tool_spec.risk_level,
                            explanation=explanation,
                        )
        except Exception as exc:
            error = f"Execution-tool build failed: {exc}"

        if command is None:
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


@app.post("/api/chat/session", response_model=CreateSessionResponse)
async def create_chat_session(request: CreateSessionRequest):
    """Create or ensure a backend chat session."""
    try:
        session_id = _orchestrator.create_session(request.session_id)
        return CreateSessionResponse(success=True, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/turn", response_model=ChatTurnResponse)
async def chat_turn(request: ChatTurnRequest):
    """Process one multi-turn chat request and return safe action suggestion."""
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    try:
        result = _orchestrator.process_v2(
            user_input=request.message,
            target=request.target,
            session_id=request.session_id,
            memory_turn_limit=max(1, request.memory_turn_limit),
        )

        intent = result.get("intent")
        command = result.get("command")
        return ChatTurnResponse(
            success=bool(result.get("success")),
            session_id=result.get("session_id") or request.session_id,
            message=result.get("message") or "",
            needs_clarification=bool(result.get("needs_clarification")),
            requires_approval=bool(result.get("requires_approval")),
            intent_type=intent.intent_type.value if intent else None,
            confidence=float(intent.confidence) if intent else None,
            command=command.model_dump() if command else None,
            agent_observation=result.get("agent_observation"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 20):
    """Return recent turns for an existing chat session."""
    try:
        turns = _orchestrator.get_session_turns(session_id=session_id, limit=max(1, limit))
        return {
            "success": True,
            "session_id": session_id,
            "count": len(turns),
            "turns": turns,
        }
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
