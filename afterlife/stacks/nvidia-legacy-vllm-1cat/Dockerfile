# Afterlife nvidia-legacy-vllm-1cat: 1Cat-vLLM 1.5.2 (cu128, torch 2.10, py3.12) for sm_70. UNBUILT / UNTESTED.
# Separate from ../nvidia-legacy by design. Build locally; do NOT push (contains nvcc, CUDA EULA).
FROM nvidia/cuda:12.8.1-devel-ubuntu24.04@sha256:520292dbb4f755fd360766059e62956e9379485d9e073bbd2f6e3c20c270ed66
ARG WHEEL_URL=https://github.com/1CatAI/1Cat-vLLM/releases/download/v1.5.2/1cat_vllm-1.5.2%2Bcu128-cp312-cp312-linux_x86_64.whl
ARG WHEEL_SHA256=a27afc512cf29d4baa322366f92b32f1d0ddec6d7178b0bf4351ad00c1958baa
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv python3-pip curl ca-certificates ninja-build build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fL -o /tmp/1cat.whl "${WHEEL_URL}" && echo "${WHEEL_SHA256}  /tmp/1cat.whl" | sha256sum -c - \
 && python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir /tmp/1cat.whl && rm /tmp/1cat.whl
ENV PATH=/opt/venv/bin:$PATH
EXPOSE 8000
CMD ["vllm", "--help"]
