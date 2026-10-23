# Manga Conversion Atelier

Author: **awasemiso** (name used on X).

Repository: [ScreenmateWorks/manga-conversion-atelier](https://github.com/ScreenmateWorks/manga-conversion-atelier)

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
