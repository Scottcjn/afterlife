# Disclaimer

Afterlife is a maintenance and packaging project. It pins community-maintained software
stacks (drivers, toolkits, frameworks, forks) that still work on GPUs their vendors have
stopped supporting, and adds a diagnostic (`afterlife doctor`) and a fixed-methodology
benchmark runner (`afterlife bench`).

- It is not new kernels or a new inference engine. The speed comes from upstream work (see NOTICE).
- Proxies are labeled as proxies. A GTX 1060 stands in for a Tesla P40 (Pascal); it is not one.
  The MI50 in our lab runs as a 16 GB board.
- Numbers from the Elyan Labs lab that are not yet reproduced by a published receipt are
  unpublished lab measurements, not verified results.
- Gemma 4 26B A4B is a mixture-of-experts model with about 4B active parameters; its tok/s is not
  comparable to a dense 26B.
- Pinned stacks are old by design and will stop receiving vendor security fixes. Use on
  isolated or trusted machines.
- No warranty. Provided "as is" under the Apache-2.0 license; use at your own risk. Driver and
  firmware changes can brick or destabilize hardware.
- Not affiliated with NVIDIA, AMD, or the upstream projects credited in NOTICE.
