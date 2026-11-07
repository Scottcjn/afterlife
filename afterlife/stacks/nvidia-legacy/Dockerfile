# Afterlife nvidia-legacy: CUDA 12.9.1 + torch 2.14.0(cu126) + llama.cpp b12182 for sm_70;61
# UNBUILT / UNTESTED recipe (2026-11-06). Build locally; do NOT push the result (CUDA EULA: see stack.yaml).
# Host needs NVIDIA R580 driver + nvidia-container-toolkit. Driver is never baked in.
#   docker build -t afterlife/nvidia-legacy:local -f Dockerfile .
#   docker run --rm --gpus all afterlife/nvidia-legacy:local python3 -c "import torch;print(torch.cuda.get_device_capability(0))"
FROM nvidia/cuda:12.9.1-devel-ubuntu24.04@sha256:020bc241a628776338f4d4053fed4c38f6f7f3d7eb5919fecb8de313bb8ba47c
ARG LLAMA_REPO=https://github.com/ggml-org/llama.cpp.git
ARG LLAMA_COMMIT=fd27b2034905f8dadd8bd6d2cc44595f4929d391
ARG CUDA_ARCHS="70;61"
ARG TORCH_VERSION=2.14.0
ARG TORCHVISION_VERSION=0.29.0
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      git cmake ninja-build build-essential python3 python3-venv python3-pip ca-certificates curl libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*
RUN git clone ${LLAMA_REPO} /src/llama.cpp && cd /src/llama.cpp && git checkout ${LLAMA_COMMIT} \
 && cmake -S . -B build -G Ninja -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHS}" -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build -j"$(nproc)" \
 && cmake --install build --prefix /usr/local
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir \
      torch==${TORCH_VERSION} torchvision==${TORCHVISION_VERSION} --index-url https://download.pytorch.org/whl/cu126
ENV PATH=/opt/venv/bin:$PATH LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
CMD ["bash"]
