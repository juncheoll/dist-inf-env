# dist-inf-env

### Docker 빌드
```bash
docker build -t vllm-env:lates .
```

### Docker 컨테이너 실행
```bash
docker run --gpus all -it vllm-env:latest /bin/bash
```