# AI向け導入手順（Windows、手動設定）

このファイルはCodex・Claude Codeと、人が導入するための手順です。インストーラーではありません。必要な方式だけ設定してください。

## 0. 作業範囲を確認

- 既存ComfyUI・Python・モデルの場所、GPU、RAM、空きディスクを読み取り確認する。
- 既存ComfyUIを無条件にpull/updateしない。依存パッケージやドライバーも無条件に変更しない。
- 非対応なら利用者に説明し、独立したComfyUIクローンとvenvを使う。モデルは既存のフォルダを参照できる。
- **大型モデルのダウンロードは容量・配布元・条件を先に伝えて確認する。** Hugging Faceの同意やログインは本人が行う。トークンをチャットや設定ファイルに貼らせない。
- インストール後はローカルのみで生成。課金API・Partner Nodeは使用しない。

## 1. アプリ用Python

作者の使用構成：Windows 11 / RTX 5060 Laptop 8GB / RAM 32GB / Python 3.12.12。UI依存はaiohttp 3.14.5、requests 2.34.2、psutil 7.2.2、Pillow 12.3.0で確認。モデル読込は別のComfyUI用Pythonを使う。

リポジトリのルートでPowerShellを開き、既存環境と別のvenvを作る。

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item -LiteralPath config.example.json -Destination config.local.json
```

既にconfig.local.jsonがある場合はコピーで上書きしない。`py`がなければ、利用者のPython 3.12実行ファイルを指定する。アプリ用venvにPyTorchやComfyUIを入れる必要はない。

## 2. ComfyUIの確認

両方式とも `main.py` を持つPython版ComfyUIが必要。GUI専用の起動ファイルではなく、ComfyUIのフォルダと、その依存関係を備えたPython実行ファイルを設定する。

FLUX 3で使用したComfyUIのcommit：`63be2f9b82ad0dac88a7ceaa28a9cf3154125a18`。これは作者構成の参照点で、既存インストールをこのcommitへ強制変更する指示ではない。[公式FLUX 3案内](https://docs.comfy.org/tutorials/flux/flux-3-klein) とノードの有無を確認する。古い版に不足があれば別フォルダに [ComfyUI](https://github.com/Comfy-Org/ComfyUI) を用意し、そのREADMEに従って専用venv・対応CUDA版PyTorch・requirementsを導入する。作者のFLUX環境のPyTorchは `2.12.0+cu130`。他のGPUにそのまま強制しない。

このアプリはComfyUIを別プロセスで起動する。`--base-directory` を配布版内の `runtime/sd` / `runtime/flux` に固定し、個人版や他の起動中ComfyUIを利用しない。既存ファイルは更新しない。起動対象のComfyUIは信頼できるものを使う。下記の起動引数が使える版が必要：

```text
--base-directory --listen --port --disable-auto-launch
--disable-all-custom-nodes --reserve-vram --cache-none
--disable-pinned-memory --disable-async-offload --preview-method
--extra-model-paths-config --database-url
--whitelist-custom-nodes  (SDのみ)
```

## 3. FLUX 3を使う場合

[BFL公式配布](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy) の利用同意を本人が行う。使用した配布revisionは `feef60b0aaf63a4773ace96636ebbcf43b881312`。下記4ファイルの合計は **17.75GB（約16.53GiB）**。Python環境・キャッシュ・生成物には別途空きが必要。既にあれば再取得しない。

| model_rootsで指定するmodelsフォルダ内の相対位置 | サイズ（GB） |
|---|---:|
| diffusion_models/flux3-image-klein-int8-convrot.safetensors | 5.83 |
| text_encoders/qwen3vl_4b_int8_convrot.safetensors | 4.86 |
| text_encoders/qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors | 6.72 |
| vae/flux2-vae.safetensors | 0.34 |

さらに同revisionの **`workflows/flux3_klein_int8_i2i.json`** を利用者のローカルフォルダへ取得し、`prompt_template` にそのファイルを指定する。公式テンプレート本体はこの配布に含まない。[取得ページ](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/blob/feef60b0aaf63a4773ace96636ebbcf43b881312/workflows/flux3_klein_int8_i2i.json)。このアプリは `Prompt Upsampler` サブグラフ内のノード114・134からシステム指示と入力書式を読み、毎回新しい原画を読む。無効化による代替はしない。

必要なComfyUI組み込みノード：UNETLoader、CLIPLoader（type=flux3）、VAELoader、CLIPTextEncode、LoadImage、ReferenceMultiLatent、ModelSamplingFlux、EmptyFlux2LatentImage、KSampler、VAEDecode、SaveImage、TextGenerate、PreviewAny。外部FLUXカスタムノードは不要。

## 4. SD系を使う場合

プリセット別の正確なモデル・ノード一覧は [docs/preset-dependencies.json](docs/preset-dependencies.json)。SDXL / Illustrious系用で、SD1.5用ではない。

| models内の配置先とファイル名 | 必要なプリセット |
|---|---|
| checkpoints/gsBEYONDTHEDRAWINGANIME_v10.safetensors | A01、A12、A15、B08、検証05、検証07、追加A01、A15-中間-再描画直後 |
| checkpoints/novaAnimeXL_ilV160.safetensors | A08、B04 |
| loras/Manga_Mode_Illustrious.safetensors | A12、A15、B08、検証05、検証07、追加A01、A15-中間-再描画直後 |
| controlnet/controlnet_union_sdxl_promax.safetensors | A01以外のSDプリセット |

checkpointは各約6.94GB、LoRAは約0.23GB。ControlNet等は配布元のサイズを確認する。[各配布元と利用条件](THIRD_PARTY.md)。ControlNet ProMaxの配布名が `diffusion_pytorch_model_promax.safetensors` 等の場合は `model_names` で実際のファイル名へ対応付ける。別モデルへの置き換えは画風・品質が変わる。

SDの線画ガイド用に [comfyui_controlnet_aux](https://github.com/Fannovel16/comfyui_controlnet_aux) を別フォルダへ導入し、そのrequirementsを**SD用ComfyUIのPython環境**で満たす。既存環境へ入れるなら事前に説明し、依存衝突があれば専用venvを使う。`aux_path` はそのリポジトリのルート（`src/custom_controlnet_aux` の親の親）。`erika_path` は別途用意した [erika.pth](https://huggingface.co/lllyasviel/Annotators/blob/main/erika.pth) のフルパス。アプリは自動ダウンロードしない。

配布内の自作接続コード `app/adapters/mono_local` は起動時にこのアプリ専用の `runtime/sd/custom_nodes/mono_local` にコピーされる。MonoLuminance、MonoOfficialLineart、MonoInkFinishを登録し、MangaLineartをCPUで実行する。外部ノード本体は同梱しない。MangaScreenは今回のプリセットの実行には不要。

その他のSDノードはComfyUI組み込み：CheckpointLoaderSimple、LoraLoader、ControlNetLoader、SetUnionControlNetType、Canny、ControlNetApplyAdvanced、ImageScale、VAEEncode、VAEDecodeTiled、CLIPTextEncode、KSampler、SaveImage等。詳細は依存一覧の全ノードを照合する。

## 5. config.local.jsonを編集

`config.example.json` の構造を保ち、使う方式の `enabled` を `true` にする。JSONのパスは `/` 区切りが簡単。下記は**配置例**であり自動検出された値ではない。

```json
{
  "ui_port": 8971,
  "engines": {
    "sd": {
      "enabled": false, "python": "", "comfyui": "", "port": 8196,
      "model_roots": [], "aux_path": "", "erika_path": ""
    },
    "flux": {
      "enabled": true,
      "python": "D:/AI/ComfyUI-Flux/.venv/Scripts/python.exe",
      "comfyui": "D:/AI/ComfyUI-Flux",
      "port": 8197,
      "model_roots": ["D:/AI/models"],
      "prompt_template": "D:/AI/templates/flux3_klein_int8_i2i.json"
    }
  },
  "model_names": {}
}
```

`model_roots` は各種モデルフォルダを含む `models` 相当の親を指定する。複数指定可能。設定したComfyUI自身の `models` は自動で参照する。既存のextra_model_paths.yamlだけに依存せず、そこにしかないパスはこの設定にも追加する。フォルダ名が異なる既存配置は各方式の設定に `"model_paths": {"checkpoints": ["D:/AI/StableDiffusion"], "loras": ["D:/AI/Lora"]}` のように追加できる。ファイル名が異なる場合：

```json
"model_names": {
  "controlnet_union_sdxl_promax.safetensors": "diffusion_pytorch_model_promax.safetensors"
}
```

全ポートは重複しない番号を選ぶ。ホストは127.0.0.1固定。認証キーを設定ファイルへ入れない。`MANGA_CONFIG` 環境変数を指定すると別の設定ファイルを参照できる（検証用）。

## 6. 起動・最小確認

```powershell
& .\.venv\Scripts\python.exe -X utf8 app/check_install.py
# 有効にした方式だけ確認（モデルの生成・ダウンロードはしない）
& .\.venv\Scripts\python.exe -X utf8 app/check_install.py --engine flux
.\start.bat
```

画面が開き20件の説明が見えること、原画選択、基本の非表示→再表示、自作プリセットの保存→削除を確認する。生成試験を行う場合は利用者の画像で設定済み方式を1枚、1MPで試す。FLUXは原画理解→漫画化の順。SDの2段階プリセットは顔などの保護範囲を手でなぞる必要がある。出力PNGと設定は `出力/` に保存される。

メモリは生成前にRAM使用率90%以上または空き3.5GiB未満、生成中に94%以上または空き2.5GiB未満で停止する。生成は逐次1枚。自分が起動した専用エンジンを終了・解放することはあるが、別のComfyUIや無関係のアプリを終了しない。低メモリ停止時に基準を無断で緩めない。

失敗時は `記録/` と `runtime/<方式>/server.log` を本人のPC内で確認する。外へ送る前に原画・プロンプト・パス等を除く。UIが起動しても、モデルやノードの不足を含め画像生成の成功を保証するものではない。

作者環境以外では未検証。全自動導入や他環境での動作を保証しない。利用者の既存環境を尊重し、上記の範囲で導入を確認する。
