# 外部依存とライセンス

この配布物にはPythonパッケージ、ComfyUI、AIモデル、LoRA、外部カスタムノード、公式テンプレート本文を同梱していません。配布内のHTTP UI、実行アダプター、プリセット構成、補助コードは本プロジェクトのコードです。

`app/adapters/mono_local` は本プロジェクトの薄い接続・仕上げ処理です。線画検出ネットワークの実装や重みは含まず、利用者が別途導入したライブラリを呼び出します。外部実装をMITへ変更して配布するものではありません。ノードAPIを指定するJSONは、外部ノードのソースコードを含みません。

| 外部依存 | 案内・利用条件 |
|---|---|
| ComfyUI | [公式リポジトリ](https://github.com/Comfy-Org/ComfyUI) / [GPL-3.0](https://github.com/Comfy-Org/ComfyUI/blob/master/LICENSE) |
| comfyui_controlnet_aux | [公式](https://github.com/Fannovel16/comfyui_controlnet_aux) / [Apache-2.0](https://github.com/Fannovel16/comfyui_controlnet_aux/blob/main/LICENSE.txt)。内部で使用する各実装・重みの条件も確認してください |
| FLUX 3 Image Klein本体（画像生成モデル） | [FLUX Kommunity License](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/blob/main/LICENSE.md)。MITやApache-2.0ではありません |
| Qwen3-VL-4B-Instructテキストエンコーダー（本構成ではINT8版） | Apache-2.0。[BFLが案内するテキストエンコーダーのLICENSE](https://huggingface.co/black-forest-labs/flux-3-image-klein/blob/main/text_encoder/LICENSE) / [Qwen公式配布](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) |
| 公式プロンプト拡張モデル（Qwen3.5 9B、本構成ではW4A8版） | Apache-2.0。[BFL公式プロンプト拡張モデル配布元](https://huggingface.co/black-forest-labs/flux-3-image-klein-pup) |
| FLUX.2 VAE、公式ワークフロー／テンプレート、その他の関連ファイル | [公式配布元の各ファイル・利用条件](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy) を個別に確認してください。上記3モデルのライセンスを一律に適用するものではありません |
| GS BEYOND THE DRAWING ANIME v1.0 | [作者配布ページ](https://civitai.com/models/2455018?modelVersionId=2760456) の利用条件 |
| Nova Anime XL IL v16.0 | [作者配布ページ](https://civitai.com/models/376130) の該当版の利用条件 |
| Manga Mode [Illustrious] / dreamerdragon | [作者配布ページ](https://civitai.com/models/1255751?modelVersionId=1415781) の利用条件。クレジット・商用利用・派生について条件があります。商用画像販売を一律許可するものとして扱わないでください |
| SDXL Union ControlNet ProMax | [xinsir配布ページ](https://huggingface.co/xinsir/controlnet-union-sdxl-1.0) のProMax版の利用条件 |
| erika.pth / Manga Lineart | [Annotators配布元](https://huggingface.co/lllyasviel/Annotators/blob/main/erika.pth) と [使用実装](https://github.com/Fannovel16/comfyui_controlnet_aux/tree/main/src/custom_controlnet_aux/manga_line) を確認してください |
| requests / aiohttp / psutil / Pillow | pipで別途導入。各配布パッケージのLICENSEを適用。Python本体とComfyUIの依存パッケージも同様です |

FLUX 3本体・テキストエンコーダー・プロンプト拡張モデルの区別は、[BFL公式モデルカードのLicense節](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy#license) に基づきます。同じ配布リポジトリにあることは、全ファイルが同じライセンスであることを意味しません。

本ツールのライセンスと、外部モデルの利用条件は別です。取得・利用・商用利用の可否は、実際に使用する版の配布元で確認してください。外部コードを改造して再配布に追加する場合は、そのライセンス表示・ソース提供等の義務を別途確認してください。
