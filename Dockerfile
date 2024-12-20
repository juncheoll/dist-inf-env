# Dockerfile
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    VLLM_USE_PRECOMPILED=1 \
    PATH="/root/.local/bin:$PATH"

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Clone the vllm project
WORKDIR /
RUN git clone https://github.com/vllm-project/vllm.git .

# Set up virtual environment and install vllm
WORKDIR /vllm
RUN python3 -m venv myenv && \
    source myenv/bin/activate && \
    pip install --upgrade pip && \
    pip install --editable .

# Set the default shell to bash
SHELL ["/bin/bash", "-c"]

# Default command
CMD ["bash", "-c", "source /vllm/myenv/bin/activate && cd /vllm && pip install --editable . && exec bash"]
