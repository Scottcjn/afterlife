# Afterlife gfx906: TheRock 7.14.0-gfx906 (mixa3607 apt) + llama.cpp HIP (gfx906) + Vulkan baseline binary. UNBUILT / UNTESTED.
# Mirrors mixa3607/ML-gfx906 rocm/build-image.Dockerfile but builds from ubuntu:24.04 so we depend on packages, not their image.
#   docker build -t afterlife/gfx906:local .
#   docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video --group-add render afterlife/gfx906:local rocminfo
FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
ARG ROCM_BUILD=7.14.0-gfx906+20261018172427
ARG LLAMA_COMMIT=fd27b2034905f8dadd8bd6d2cc44595f4929d391
ENV DEBIAN_FRONTEND=noninteractive ROCM_PATH=/opt/rocm PATH=/opt/rocm/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl git build-essential cmake ninja-build libssl-dev \
      libvulkan-dev glslc mesa-vulkan-drivers vulkan-tools \
 && install -m 0755 -d /etc/apt/keyrings \
 && curl -fsSL https://s3.arkprojects.space/apt-gfx906/ubuntu/gpg -o /etc/apt/keyrings/apt-gfx906.asc \
 && printf 'Types: deb\nURIs: https://s3.arkprojects.space/apt-gfx906/ubuntu\nSuites: noble\nComponents: main\nArchitectures: amd64\nSigned-By: /etc/apt/keyrings/apt-gfx906.asc\n' > /etc/apt/sources.list.d/gfx906.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends amdrocm7.14=${ROCM_BUILD} amdrocm-core-sdk7.14=${ROCM_BUILD} amdrocm7.14-gfx906=${ROCM_BUILD} amdrocm-core-sdk7.14-gfx906=${ROCM_BUILD} \
 && echo "/opt/rocm/lib" > /etc/ld.so.conf.d/rocm.conf && ldconfig && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/ggml-org/llama.cpp.git /src/llama.cpp && cd /src/llama.cpp && git checkout ${LLAMA_COMMIT} \
 && HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" cmake -S . -B build-hip -G Ninja -DGGML_HIP=ON -DGPU_TARGETS=gfx906 -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build-hip -j"$(nproc)" \
 && cmake -S . -B build-vulkan -G Ninja -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release && cmake --build build-vulkan -j"$(nproc)"
ENV PATH=/src/llama.cpp/build-hip/bin:$PATH
# Vulkan binaries live in /src/llama.cpp/build-vulkan/bin
CMD ["bash"]
