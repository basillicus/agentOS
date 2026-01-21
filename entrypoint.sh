#!/bin/bash
set -e

# Default settings
export OLLAMA_HOST=${OLLAMA_HOST:-"127.0.0.1:11434"}
export AGENT_MODEL=${AGENT_MODEL:-"granite4"}

# Function to handle shutdown
cleanup() {
    echo "Stopping background services..."
    if [ ! -z "$OLLAMA_PID" ]; then
        kill $OLLAMA_PID
    fi
}
trap cleanup EXIT

# 1. Start Internal Ollama Server if we are using the local default
#    (We check if OLLAMA_HOST is pointing to localhost)
if [[ "$OLLAMA_HOST" == *"127.0.0.1"* || "$OLLAMA_HOST" == *"localhost"* ]]; then
    echo " [AgentOS] Starting internal Ollama server..."
    ollama serve &
    OLLAMA_PID=$!

    # Wait for Ollama to wake up
    echo " [AgentOS] Waiting for Ollama API..."
    until curl -s http://127.0.0.1:11434/api/tags > /dev/null; do
        sleep 1
    done
    echo " [AgentOS] Ollama is ready."

    # 2. Check/Pull Model
    #    We check if the model is available locally. If not, we try to pull it.
    #    Note: This requires internet access inside the container or a pre-populated volume.
    echo " [AgentOS] Checking for model: $AGENT_MODEL"
    if ! ollama list | grep -q "$AGENT_MODEL"; then
        echo " [AgentOS] Model not found. Attempting to pull '$AGENT_MODEL'..."
        echo " [AgentOS] (This requires internet access. If offline, bind-mount ~/.ollama)"
        if ollama pull "$AGENT_MODEL"; then
            echo " [AgentOS] Model pulled successfully."
        else
            echo " [AgentOS] ERROR: Failed to pull model. Check internet connection or usage."
            # We don't exit here, because maybe the user wants to use tool mode only.
        fi
    else
        echo " [AgentOS] Model found."
    fi
else
    echo " [AgentOS] Using external Ollama at $OLLAMA_HOST"
fi

# 3. Run AgentOS
echo " [AgentOS] Launching Interface..."
echo "------------------------------------------------"
# Pass all arguments to the agent
python3 /app/agentOS/agent.py "$@"
