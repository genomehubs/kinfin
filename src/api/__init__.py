from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from api.utils import load_clustering_datasets

from .core.limiter import limiter


def run_server(
    port: int,
    nodesdb_f: str,
    cluster_f: str,
    ndb_f: str,
    # pfam_mapping_f: str,
    # ipr_mapping_f: str,
    # go_mapping_f: str,
    # taxon_idx_mapping_file: str,
    # sequence_ids_f: str,
) -> None:
    import os

    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    current_dir = os.path.dirname(__file__)
    dataset_path = os.path.join(current_dir, "clustering.json")
    load_clustering_datasets(dataset_path)

    from api.endpoints import router
    from api.sessions import query_manager

    query_manager.cluster_f = cluster_f
    query_manager.nodesdb_f = nodesdb_f
    # query_manager.sequence_ids_f = sequence_ids_f
    # query_manager.taxon_idx_mapping_file = taxon_idx_mapping_file
    # query_manager.pfam_mapping_f = pfam_mapping_f
    # query_manager.ipr_mapping_f = ipr_mapping_f
    # query_manager.go_mapping_f = go_mapping_f

    app = FastAPI()
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    def rate_limit_handler(request, exc):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
        )

    ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(
            ","
        )
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/")
    def hello():
        return {"hi": "hello"}

    app.include_router(router)

    uvicorn.run(app=app, port=int(port))
