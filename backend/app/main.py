"""
FastAPI Application Entry Point

Main application module that configures and initializes the FastAPI application
for the Duolingo clone backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI application
app = FastAPI(
    title="Duolingo Clone API",
    description="Backend API for the Duolingo clone language learning platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint providing basic API information."""
    return {"message": "Duolingo Clone API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and deployment."""
    return {"status": "healthy", "message": "API is running"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)