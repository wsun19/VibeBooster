import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, Response
import uvicorn
from openai import AsyncOpenAI
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com"
client = httpx.AsyncClient()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

system_prompt = """You are an AI assistant that functions as a lossless compression proxy for API requests. Your goal is to significantly reduce the token count of the incoming JSON payload while preserving all critical information and meaning.

You will be given a JSON object. Your output MUST be a modified, compressed version of this same JSON object.

**Most Important Rule:** If you are unsure whether a piece of information is safe to compress, modify, or remove, **DO NOT CHANGE IT**. Preserving the original context is your highest priority.

Follow these compression rules in order:

1.  **System Prompt Compression**: Identify the large, repetitive `system` prompt containing boilerplate instructions like "Development Guidelines" and "Tool usage policy." If this block is present, replace its entire content with the single placeholder string: `"<COMPRESSED_SYSTEM_PROMPT_V1>"`.

2.  **Path Deduplication**: Scan the entire JSON for all instances of the primary working directory path: `/Users/william/Documents/GitHub/VibeBooster/`. Replace every occurrence of this exact string with the short token `⟦CWD⟧`.

3.  **Safe Output Pruning**: In `tool_result` blocks, only remove high-confidence, zero-risk noise.
    * **Safe to remove**: The multi-line progress meter from `curl` outputs.
    * **Do NOT remove**: Any other content, especially error messages, stack traces, or logs.

Now, compress the following JSON payload:"""
async def ensure_client_healthy():
    global client
    try:
        if client.is_closed:
            logger.info("Client is closed, reinitializing...")
            client = httpx.AsyncClient()
    except Exception as e:
        logger.warning(f"Client health check failed, reinitializing: {e}")
        try:
            await client.aclose()
        except:
            pass
        client = httpx.AsyncClient()

@asynccontextmanager
async def lifespan(_):
    yield
    await client.aclose()
    if openai_client:
        await openai_client.close()

app = FastAPI(title="VibeBooster Anthropic Proxy", version="1.0.0", lifespan=lifespan)


@app.post("/v1/messages")
async def proxy_messages(request: Request):
    try:
        await ensure_client_healthy()
        
        request_body = await request.json()

        for i, message in enumerate(request_body.get('messages', [])):
            role = message.get('role', 'unknown')
            logger.info(f"Message {i}: role={role}")
            
            content = message.get('content', [])
            if isinstance(content, str):
                logger.info(f"  Content: type=text, text={content[:40].replace(chr(10), '\\n')}")
            elif isinstance(content, list):
                for j, content_item in enumerate(content):
                    if isinstance(content_item, dict):
                        content_type = content_item.get('type', 'unknown')
                        text = content_item.get('text', '')
                        logger.info(f"  Content {j}: type={content_type}, text={text[:40].replace(chr(10), '\\n')}")
                    else:
                        logger.info(f"  Content {j}: {str(content_item)[:40].replace(chr(10), '\\n')}")
            else:
                logger.info(f"  Content: {str(content)[:40].replace(chr(10), '\\n')}")
        
        # Compress the payload before forwarding
        compressed_body = await compress_payload(request_body, test_mode=True)
        
        # Start with original headers (except host)
        headers = {**dict(request.headers)}
        headers.pop("host", None)
        
        if compressed_body.get("stream", False):
            async with client.stream(
                "POST",
                f"{ANTHROPIC_API_URL}/v1/messages",
                json=compressed_body,
                headers=headers,
                timeout=60.0
            ) as stream_response:
                
                logger.info(f"Anthropic response status: {stream_response.status_code}")
                logger.info(f"Anthropic response headers: {dict(stream_response.headers)}")
                
                if stream_response.status_code >= 400:
                    response_text = await stream_response.aread()
                    error_data = response_text.decode()
                    raise HTTPException(status_code=stream_response.status_code, detail=error_data)
                
                return StreamingResponse(
                    stream_response.aiter_bytes(),
                    status_code=stream_response.status_code,
                    headers=dict(stream_response.headers)
                )
        else:
            response = await client.post(
                f"{ANTHROPIC_API_URL}/v1/messages",
                json=compressed_body,
                headers=headers,
                timeout=60.0
            )
            
            response_data = response.json()
            logger.info(f"Response: type={response_data.get('type')}, role={response_data.get('role')}, model={response_data.get('model')}")
            
            for i, content_item in enumerate(response_data.get('content', [])):
                content_type = content_item.get('type', 'unknown')
                text = content_item.get('text', '')
                logger.info(f"  Response content {i}: type={content_type}, text={text[:40].replace(chr(10), '\\n')}")
            
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    raise HTTPException(status_code=response.status_code, detail=error_data)
                except ValueError:
                    raise HTTPException(status_code=response.status_code, detail=response.text)
            
            response_data = response.json()
            logger.info(f"Anthropic response body: {response_data}")
            
            return JSONResponse(content=response_data)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_other_requests(request: Request, path: str):
    await ensure_client_healthy()
    
    headers = {**dict(request.headers)}
    headers.pop("host", None)
    
    target_url = f"{ANTHROPIC_API_URL}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    response = await client.request(
        method=request.method,
        url=target_url,
        headers=headers,
        content=await request.body()
    )
    
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

async def compress_payload(payload, test_mode=False):
    if test_mode or not openai_client:
        return payload
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(payload)}
            ],
            max_tokens=4000,
            temperature=0.1
        )
        
        compressed_content = response.choices[0].message.content
        
        return json.loads(compressed_content)
                
    except Exception as e:
        logger.error(f"Error compressing payload: {str(e)}, returning original")
        return payload


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)