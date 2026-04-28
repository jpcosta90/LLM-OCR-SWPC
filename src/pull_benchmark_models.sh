#!/bin/bash

# List of models to pull for the Impossible Triangle benchmark (< 15B)
MODELS=(
    "moondream"
    "qwen2-vl:2b"
    "qwen2-vl:7b"
    "blaifa/internvl2:2b"
    "blaifa/internvl2:4b"
    "blaifa/internvl2:8b"
    "llava:7b"
    "llava:13b"
    "llama3.2-vision:11b"
    "erwan2/Janus-1.3B"
    "deepseek-janus:7b"
)

echo "Starting bulk pull of 11 multimodal models..."

for model in "${MODELS[@]}"; do
    echo "------------------------------------------------"
    echo "Pulling: $model"
    # Use the remote API if possible, otherwise local command
    # Assuming local command works since we are on the instance
    ollama pull "$model"
done

echo "------------------------------------------------"
echo "All models pulled successfully!"
