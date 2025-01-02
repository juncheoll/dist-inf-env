#!/usr/bin/env bash
set -e

echo "[entrypoint.sh] Container started..."

# 1) pip show vllm을 통해 site-packages 위치를 알아냄
LOCATION=$(pip show vllm | grep '^Location:' | awk '{print $2}')
echo "[entrypoint.sh] vllm is installed at: $LOCATION"

# 2) 수정된 /vllm 폴더에서 변경 사항을 dist-packages/vllm에 덮어쓰기
if [ -d "/vllm" ]; then
    echo "[entrypoint.sh] Syncing changes from /vllm to $LOCATION/vllm..."
    
    # dist-packages 경로가 없으면 경고 출력 후 종료
    if [ ! -d "$LOCATION/vllm" ]; then
        echo "[entrypoint.sh] ERROR: $LOCATION/vllm does not exist. Cannot sync changes."
        exit 1
    fi

    # rsync를 사용하여 /vllm 내용을 $LOCATION/vllm에 덮어쓰기
    rsync -av --exclude='*.pyc' --exclude='__pycache__' /vllm/vllm "$LOCATION/vllm/"

    echo "[entrypoint.sh] Sync completed: /vllm -> $LOCATION/vllm"
else
    echo "[entrypoint.sh] WARNING: /vllm does not exist. Nothing to sync."
fi


# 3) 추가적으로, 컨테이너 내에서 실행할 명령이 있다면 여기서 실행
python3 -c "import vllm; print('VLLM imported!')"