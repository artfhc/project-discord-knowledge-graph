"""FastAPI backend for the web interface"""

from fastapi import FastAPI
from typing import List, Dict, Any

app = FastAPI(title="Discord Knowledge Graph API", version="0.1.0")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Discord KG Pipeline API"}

@app.get("/health")
async def health_check():
    """System health check"""
    # TODO: Check database connections, storage access
    return {"status": "healthy"}

@app.get("/graph/query")
async def query_graph(query: str):
    """Query the knowledge graph"""
    # TODO: Execute graph queries via Neo4j client
    pass

@app.get("/stats")
async def get_stats():
    """Get pipeline statistics"""
    # TODO: Return processing stats, node counts, etc.
    pass