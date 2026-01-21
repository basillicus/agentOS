#!/bin/bash
set -e

# Default settings
export OLLAMA_HOST=${OLLAMA_HOST:-"127.0.0.1:11434"}
export AGENT_MODEL=${AGENT_MODEL:-"granite4"}

# Function to handle shutdown
cleanup() {
    echo "Stopping background services..."
    if [ ! -z "$OLLAMA_PID" ]; then
        kill $OLLAMA_PID 2>/dev/null
    fi
}
trap cleanup EXIT

# FIX: Apptainer runs as user, but default env points to /root (read-only)
# If OLLAMA_MODELS is in /root and we are not root, redirect to a writable path.
if [[ "$OLLAMA_MODELS" == *"/root/"* ]] && [ "$(id -u)" -ne 0 ]; then
    if [ -d "/data" ] && [ -w "/data" ]; then
        export OLLAMA_MODELS="/data/ollama/models"
    else
        export OLLAMA_MODELS="$HOME/.ollama/models"
    fi
    # Ensure it exists
    mkdir -p "$OLLAMA_MODELS"
fi

# 1. Start Internal Ollama Server if we are using the local default
#    (We check if OLLAMA_HOST is pointing to localhost)
if [[ "$OLLAMA_HOST" == *"127.0.0.1"* || "$OLLAMA_HOST" == *"localhost"* ]]; then
    echo " [AgentOS] Starting internal Ollama server..."
    echo " [AgentOS] Models Directory: ${OLLAMA_MODELS:-'(Default)'}"
    
    ollama serve > /dev/null 2>&1 &
    OLLAMA_PID=$!

    # Wait for Ollama to wake up
    echo " [AgentOS] Waiting for Ollama API..."
    MAX_RETRIES=30
    COUNT=0
    while ! curl -s http://127.0.0.1:11434/api/tags > /dev/null; do
        if ! kill -0 $OLLAMA_PID 2>/dev/null; then
            echo " [AgentOS] ERROR: Internal Ollama server died unexpectedly."
            echo " [AgentOS] Check permissions on your bind mounts or if port 11434 is in use."
            exit 1
        fi
        sleep 1
        COUNT=$((COUNT+1))
        if [ $COUNT -ge $MAX_RETRIES ]; then
             echo " [AgentOS] ERROR: Timed out waiting for Ollama API."
             exit 1
        fi
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
