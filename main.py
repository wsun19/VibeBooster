import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, Response
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com"
client = httpx.AsyncClient()

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

app = FastAPI(title="VibeBooster Anthropic Proxy", version="1.0.0", lifespan=lifespan)


@app.post("/v1/messages")
async def proxy_messages(request: Request):
    try:
        await ensure_client_healthy()
        
        request_body = await request.json()
        
        logger.info(f"Incoming request: {request.method} {request.url}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request body: {request_body}")
        
        # Start with original headers (except host)
        headers = {**dict(request.headers)}
        headers.pop("host", None)
        
        if request_body.get("stream", False):
            async with client.stream(
                "POST",
                f"{ANTHROPIC_API_URL}/v1/messages",
                json=request_body,
                headers=headers,
                timeout=60.0
            ) as response:
                logger.info(f"Anthropic response status: {response.status_code}")
                logger.info(f"Anthropic response headers: {dict(response.headers)}")
                
                if response.status_code >= 400:
                    response_text = await response.aread()
                    error_data = response_text.decode()
                    raise HTTPException(status_code=response.status_code, detail=error_data)
                
                async def generate():
                    async for chunk in response.aiter_bytes():
                        yield chunk
                
                return StreamingResponse(
                    generate(), 
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )
        else:
            response = await client.post(
                f"{ANTHROPIC_API_URL}/v1/messages",
                json=request_body,
                headers=headers,
                timeout=60.0
            )
            
            logger.info(f"Anthropic response status: {response.status_code}")
            logger.info(f"Anthropic response headers: {dict(response.headers)}")
            
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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)