# Dockerfile
FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu24.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    PATH="/root/.local/bin:$PATH"

# Install system dependencies
RUN apt-get update && \
    apt-get install -y  \
        git \
        rsync \
        python3 \
        python3-pip \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Clone the vllm project
WORKDIR /
COPY . ./dist-inf-env

#RUN pip install vllm==0.6.6 --break-system-packages
RUN pip install vllm --break-system-packages
RUN pip install bitsandbytes>=0.45.0 --break-system-packages
RUN pip install python-json-logger --break-system-packages
RUN pip install pyarrow --break-system-packages

RUN chmod +x /dist-inf-env/entrypoint.sh

#ENTRYPOINT ["/dist-inf-env/entrypoint.sh"]
