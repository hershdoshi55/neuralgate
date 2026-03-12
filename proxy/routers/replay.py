from fastapi import APIRouter, HTTPException, Request
import json
import uuid
import time

from proxy.classifier import classify_complexity, count_tokens
from proxy.router import select_model
from proxy.model_registry import MODEL_REGISTRY
from proxy.providers import get_provider
from proxy.cost import calculate_cost

router = APIRouter()


@router.post("/requests/{request_id}/replay")
async def replay_request(request_id: str, request: Request):
    """
    Re-run a previously logged request through the full proxy pipeline.
    Requires STORE_PAYLOADS=true in .env for the payload to have been stored.
    Returns a comparison of original vs replayed result.
    """
    db = request.app.state.db_pool

    async with db.acquire() as conn:
        original = await conn.fetchrow(
            "SELECT * FROM requests WHERE request_id = $1", request_id
        )
        if not original:
            raise HTTPException(status_code=404, detail={
                "message": f"Request {request_id} not found.",
                "type": "not_found",
            })

        payload = await conn.fetchrow(
            "SELECT messages, request_params FROM request_payloads WHERE request_id = $1",
            request_id,
        )
        if not payload:
            raise HTTPException(status_code=404, detail={
                "message": (
                    f"No payload stored for request {request_id}. "
                    "Set STORE_PAYLOADS=true in .env and resend the request to enable replay."
                ),
                "type": "payload_not_found",
            })

    messages = json.loads(payload["messages"])
    params   = json.loads(payload["request_params"])

    # Re-run through the proxy pipeline
    t0 = time.monotonic()
    full_text     = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
    prompt_tokens = count_tokens(full_text)
    complexity    = classify_complexity(messages)

    selected_model, failover_chain = select_model(
        requested_model=params.get("model", "auto"),
        complexity_result=complexity,
        prompt_tokens=prompt_tokens,
    )

    provider_response = None
    actual_model = selected_model

    for model_id in [selected_model] + failover_chain:
        model_info = MODEL_REGISTRY.get(model_id)
        if not model_info:
            continue
        try:
            provider = get_provider(model_info["provider"])
            provider_response = await provider.complete(
                model=model_id,
                messages=messages,
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.7),
            )
            actual_model = model_id
            break
        except Exception:
            continue

    if not provider_response:
        raise HTTPException(status_code=503, detail={
            "message": "All providers unavailable during replay.",
            "type": "providers_unavailable",
        })

    elapsed_ms = round((time.monotonic() - t0) * 1000)
    model_info = MODEL_REGISTRY[actual_model]
    input_cost, output_cost = calculate_cost(
        model_info=model_info,
        prompt_tokens=provider_response.prompt_tokens,
        completion_tokens=provider_response.completion_tokens,
    )
    total_cost = input_cost + output_cost

    # Log the replayed request
    new_request_id = str(uuid.uuid4())
    async with db.acquire() as conn:
        await conn.execute("""
            INSERT INTO requests (
                request_id, requested_model, selected_model, selected_provider,
                complexity_score, complexity_tier,
                prompt_tokens, completion_tokens,
                input_cost_usd, output_cost_usd,
                total_latency_ms, messages_hash, message_count,
                finish_reason, cache_hit
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
        """,
        new_request_id,
        params.get("model", "auto"), actual_model, model_info["provider"],
        complexity["score"], complexity["tier"],
        provider_response.prompt_tokens, provider_response.completion_tokens,
        input_cost, output_cost,
        elapsed_ms, original["messages_hash"], original["message_count"],
        provider_response.finish_reason, False)

    return {
        "original": {
            "request_id":      request_id,
            "selected_model":  original["selected_model"],
            "complexity_tier": original["complexity_tier"],
            "complexity_score": float(original["complexity_score"] or 0),
            "total_cost_usd":  float(original["total_cost_usd"] or 0),
            "total_latency_ms": original["total_latency_ms"],
        },
        "replayed": {
            "request_id":      new_request_id,
            "selected_model":  actual_model,
            "complexity_tier": complexity["tier"],
            "complexity_score": round(complexity["score"], 4),
            "content":         provider_response.content,
            "total_cost_usd":  round(total_cost, 8),
            "total_latency_ms": elapsed_ms,
        },
        "diff": {
            "model_changed":    original["selected_model"] != actual_model,
            "tier_changed":     original["complexity_tier"] != complexity["tier"],
            "cost_delta_usd":   round(total_cost - float(original["total_cost_usd"] or 0), 8),
            "latency_delta_ms": elapsed_ms - (original["total_latency_ms"] or 0),
        },
    }
