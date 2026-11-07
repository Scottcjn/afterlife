# Afterlife control-sm86: CUDA 13.4.3 + torch 2.15.0 (PyPI) + llama.cpp b12182 for sm_86. UNBUILT / UNTESTED. Build locally; do not push.
FROM nvidia/cuda:13.4.3-devel-ubuntu24.04@sha256:5626a7d0ecafe3e7c115a452f6b05f20f214f8509346196a7835b205dc5b7fd9
ARG LLAMA_COMMIT=fd27b2034905f8dadd8bd6d2cc44595f4929d391
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends git cmake ninja-build build-essential python3 python3-venv python3-pip ca-certificates libcurl4-openssl-dev && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/ggml-org/llama.cpp.git /src/llama.cpp && cd /src/llama.cpp && git checkout ${LLAMA_COMMIT} \
 && cmake -S . -B build -G Ninja -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build -j"$(nproc)" && cmake --install build --prefix /usr/local
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir torch==2.15.0
ENV PATH=/opt/venv/bin:$PATH
