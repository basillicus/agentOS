#!/bin/bash
set -e

# Default settings
export OLLAMA_HOST=${OLLAMA_HOST:-"127.0.0.1:11434"}
export AGENT_MODEL=${AGENT_MODEL:-"granite4"}

# Function to handle shutdown
cleanup() {
    # Only try to kill if we started it
    if [ ! -z "$OLLAMA_PID" ]; then
        echo "Stopping background services..."
        kill $OLLAMA_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ==========================================
# 1. SETUP MODEL PATHS
# ==========================================
# If OLLAMA_MODELS is not set, or points to /root (read-only for us), find a better place.
if [[ -z "$OLLAMA_MODELS" ]] || [[ "$OLLAMA_MODELS" == *"/root/"* && "$(id -u)" -ne 0 ]]; then
    # Priority 1: The /opt location (if baked into the image)
    if [ -d "/opt/ollama/models" ] && [ -r "/opt/ollama/models" ]; then
        export OLLAMA_MODELS="/opt/ollama/models"
    # Priority 2: A writable /data volume (if bound)
    elif [ -d "/data" ] && [ -w "/data" ]; then
        export OLLAMA_MODELS="/data/ollama/models"
    # Priority 3: User's home directory
    else
        export OLLAMA_MODELS="$HOME/.ollama/models"
    fi
fi
# Ensure the directory exists (if we have permission)
mkdir -p "$OLLAMA_MODELS" 2>/dev/null || true


# ==========================================
# 2. START OLLAMA (If applicable)
# ==========================================
# We only start Ollama if:
# a) The user hasn't specified an external host
# b) We actually HAVE the ollama binary installed
if [[ "$OLLAMA_HOST" == *"127.0.0.1"* || "$OLLAMA_HOST" == *"localhost"* ]]; then
    
    if command -v ollama >/dev/null 2>&1; then
        echo " [AgentOS] Starting internal Ollama server..."
        echo " [AgentOS] Models Directory: ${OLLAMA_MODELS}"
        
        ollama serve > /dev/null 2>&1 &
        OLLAMA_PID=$!

        # Wait for Ollama to wake up
        echo " [AgentOS] Waiting for Ollama API..."
        MAX_RETRIES=30
        COUNT=0
        while ! curl -s http://127.0.0.1:11434/api/tags > /dev/null; do
            if ! kill -0 $OLLAMA_PID 2>/dev/null; then
                echo " [AgentOS] ERROR: Internal Ollama server died unexpectedly."
                echo " [AgentOS] Check if port 11434 is in use or if OLLAMA_MODELS is writable."
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

        # Check/Pull Model
        echo " [AgentOS] Checking for model: $AGENT_MODEL"
        if ! ollama list | grep -q "$AGENT_MODEL"; then
            echo " [AgentOS] Model '$AGENT_MODEL' not found locally."
            echo " [AgentOS] Attempting to pull... (Requires Internet)"
            if ollama pull "$AGENT_MODEL"; then
                echo " [AgentOS] Model pulled successfully."
            else
                echo " [AgentOS] WARNING: Failed to pull model. Agent functionality might fail."
            fi
        else
            echo " [AgentOS] Model found."
        fi
        
    else
        echo " [AgentOS] NOTICE: 'ollama' binary not found (Lite Flavor?)."
        echo " [AgentOS] Assuming you have an external Ollama server."
        # If we are lite, we expect the user might have port forwarded or bound something,
        # but if OLLAMA_HOST is still localhost, the agent will likely fail unless 
        # the host machine is listening on localhost and we share the network (which Apptainer does).
    fi
else
    echo " [AgentOS] Using external Ollama at $OLLAMA_HOST"
fi

# ==========================================
# 3. LAUNCH AGENT
# ==========================================
echo " [AgentOS] Launching Interface..."
echo "------------------------------------------------"
python3 /app/agentOS/agent.py "$@"