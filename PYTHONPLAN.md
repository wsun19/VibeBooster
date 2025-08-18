# Plan for Python-based Anthropic Proxy

## 1. Background and Rationale

This document outlines a plan to create a Python version of the existing Go-based Anthropic proxy. The Go proxy intercepts requests to the Anthropic API, modifies them, and then forwards them. The purpose of this project is to replicate this functionality in Python, providing a more accessible and potentially easier-to-extend solution for developers familiar with the Python ecosystem.

The Python version will serve as a reference implementation and a starting point for more complex modifications and features. This plan is designed to be handed off to a coding agent for implementation.

## 2. Core Requirements

The Python proxy must meet the following requirements:

1.  **Act as a proxy for the Anthropic Messages API:** It should have an endpoint that mimics the real Anthropic API (e.g., `/v1/messages`).
2.  **Intercept and modify requests:** It must be able to parse the incoming JSON request, modify its content, and then forward the modified request.
3.  **Forward requests to the Anthropic API:** It should correctly forward the (potentially modified) request to the actual Anthropic API.
4.  **Handle both streaming and non-streaming responses:** It must be able to handle both standard and streaming responses from the Anthropic API and pass them back to the original client.
5.  **Be configurable:** Key settings, such as the Anthropic API key and API URL, should be configurable via environment variables.
6.  **Include basic logging:** It should log basic information about requests and responses.

## 3. Technology Stack

The following Python libraries are recommended:

*   **FastAPI:** A modern, fast (high-performance) web framework for building APIs. Its dependency injection system and automatic documentation make it a good choice for this project.
*   **HTTPX:** A fully featured HTTP client for Python 3, which provides sync and async APIs and support for both HTTP/1.1 and HTTP/2. It's ideal for forwarding requests to the Anthropic API.
*   **Uvicorn:** An ASGI server implementation, used to run the FastAPI application.

## 4. Incremental Development Plan

The application should be built in the following incremental steps. Each step results in a testable piece of functionality.

### Step 1: Basic Proxy (No Modification)

**Goal:** Create a basic FastAPI server that forwards requests to the Anthropic API without any modification.

**Implementation:**

1.  Create a new directory for the Python project (e.g., `claude-proxy-py`).
2.  Set up a virtual environment and install `fastapi`, `uvicorn`, and `httpx`.
3.  Create a `main.py` file.
4.  In `main.py`, create a FastAPI application.
5.  Create a `/v1/messages` endpoint that accepts `POST` requests.
6.  In this endpoint, use `httpx` to forward the request to the Anthropic API.
7.  Return the response from the Anthropic API to the client.
8.  Hardcode the Anthropic API key and URL for now.

**Testing:**

Use `curl` to send a request to the proxy. Verify that you get a valid response from Anthropic.

```bash
curl -X POST http://127.0.0.1:8000/v1/messages \
-H "Content-Type: application/json" \
-d '{
    "model": "claude-3-opus-20240229",
    "max_tokens": 25,
    "messages": [
        {"role": "user", "content": "Hello, world"}
    ]
}'
```

### Step 2: Implement Request Modification

**Goal:** Add the logic to intercept and modify the request body.

**Implementation:**

1.  In the `/v1/messages` endpoint, before forwarding the request, parse the JSON body.
2.  Add the logic to append a string to the `content` of the last message in the `messages` array.
3.  Handle both simple string content and the array of content blocks format.
4.  Forward the *modified* request to the Anthropic API.

**Testing:**

Send the same `curl` request as in Step 1. The response from Anthropic should now be modified. For example, if the appended string is " and say moo", the response should be something like "Hello, world! moo".

### Step 3: Add Streaming Support

**Goal:** Implement handling for streaming responses.

**Implementation:**

1.  In the `/v1/messages` endpoint, check if the `stream` parameter in the request body is set to `true`.
2.  If `stream` is `true`, use `httpx`'s streaming support (`client.stream`) to forward the request.
3.  Use FastAPI's `StreamingResponse` to stream the response back to the client.

**Testing:**

Send a `curl` request with `"stream": true`.

```bash
curl -X POST http://127.0.0.1:8000/v1/messages \
-H "Content-Type: application/json" \
-d '{
    "model": "claude-3-opus-20240229",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "Hello, world"}
    ],
    "stream": true
}'
```

You should see a stream of server-sent events (SSEs) in the response.

### Step 4: Configuration and Environment Variables

**Goal:** Move hardcoded values to a configuration file or environment variables.

**Implementation:**

1.  Create a `config.py` file.
2.  In `config.py`, use the `os` module to read the `ANTHROPIC_API_KEY` and `ANTHROPIC_API_URL` from environment variables.
3.  In `main.py`, import these values from `config.py` and use them.

**Testing:**

Set the environment variables and run the application.

```bash
export ANTHROPIC_API_KEY="your-api-key"
python main.py
```

The application should work as before.

### Step 5: Add Logging

**Goal:** Implement logging to record requests and responses.

**Implementation:**

1.  Use Python's built-in `logging` module.
2.  Configure a basic logger to print to the console.
3.  Log the incoming request (method, path, headers).
4.  Log the modified request body.
5.  Log the response from Anthropic (status code, headers).

**Testing:**

Run the application and send requests. You should see log messages in the console.

### Step 6 (Optional but Recommended): Add a Storage Layer

**Goal:** Outline how to add a simple SQLite database to log requests, similar to the Go version.

**Implementation:**

1.  Add `sqlalchemy` to the `requirements.txt`.
2.  Define a simple data model for requests and responses.
3.  Use SQLAlchemy to create a SQLite database and tables.
4.  In the `/v1/messages` endpoint, after receiving a request and before forwarding it, save the request to the database.
5.  After receiving the response, update the database record with the response data.

**Testing:**

Send requests to the proxy. Then, use a SQLite client to inspect the database and verify that the requests and responses are being logged correctly.

## 5. Final Code Structure

The final project structure should look something like this:

```
claude-proxy-py/
├── main.py
├── config.py
├── requirements.txt
└── database.py  # For Step 6
```
