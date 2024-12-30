#!/bin/bash

# Check for minimum number of required arguments
if [ $# -lt 4 ]; then
    echo "Usage: $0 docker_image head_node_address --head|--worker path_to_hf_home [additional_args...]"
    exit 1
fi

# Assign the first three arguments and shift them away
DOCKER_IMAGE="$1"
HEAD_NODE_ADDRESS="$2"
NODE_TYPE="$3"  # Should be --head or --worker
PATH_TO_HF_HOME="$4"
shift 4

# Additional arguments are passed directly to the Docker command
ADDITIONAL_ARGS=("$@")

# Validate node type
if [ "${NODE_TYPE}" != "--head" ] && [ "${NODE_TYPE}" != "--worker" ]; then
    echo "Error: Node type must be --head or --worker"
    exit 1
fi

IMAGE_ID=$(docker images -q "${DOCKER_IMAGE}")
if [ -z "$IMAGE_ID" ]; then
    echo "[run_cluster.sh] Docker image '${DOCKER_IMAGE}' does NOT exist. Building..."
    # 컨텍스트를 어디서 빌드할지 주의! 
    # 예: 이 스크립트가 레포지토리 루트에서 실행된다고 가정하여 '.'을 컨텍스트로 사용
    docker build -t "${DOCKER_IMAGE}" .
else
    echo "[run_cluster.sh] Docker image '${DOCKER_IMAGE}' found (ID: $IMAGE_ID). Skip building."
fi

# Command setup for head or worker node
RAY_START_CMD="ray start --block"
if [ "${NODE_TYPE}" == "--head" ]; then
    RAY_START_CMD+=" --head --port=6379"
else
    RAY_START_CMD+=" --address=${HEAD_NODE_ADDRESS}:6379"
fi

cleanup() {
    docker stop node >/dev/null 2>&1 || true
    docker rm node >/dev/null 2>&1 || true
}
cleanup

# Run the docker command with the user specified parameters and additional arguments
docker run  -d \
    --network host \
    --name node \
    --shm-size 10.24g \
    --gpus all \
    -v "${PATH_TO_HF_HOME}:/root/.cache/huggingface" \
    "${ADDITIONAL_ARGS[@]}" \
    "${DOCKER_IMAGE}" -c "${RAY_START_CMD}"
