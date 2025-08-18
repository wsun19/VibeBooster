# VibeBooster - Anthropic API Proxy

A simple Python proxy for the Anthropic API that forwards and inspects requests.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

3. Run the proxy:
```bash
python main.py
```

The proxy will start on `http://127.0.0.1:8000`

## Testing

Test with curl:
```bash
curl -X POST http://127.0.0.1:8000/v1/messages \
-H "Content-Type: application/json" \
-d '{
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 25,
    "messages": [
        {"role": "user", "content": "Hello, world"}
    ]
}'
```

For streaming responses:
```bash
curl -X POST http://127.0.0.1:8000/v1/messages \
-H "Content-Type: application/json" \
-d '{
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 100,
    "messages": [
        {"role": "user", "content": "Hello, world"}
    ],
    "stream": true
}'
```

## Features

- Forwards requests to Anthropic API
- Supports both streaming and non-streaming responses
- Logs all requests and responses for inspection
- Health check endpoint at `/health`