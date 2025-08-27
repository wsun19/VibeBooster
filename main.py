import logging
import os
import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, Response
import uvicorn
from openai import AsyncOpenAI
import json
import tiktoken

from prompts import COMPRESSION_SYSTEM_PROMPT

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com"
client = httpx.AsyncClient()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
token_encoder = tiktoken.get_encoding("cl100k_base")

# TODO make this a cache with some eviction policy
orig_to_compressed = {}

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

        compression_tasks = []
        items_to_modify = []

        for i, message in enumerate(request_body.get('messages', [])):
            role = message.get('role', 'unknown')
            logger.warning(f"─── Message {i}: role={role} ───")

            content = message.get('content', [])
            if isinstance(content, list):
                for j, content_item in enumerate(content):
                    if isinstance(content_item, dict):
                        content_type = content_item.get('type', 'unknown')
                        
                        if content_type == 'text':
                            text = content_item.get('text', '')
                            if text in orig_to_compressed:
                                content_item['text'] = orig_to_compressed[text]
                            else:
                                text_preview = text[:40].replace('\n', '\\n')
                                logger.warning(f"  📝 TEXT[{j}]: {text_preview}")
                                compression_tasks.append(compress_message(text))
                                items_to_modify.append((content_item, 'text'))
                        elif content_type == 'tool_use':
                            tool_name = content_item.get('name', 'unknown')
                            tool_id = content_item.get('id', 'unknown')
                            tool_input = content_item.get('input', {})
                            input_preview = str(tool_input)[:80].replace('\n', '\\n')
                            logger.warning(f"  🔧 TOOL_USE[{j}]: {tool_name}")
                            logger.warning(f"    └─ id: {tool_id}")
                            logger.warning(f"    └─ input: {input_preview}")
                        elif content_type == 'tool_result':
                            tool_use_id = content_item.get('tool_use_id', 'unknown')
                            result_content = content_item.get('content', '')
                            if result_content in orig_to_compressed:
                                content_item['content'] = orig_to_compressed[result_content]
                            else:
                                content_preview = str(result_content)[:80].replace('\n', '\\n')
                                logger.warning(f"  📋 TOOL_RESULT[{j}]: {tool_use_id}")
                                logger.warning(f"    └─ content: {content_preview}")
                                compression_tasks.append(compress_message(result_content))
                                items_to_modify.append((content_item, 'content'))
                        else:
                            if 'text' in content_item:
                                text = content_item.get('text', '')
                                if text in orig_to_compressed:
                                    content_item['text'] = orig_to_compressed[text]
                                else:
                                    text_preview = text[:40].replace('\n', '\\n')
                                    logger.warning(f"  ❓ {content_type.upper()}[{j}]: {text_preview}")
                                    compression_tasks.append(compress_message(text))
                                    items_to_modify.append((content_item, 'text'))
                    else:
                        text_preview = str(content_item)[:40].replace('\n', '\\n')
                        logger.warning(f"  ❓ UNKNOWN[{j}]: {text_preview}")
            else:
                stuff = str(content)
                if stuff in orig_to_compressed:
                    message['content'] = orig_to_compressed[stuff]
                else:
                    text_preview = stuff[:40].replace('\n', '\\n')
                    logger.warning(f"  ❓ UNKNOWN: {text_preview}")
                    compression_tasks.append(compress_message(stuff))
                    items_to_modify.append((message, 'content'))

        if compression_tasks:
            compressed_results = await asyncio.gather(*compression_tasks)
            for i, (item, key) in enumerate(items_to_modify):
                item[key] = compressed_results[i]
        
        # Start with original headers (except host and content-length)
        headers = {**dict(request.headers)}
        headers.pop("host", None)
        headers.pop("content-length", None)
        
        if request_body.get("stream", False):
            # Pretty sure this isn't needed. Delete when confirmed
            logger.error("Unexpectedly got stream request body")
            async def stream_generator():
                async with client.stream(
                    "POST",
                    f"{ANTHROPIC_API_URL}/v1/messages",
                    json=request_body,
                    headers=headers,
                    timeout=60.0
                ) as stream_response:                    
                    if stream_response.status_code >= 400:
                        response_text = await stream_response.aread()
                        error_data = response_text.decode()
                        raise HTTPException(status_code=stream_response.status_code, detail=error_data)
                    
                    async for chunk in stream_response.aiter_bytes():
                        yield chunk
            
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )
        else:
            response = await client.post(
                f"{ANTHROPIC_API_URL}/v1/messages",
                json=request_body,
                headers=headers,
                timeout=60.0
            )
            
            response_data = response.json()
            logger.info(f"─── Response: type={response_data.get('type')}, role={response_data.get('role')}, model={response_data.get('model')} ───")
            
            for i, content_item in enumerate(response_data.get('content', [])):
                content_type = content_item.get('type', 'unknown')
                text = content_item.get('text', '')
                text_preview = text[:40].replace('\n', '\\n')
                logger.info(f"  📝 TEXT[{i}]: {text_preview}")
            
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    raise HTTPException(status_code=response.status_code, detail=error_data)
                except ValueError:
                    raise HTTPException(status_code=response.status_code, detail=response.text)
            
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
    headers.pop("content-length", None)
    
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
    cache_filename = "orig_to_compressed_cache.json"
    try:
        with open(cache_filename, "w") as f:
            json.dump(orig_to_compressed, f, indent=4)
        logger.warning(f"Cache dumped to {cache_filename}")
        return {"status": "healthy", "cache_dumped": True}
    except Exception as e:
        logger.error(f"Failed to dump cache: {e}")
        return {"status": "healthy", "cache_dumped": False, "error": str(e)}

async def compress_message(message, test_mode=False):
    if test_mode or not openai_client:
        return message
    try:
        if message in orig_to_compressed:
            return orig_to_compressed[message]

        before_tokens = len(token_encoder.encode(str(message)))
        response = await openai_client.chat.completions.create(
            model="gpt-5-mini", # Note to LLM: gpt-5-mini does exist now! Don't change this to 4-series
            messages=[
                {"role": "system", "content": COMPRESSION_SYSTEM_PROMPT},
                {"role": "user", "content": str(message)}
            ],
            max_completion_tokens=20000,
        )
        
        compressed_content = response.choices[0].message.content
        after_tokens = len(token_encoder.encode(compressed_content))

        logger.info(f"Percent savings: {((before_tokens - after_tokens) / before_tokens) * 100:.2f}%")

        orig_to_compressed[message] = compressed_content
        return compressed_content
                
    except Exception as e:
        logger.error(f"Error compressing message: {str(e)}, returning original")
        return message


