#!/bin/bash
set -e

FLAVOR=${1:-"standard"}
IMAGE_NAME="agentOS-${FLAVOR}.sif"
DEF_FILE="agentOS.def"

echo "Building Apptainer image ($FLAVOR): $IMAGE_NAME"

ARGS=""

if [ "$FLAVOR" == "lite" ]; then
    echo " -> Config: No Ollama, No Models."
    ARGS="--build-arg INSTALL_OLLAMA=false"
    
elif [ "$FLAVOR" == "standard" ]; then
    echo " -> Config: Ollama Included, Download models at runtime."
    ARGS="--build-arg INSTALL_OLLAMA=true --build-arg PRELOAD_MODEL=false"
    
elif [ "$FLAVOR" == "full" ]; then
    echo " -> Config: All-in-one (Ollama + Granite4 Model baked in)."
    ARGS="--build-arg INSTALL_OLLAMA=true --build-arg PRELOAD_MODEL=true"
    
else
    echo "Error: Unknown flavor '$FLAVOR'. Use: lite, standard, full"
    exit 1
fi

# Check for apptainer
if ! command -v apptainer &> /dev/null; then
    echo "Error: apptainer not found."
    exit 1
fi

# Build
echo "Running: apptainer build --fakeroot $ARGS $IMAGE_NAME $DEF_FILE"
apptainer build --fakeroot --force $ARGS "$IMAGE_NAME" "$DEF_FILE"

echo "Build complete: $IMAGE_NAME"