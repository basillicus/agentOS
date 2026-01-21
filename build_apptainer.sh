#!/bin/bash
set -e

IMAGE_NAME="agentOS.sif"
DEF_FILE="agentOS.def"

echo "Building Apptainer image: $IMAGE_NAME from $DEF_FILE"

# Check if apptainer is installed
if ! command -v apptainer &> /dev/null; then
    echo "Error: apptainer could not be found."
    echo "Please install Apptainer to build the image."
    exit 1
fi

# Build the image
# --force overwrites existing image
apptainer build --fakeroot --force "$IMAGE_NAME" "$DEF_FILE"

echo "Build complete: $IMAGE_NAME"
echo "To run: ./$IMAGE_NAME"
