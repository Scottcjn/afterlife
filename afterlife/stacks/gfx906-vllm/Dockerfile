# Afterlife gfx906-vllm: build ai-infos/vllm-gfx906-mobydick from source with its own script. UNBUILT / UNTESTED.
# This is a thin wrapper: the upstream script builds the image. Run on a host with docker; it does not run inside docker build.
# See install.sh. To just PULL upstream's image instead (pinned by digest):
#   docker pull aiinfos/vllm-gfx906-mobydick@sha256:b7f62e582dcbf3e2d333925f6d325e0a521dca8778fdfd76b284e5ff8244f27c
#
# Run (upstream pattern, trimmed of --privileged/--pid=host):
#   docker run --rm -it --device=/dev/kfd --device=/dev/dri --group-add video --group-add render --ipc=host -p 127.0.0.1:8000:8000 \
#     -v $HOME/.cache/huggingface:/root/.cache/huggingface <image> vllm serve <model> --dtype float16
FROM aiinfos/vllm-gfx906-mobydick@sha256:b7f62e582dcbf3e2d333925f6d325e0a521dca8778fdfd76b284e5ff8244f27c
LABEL org.afterlife.stack="gfx906-vllm" org.afterlife.status="untested"
