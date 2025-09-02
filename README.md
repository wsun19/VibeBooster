# VibeBooster - Anthropic API Proxy

A Python proxy for the Anthropic API that automatically compresses requests to reduce token usage while maintaining full functionality. Intercepts API calls, compresses message content using GPT models, and forwards optimized requests to Anthropic's servers.

## Prerequisites

- Python 3.11 or higher
- OpenAI API key (for compression)

## Installation

### Option 1: Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/wsun19/vibebooster.git
cd vibebooster

# Install dependencies
uv sync
```

### Option 2: Using pip

```bash
# Clone the repository
git clone https://github.com/wsun19/vibebooster.git
cd vibebooster

# Install dependencies
pip install .
```

## Configuration

Set your OpenAI API key for message compression:

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

## Running the Proxy

### Option 1: Using uv

```bash
uv run python main.py
```

### Option 2: Using Python directly

```bash
python main.py
```

The proxy will start on `http://127.0.0.1:8000`

## Usage with Claude Code

Once the proxy is running, configure Claude Code to use it:

```bash
ANTHROPIC_BASE_URL=http://localhost:8000 claude
```

## Features

- **Message Compression**: Automatically compresses long messages to reduce token usage
- **Full API Compatibility**: Supports all Anthropic API endpoints and features
- **Logging**: Logs requests and responses for debugging and monitoring
- **Compression Statistics**: Logs token savings and compression ratios

## Parameters

- `MINIMUM_TOKENS_TO_COMPRESS`: The minimum number of tokens in a message to trigger compression (default: 200)
- `COMPRESSION_SYSTEM_PROMPT`: The system prompt used for compression. Located in prompts.py

## How It Works

1. Receives API requests from Claude Code or other clients
2. Extracts text content from messages
3. Compresses lengthy text using OpenAI's GPT models
4. Forwards compressed requests to Anthropic's API
5. Returns responses unchanged to the client

The compression is designed to be lossless for functionality while significantly reducing token count and API costs.

## Experimentation / next steps

1. Create an eval setup to compare using different models, model parameters, and compression prompts.
2. Inject an additional system prompt to explicitly ask the Anthropic API to minimize token output. See MINIMIZATION_SYSTEM_PROMPT in prompts.py
3. Enable usage of different LLM API providers. OpenAI does provide some free daily tokens if you opt into data sharing, but there are many other options too.
4. Right now, Vibebooster is aims to minimize token usage without any impact to performance. There are other potential targets for optimization, like (a) better performance at the cost of more token usage, or (b) accepting a hit to performance to save even more tokens.