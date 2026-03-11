from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import time
import hashlib
import json
import uuid
import asyncio

from proxy.classifier import classify_complexity, count_tokens
from proxy.router import select_model
from proxy.model_registry import MODEL_REGISTRY
from proxy.providers import get_provider
from proxy.cache import check_semantic_cache, store_semantic_cache
from proxy.cost import calculate_cost, calculate_frontier_cost

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "auto"
    messages: list[Message]
    max_tokens: Optional[int] = 4096
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False


@router.post("/v1/chat/completions")
async def chat_completions(
    request_body: ChatCompletionRequest,
    request: Request,
    x_client_id: Optional[str] = Header(None),
    x_preferred_provider: Optional[str] = Header(None),
    x_max_cost_usd: Optional[float] = Header(None),
    x_force_tier: Optional[str] = Header(None),
    x_skip_cache: Optional[str] = Header(None),
    x_cache_ttl: Optional[int] = Header(None),
):
    wall_start = time.monotonic()
    request_id = str(uuid.uuid4())

    if request_body.stream:
        raise HTTPException(
            status_code=400,
            detail={"message": "Streaming not supported in v1. Use stream=false.",
                    "type": "streaming_not_supported"}
        )

    messages = [m.dict() for m in request_body.messages]

    # ── Step 1: Token counting ────────────────────────────────────────────
    full_text = " ".join(m["content"] for m in messages if isinstance(m.get("content"), str))
    prompt_tokens_estimate = count_tokens(full_text)

    # ── Step 2: Messages hash for exact cache lookup ───────────────────────
    messages_json = json.dumps(messages, sort_keys=True)
    messages_hash = hashlib.sha256(messages_json.encode()).hexdigest()

    # ── Step 3: Semantic cache check ──────────────────────────────────────
    cache_result = None
    skip_cache = x_skip_cache and x_skip_cache.lower() == "true"

    if not skip_cache:
        cache_result = await check_semantic_cache(
            messages_hash=messages_hash,
            full_text=full_text,
            db=request.app.state.db_pool,
            redis=request.app.state.redis,
        )

    if cache_result:
        wall_elapsed = round((time.monotonic() - wall_start) * 1000)
        asyncio.create_task(log_request(
            request_id=request_id,
            requested_model=request_body.model,
            selected_model=cache_result["model"],
            selected_provider="cache",
            prompt_tokens=prompt_tokens_estimate,
            completion_tokens=cache_result["completion_tokens"],
            input_cost_usd=0,
            output_cost_usd=0,
            frontier_cost_usd=0,
            cache_hit=True,
            cache_similarity=cache_result.get("similarity"),
            total_latency_ms=wall_elapsed,
            provider_latency_ms=0,
            complexity_score=None,
            complexity_tier=None,
            complexity_signals=None,
            messages_hash=messages_hash,
            message_count=len(messages),
            finish_reason=cache_result.get("finish_reason", "stop"),
            client_id=x_client_id,
            db=request.app.state.db_pool,
        ))
        return build_response(
            request_id=request_id,
            content=cache_result["content"],
            model=cache_result["model"],
            prompt_tokens=prompt_tokens_estimate,
            completion_tokens=cache_result["completion_tokens"],
            finish_reason=cache_result.get("finish_reason", "stop"),
            complexity_score=None,
            complexity_tier=None,
            requested_model=request_body.model,
            selected_model=cache_result["model"],
            selected_provider="cache",
            cache_hit=True,
            cache_similarity=cache_result.get("similarity"),
            failover=False,
            total_cost_usd=0,
            total_latency_ms=wall_elapsed,
        )

    # ── Step 4: Classify complexity ───────────────────────────────────────
    if x_force_tier:
        complexity_result = {
            "score": 0.5,
            "tier": x_force_tier,
            "signals": [f"forced_tier:{x_force_tier}"],
            "total_tokens": prompt_tokens_estimate,
            "reasoning": f"Tier forced by X-Force-Tier header: {x_force_tier}"
        }
    else:
        complexity_result = classify_complexity(messages)

    # ── Step 5: Select model + failover chain ─────────────────────────────
    selected_model, failover_chain = select_model(
        requested_model=request_body.model,
        complexity_result=complexity_result,
        prompt_tokens=prompt_tokens_estimate,
        preferred_provider=x_preferred_provider,
        max_cost_per_request=x_max_cost_usd,
    )

    # ── Step 6: Call provider with failover ───────────────────────────────
    provider_start = time.monotonic()
    provider_response = None
    actual_model = selected_model
    failover_occurred = False
    original_model = None

    models_to_try = [selected_model] + failover_chain

    for model_id in models_to_try:
        model_info = MODEL_REGISTRY.get(model_id)
        if not model_info:
            continue

        provider_name = model_info["provider"]

        try:
            provider = get_provider(provider_name)
            provider_response = await provider.complete(
                model=model_id,
                messages=messages,
                max_tokens=request_body.max_tokens or 4096,
                temperature=request_body.temperature or 0.7,
            )
            actual_model = model_id

            if model_id != selected_model:
                failover_occurred = True
                original_model = selected_model

            break  # Success — stop trying

        except Exception as e:
            import httpx
            error_str = str(e)
            # Transient errors: rate limit, server errors, network failures → try next provider
            if (isinstance(e, (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError))
                    or any(code in error_str for code in ["429", "500", "502", "503"])):
                print(f"Failover from {model_id}: {error_str[:100]}")
                continue
            else:
                # 4xx client errors (bad request, auth) — don't retry, fail immediately
                raise HTTPException(
                    status_code=400,
                    detail={"message": f"Provider error: {error_str}", "type": "provider_error"}
                )

    if not provider_response:
        raise HTTPException(
            status_code=503,
            detail={"message": "All providers unavailable", "type": "all_providers_exhausted"}
        )

    provider_elapsed = round((time.monotonic() - provider_start) * 1000)
    wall_elapsed = round((time.monotonic() - wall_start) * 1000)

    # ── Step 7: Calculate cost ─────────────────────────────────────────────
    actual_model_info = MODEL_REGISTRY[actual_model]
    input_cost, output_cost = calculate_cost(
        model_info=actual_model_info,
        prompt_tokens=provider_response.prompt_tokens,
        completion_tokens=provider_response.completion_tokens,
    )
    frontier_cost = calculate_frontier_cost(
        tier=complexity_result["tier"],
        prompt_tokens=provider_response.prompt_tokens,
        completion_tokens=provider_response.completion_tokens,
    )

    # ── Step 8: Store in semantic cache ───────────────────────────────────
    asyncio.create_task(store_semantic_cache(
        messages_hash=messages_hash,
        full_text=full_text,
        response_content=provider_response.content,
        response_metadata={
            "model": actual_model,
            "finish_reason": provider_response.finish_reason,
            "prompt_tokens": provider_response.prompt_tokens,
            "completion_tokens": provider_response.completion_tokens,
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
        },
        ttl_hours=x_cache_ttl / 3600 if x_cache_ttl else None,
        db=request.app.state.db_pool,
        redis=request.app.state.redis,
    ))

    # ── Step 9: Log request ───────────────────────────────────────────────
    asyncio.create_task(log_request(
        request_id=request_id,
        requested_model=request_body.model,
        selected_model=actual_model,
        selected_provider=actual_model_info["provider"],
        prompt_tokens=provider_response.prompt_tokens,
        completion_tokens=provider_response.completion_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        frontier_cost_usd=frontier_cost,
        cache_hit=False,
        cache_similarity=None,
        total_latency_ms=wall_elapsed,
        provider_latency_ms=provider_elapsed,
        complexity_score=complexity_result["score"],
        complexity_tier=complexity_result["tier"],
        complexity_signals=complexity_result["signals"],
        messages_hash=messages_hash,
        message_count=len(messages),
        finish_reason=provider_response.finish_reason,
        failover_occurred=failover_occurred,
        original_model=original_model,
        client_id=x_client_id,
        db=request.app.state.db_pool,
    ))

    # ── Step 10: Return response ──────────────────────────────────────────
    return build_response(
        request_id=request_id,
        content=provider_response.content,
        model=actual_model,
        prompt_tokens=provider_response.prompt_tokens,
        completion_tokens=provider_response.completion_tokens,
        finish_reason=provider_response.finish_reason,
        complexity_score=complexity_result["score"],
        complexity_tier=complexity_result["tier"],
        requested_model=request_body.model,
        selected_model=actual_model,
        selected_provider=actual_model_info["provider"],
        cache_hit=False,
        cache_similarity=None,
        failover=failover_occurred,
        total_cost_usd=input_cost + output_cost,
        total_latency_ms=wall_elapsed,
    )


