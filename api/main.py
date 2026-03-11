"""
FastAPI Application

Main application entry point for the Agentic CoE API.
"""

# Load .env file FIRST before any other imports
from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from api.models import HealthResponse, ErrorResponse
from api.routes import agents, orchestration, websocket, simulation
from api.middleware import setup_middleware
from api.dependencies import initialize_dependencies
from api.routes.resolve_issue import router as resolve_router
from api.routes.bulk_import import router as bulk_import_router

from core.config_manager import ConfigManager
from core.logging_service import LoggingService
from core.state_manager import StateManager
from orchestration.agent_orchestrator import AgentOrchestrator

# Initialize logging
LoggingService.configure(
    log_level=logging.INFO,
    log_file="logs/api.log"
)

logger = LoggingService.get_logger("api")

# Create FastAPI app
app = FastAPI(
    title="Agentic CoE API",
    description="Production-ready API for multi-agent AI systems",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup middleware
setup_middleware(app)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Agentic CoE API...")
    
    try:
        # Initialize core components
        config_manager = ConfigManager(config_dir="configs")
        state_manager = StateManager(use_redis=False)
        orchestrator = AgentOrchestrator(state_manager=state_manager)
        
        # Initialize dependencies
        initialize_dependencies(config_manager, state_manager, orchestrator)
        
        # Register Self-Service Support Agent
        from agents.self_service_support_agent import SelfServiceSupportAgent
        support_agent = SelfServiceSupportAgent()
        await support_agent.initialize()
        orchestrator.register_agent(support_agent)
        
        # Register UTA (Unified Troubleshooting Assistant) Agent
        from agents import UTAAgent
        uta_agent = UTAAgent()
        await uta_agent.initialize()
        orchestrator.register_agent(uta_agent)
        logger.info("UTA Agent registered successfully")
        
        # Initialize Simulation Service (Skilling Agent POC)
        from api.routes.simulation import initialize_simulation_service
        initialize_simulation_service(config_manager)
        logger.info("Simulation service initialized successfully")
        
        logger.info("Agentic CoE API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start API: {str(e)}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Agentic CoE API...")
    
    try:
        from api.dependencies import get_state_manager
        state_manager = get_state_manager()
        await state_manager.close()
        
        logger.info("API shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint"""
    return {
        "name": "Agentic CoE API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns service status and health of dependent services.
    """
    try:
        from api.dependencies import get_config_manager, get_state_manager, get_orchestrator
        
        # Check core services
        config_manager = get_config_manager()
        state_manager = get_state_manager()
        orchestrator = get_orchestrator()
        
        services = {
            "config_manager": "healthy",
            "state_manager": "healthy",
            "orchestrator": "healthy",
            "registered_agents": str(len(orchestrator.agents))
        }
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            version="1.0.0",
            services=services
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            version="1.0.0",
            services={"error": str(e)}
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=None,
            timestamp=datetime.utcnow().isoformat(),
            request_id=getattr(request.state, "request_id", None)
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat(),
            request_id=getattr(request.state, "request_id", None)
        ).dict()
    )


# Include routers
app.include_router(agents.router)
app.include_router(orchestration.router)
app.include_router(websocket.router)
app.include_router(simulation.router)
app.include_router(resolve_router, prefix="/kg")
app.include_router(bulk_import_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
