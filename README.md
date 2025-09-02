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

## Examples

Here are some examples of compression that Vibebooster can perform to reduce token usage while maintaining full functionality:

### Path compression
For some tool calls, a full-length directory will unnecessarily be repeated, when we could compress that information or even delete it. In this example, each line of compression reduces the path from 21 to 5 tokens.

Before:
```
/Users/william/Documents/GitHub/goat-bot/frontend/src/App.js-      if (response.data.success) {
/Users/william/Documents/GitHub/goat-bot/frontend/src/App.js-        setAvailableProjects(response.data.projects);
/Users/william/Documents/GitHub/goat-bot/frontend/src/App.js-      }
/Users/william/Documents/GitHub/goat-bot/frontend/src/App.js-    } catch (err) {
... 
```

After:
```
!CWD! -      if (response.data.success) {
!CWD! -        setAvailableProjects(response.data.projects);
!CWD! -      }
!CWD! -    } catch (err) {
(b) 
...
!CWD! -> /Users/william/Documents/GitHub/goat-bot/green-text-generator/frontend/src/App.js
```

### Semantic compression

A lot of current tools are optimized for human readibility rather than token efficiency. In this example, compression brings us from 663 -> 312 tokens

Before:
```
collected 18 tests: 17 failed, 1 passed, 15 warnings

============================= test session starts ==============================
platform darwin -- Python 3.13.3, pytest-8.4.1, pluggy-1.6.0 -- /Users/william/Documents/GitHub/goat-bot/myenv/bin/python
cachedir: .pytest_cache
rootdir: /Users/william/Documents/GitHub/goat-bot/green-text-generator/backend
plugins: anyio-4.9.0
collecting ... collected 18 items

test_step_manager.py::TestStepManager::test_can_advance_to_step_invalid FAILED [  5%]
test_step_manager.py::TestStepManager::test_can_advance_to_step_valid FAILED [ 11%]
test_step_manager.py::TestStepManager::test_get_all_step_statuses FAILED [ 16%]
test_step_manager.py::TestStepManager::test_get_current_step_all_complete FAILED [ 22%]
test_step_manager.py::TestStepManager::test_get_current_step_multiple_complete FAILED [ 27%]
test_step_manager.py::TestStepManager::test_get_current_step_no_project FAILED [ 33%]
test_step_manager.py::TestStepManager::test_get_current_step_upload_complete FAILED [ 38%]
test_step_manager.py::TestStepManager::test_get_image_generation_progress FAILED [ 44%]
test_step_manager.py::TestStepManager::test_get_step_status_completed FAILED [ 50%]
test_step_manager.py::TestStepManager::test_get_step_status_not_started FAILED [ 55%]
test_step_manager.py::TestStepManager::test_get_video_generation_progress FAILED [ 61%]
test_step_manager.py::TestStepManager::test_mark_step_complete_invalid FAILED [ 66%]
test_step_manager.py::TestStepManager::test_mark_step_complete_valid FAILED [ 72%]
test_step_manager.py::TestStepManager::test_step_number_conversion PASSED [ 77%]
test_step_manager.py::TestStepManager::test_validate_image_prompts_completion FAILED [ 83%]
test_step_manager.py::TestStepManager::test_validate_segmentation_completion FAILED [ 88%]
test_step_manager.py::TestStepManager::test_validate_upload_completion FAILED [ 94%]
test_step_manager.py::TestStepManager::test_validate_visual_identity_completion FAILED [100%]
```

After:
```
pytest output (compressed):

Environment: macOS, Python 3.13.3, pytest-8.4.1
rootdir: /Users/william/Documents/GitHub/goat-bot/backend
cachedir: .pytest_cache
collected 18 tests: 17 failed, 1 passed, 15 warnings

Failing tests (all from test_step_manager.py TestStepManager):
- test_can_advance_to_step_invalid
- test_can_advance_to_step_valid
- test_get_all_step_statuses
- test_get_current_step_all_complete
- test_get_current_step_multiple_complete
- test_get_current_step_no_project
- test_get_current_step_upload_complete
- test_get_image_generation_progress
- test_get_step_status_completed
- test_get_step_status_not_started
- test_get_video_generation_progress
- test_mark_step_complete_invalid
- test_mark_step_complete_valid
- test_validate_image_prompts_completion
- test_validate_segmentation_completion
- test_validate_upload_completion
- test_validate_visual_identity_completion

One passing:
- test_step_number_conversion
```