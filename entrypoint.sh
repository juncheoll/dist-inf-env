#!/usr/bin/env bash
set -e

echo "[entrypoint.sh] Container started..."

# 1) pip show vllm을 통해 site-packages 위치를 알아냄
LOCATION=$(pip show vllm | grep '^Location:' | awk '{print $2}')
echo "[entrypoint.sh] vllm is installed at: $LOCATION"

# 2) 만약 기존 site-packages 안에 vllm 폴더가 이미 있다면 제거 (선택적)
if [ -d "$LOCATION/vllm" ]; then
    echo "[entrypoint.sh] Removing existing $LOCATION/vllm ..."
    rm -rf "$LOCATION/vllm"
fi

# 3) 호스트에서 마운트된 /vllm(또는 다른 경로)에 소스코드로 precompiled build
#    이를 site-packages 로 복사
if [ -d "/vllm" ]; then
    echo "[entrypoint.sh] Precompiled Building /vllm"
    VLLM_USE_PRECOMPILED=1 pip install -e . --break-system-packages
else
    echo "[entrypoint.sh] WARNING: /vllm does not exist. Nothing to copy."
fi

# 4) 추가적으로, 컨테이너 내에서 실행할 명령이 있다면 여기서 실행
python3 -c "import vllm; print('VLLM imported!')"

echo "[entrypoint.sh] Done copying. Now executing CMD..."
exec "$@"
