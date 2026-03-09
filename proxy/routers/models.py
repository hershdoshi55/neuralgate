from fastapi import APIRouter
import time
from proxy.model_registry import MODEL_REGISTRY
from proxy.settings import get_available_providers

router = APIRouter()


@router.get("/v1/models")
async def list_models():
    """List all available models in OpenAI-compatible format."""
    available_providers = get_available_providers()
    models = []
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
