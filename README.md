# Manga Conversion Atelier

[日本語](README.ja.md) | **English**

Author: **awasemiso**

Repository: [ScreenmateWorks/manga-conversion-atelier](https://github.com/ScreenmateWorks/manga-conversion-atelier)

## Disk space before installation

Approximate model file sizes for the configuration documented in [AI_INSTALL.md](AI_INSTALL.md):

| Configuration | Model files only |
|---|---:|
| FLUX 3: all four required model files | 17.75 GB (about 16.53 GiB) |
| Stable Diffusion: one checkpoint | 6.94 GB |
| Stable Diffusion: two checkpoints | 13.88 GB |
| Manga Mode LoRA | 0.23 GB |
| Both backends: four FLUX 3 files + two SD checkpoints + LoRA | About 31.9 GB |

**These are sums of the listed model files, not the total disk space required for installation.** FLUX 3 also needs space for ComfyUI, Python, PyTorch, caches and generated images. SD additionally needs the ControlNet and line-art extraction models required by your chosen presets, plus its runtime environment. Using both backends requires space for those additional components as well. SD model requirements vary by preset.

- You only need the backend you want to use; installing both SD and FLUX 3 is optional.
- Existing compatible models and ComfyUI installations may be reused without downloading them again.
- Check available disk space before downloading. Sizes vary by model version and configuration; allow additional space for downloads, caches and outputs.
- GB here means 1,000,000,000 bytes. See [AI_INSTALL.md](AI_INSTALL.md) for the detailed model list and installation instructions.

## Install with Codex or Claude Code

Give your agent this repository URL and ask:

> Install Manga Conversion Atelier from this GitHub repository. Read README and AI_INSTALL.md, inspect the ComfyUI environments already on my PC, and configure the required components. Preserve existing environments and verify startup and image generation. Ask me before large downloads, model license acceptance, or changes to existing environments.

[AI_INSTALL.md](AI_INSTALL.md) provides detailed instructions in Japanese. Users obtain models under each distributor's terms. Automated installation is not guaranteed. Enable only the backend you need.

A personal, free Windows tool created for the author's own manga production because existing conversion tools did not produce the desired finish. It uses local ComfyUI, Stable Diffusion and FLUX 3 for grayscale manga, black ink, and line-art conversion. The Japanese UI shows the input on the left and output on the right. It includes 20 text-only base presets, detailed controls, custom preset creation/deletion, and hide/show controls for undeletable base presets. Supported models accept additional free-text image descriptions and finishing instructions alongside the preset's instructions. Images are processed locally and can be saved as PNG.

## Conversion example

<!-- DEMO_START -->
![Color original, manga rendering with A15, and black ink with F3-14](docs/images/manga-comparison.webp)
<!-- DEMO_END -->

Left to right: color original, manga (A15), black ink (F3-14). Both outputs were independently converted from the same color original, not produced as a three-step chain. Examples provided by awasemiso and published with permission. Open the image to inspect details.

The manually attached Release ZIP contains no images. The GitHub repository and automatically generated source archives include this one README comparison image. No other personal originals, generation history, logs or credentials are included.

Create `.venv`, install `requirements.txt`, and configure `config.local.json` as described in AI_INSTALL.md. Double-click `start.bat`; the default URL is `http://127.0.0.1:8971/`. ComfyUI, models, LoRAs and external custom nodes are not included. One configured backend is enough. No paid generation API is used.

The source workflows were used on the author's Windows 11 laptop (RTX 5060 Laptop 8GB, 32GB RAM). Public-package startup, configuration and UI management were checked there; all presets were not regenerated for this package. Other computers are untested. Results vary with the input. There is no warranty, installation support commitment, or response guarantee. GitHub Issues are optional once the repository is published.

Original code is under the [MIT License](LICENSE), including commercial use, modification and redistribution. External components and models retain their own terms; MIT does not grant rights to those models or their outputs. See [THIRD_PARTY.md](THIRD_PARTY.md).

Do not redistribute your `config.local.json`, `runtime/`, `出力/`, `記録/` or `自分のプリセット/` folders. They may contain private images, prompts, paths and browser data.
