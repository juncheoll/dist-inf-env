# dist-inf-env

### Docker 빌드
```bash
docker build -t vllm-env:latest .
```

### Docker 컨테이너 실행
```bash
docker bash run_cluster.sh vllm-env:latest 192.168.79.18 --head ~/.cache/huggingface -e NCCL_SOCKET_IFNAME=enp7s0 -e GLOO_SOCKET_IFNAME=enp7s0
```