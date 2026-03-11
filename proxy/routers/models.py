from fastapi import APIRouter
import time
from proxy.model_registry import MODEL_REGISTRY
from proxy.settings import get_available_providers

router = APIRouter()


@router.get("/v1/models")
async def list_models():
    """List all available models in OpenAI-compatible format."""
    available_providers = get_available_providers()
    models = [
        {"id": "auto",     "object": "model", "created": int(time.time()), "owned_by": "neuralgate", "description": "Automatically route to optimal model based on complexity"},
        {"id": "cheapest", "object": "model", "created": int(time.time()), "owned_by": "neuralgate", "description": "Always use cheapest available model"},
        {"id": "balanced", "object": "model", "created": int(time.time()), "owned_by": "neuralgate", "description": "Always use mid-tier model"},
        {"id": "best",     "object": "model", "created": int(time.time()), "owned_by": "neuralgate", "description": "Always use frontier model"},
    ]
    for model_id, info in MODEL_REGISTRY.items():
        if info["provider"] in available_providers:
            models.append({
                "id": model_id,
                "object": "model",
                "created": int(time.time()),
                "owned_by": info["provider"],
                "neuralgate": {
                    "tier": info["tier"],
                    "provider": info["provider"],
                    "context_window": info["context_window"],
                    "input_cost_per_million": info["input_cost_per_million"],
                    "output_cost_per_million": info["output_cost_per_million"],
                    "description": info.get("description", ""),
                }
            })
    return {"object": "list", "data": models}