def build_response(request_id, content, model, prompt_tokens, completion_tokens,
                   finish_reason, complexity_score, complexity_tier, requested_model,
                   selected_model, selected_provider, cache_hit, cache_similarity,
                   failover, total_cost_usd, total_latency_ms):
    """Build OpenAI-format response with NeuralGate metadata."""
    return {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": finish_reason
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "x_neuralgate": {
            "request_id": request_id,
            "complexity_score": round(complexity_score, 4) if complexity_score else None,
            "complexity_tier": complexity_tier,
            "requested_model": requested_model,
            "selected_model": selected_model,
            "selected_provider": selected_provider,
            "cache_hit": cache_hit,
            "cache_similarity": cache_similarity,
            "failover": failover,
            "total_cost_usd": round(total_cost_usd, 8) if total_cost_usd else 0,
            "total_latency_ms": total_latency_ms,
        }
    }


async def log_request(request_id, requested_model, selected_model, selected_provider,
                      prompt_tokens, completion_tokens, input_cost_usd, output_cost_usd,
                      frontier_cost_usd, cache_hit, cache_similarity, total_latency_ms,
                      provider_latency_ms, complexity_score, complexity_tier, complexity_signals,
                      messages_hash, message_count, finish_reason, db,
                      failover_occurred=False, original_model=None, client_id=None):
    """Insert request log record. Called as async background task."""
    try:
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO requests (
                    request_id, requested_model, selected_model, selected_provider,
                    failover_occurred, original_model,
                    complexity_score, complexity_tier, complexity_signals,
                    prompt_tokens, completion_tokens,
                    input_cost_usd, output_cost_usd, frontier_cost_usd,
                    cache_hit, cache_similarity,
                    total_latency_ms, provider_latency_ms,
                    messages_hash, message_count, finish_reason, client_id
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11,
                    $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22
                )
            """,
            request_id, requested_model, selected_model, selected_provider,
            failover_occurred, original_model,
            complexity_score, complexity_tier,
            json.dumps(complexity_signals) if complexity_signals else None,
            prompt_tokens, completion_tokens,
            input_cost_usd, output_cost_usd, frontier_cost_usd,
            cache_hit, cache_similarity,
            total_latency_ms, provider_latency_ms,
            messages_hash, message_count, finish_reason, client_id)
    except Exception as e:
        print(f"Log error: {e}")
