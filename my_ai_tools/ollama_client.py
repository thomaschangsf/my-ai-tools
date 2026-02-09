"""Connect to local Ollama via HTTP.

Ollama runs at http://localhost:11434 by default. Use the official
ollama package from PyPI (already a dependency) in your code:

    from ollama import Client

    client = Client(host="http://localhost:11434")
    response = client.chat(model="llama2", messages=[...])
"""

from ollama import Client

# Default client for local Ollama (http://localhost:11434)
DEFAULT_HOST = "http://localhost:11434"


def get_client(host: str = DEFAULT_HOST) -> Client:
    """Return an Ollama client connected to the given host."""
    return Client(host=host)
