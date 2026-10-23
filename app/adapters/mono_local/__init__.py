"""Explicit luminance conversion only; no edge extraction or smoothing."""
class MonoLuminance:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'image': ('IMAGE',)}}
    RETURN_TYPES=('IMAGE',)
    FUNCTION='convert'
    CATEGORY='モノクロ制作'
    def convert(self,image):
        gray=image[...,0:1]*0.299+image[...,1:2]*0.587+image[...,2:3]*0.114
        return (gray.repeat(1,1,1,3),)

class MonoOfficialLineart:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{'image':('IMAGE',),'resolution':('INT',{'default':768,'min':256,'max':1536,'step':256})}}
    RETURN_TYPES=('IMAGE','IMAGE')
    RETURN_NAMES=('構造ガイド（黒地）','線画下地（白地）')
    FUNCTION='extract'
    CATEGORY='モノクロ制作'
    def extract(self,image,resolution):
        from pathlib import Path
        import sys,torch,numpy as np
        from PIL import Image
        aux=Path(__import__('os').environ['MANGA_AUX_PATH'])
        src=str(aux/'src')
        if src not in sys.path:sys.path.insert(0,src)
        from custom_controlnet_aux.manga_line import LineartMangaDetector
        from custom_controlnet_aux.manga_line.model_torch import res_skip
        weights=Path(__import__('os').environ['MANGA_ERIKA_PATH'])
        if not weights.is_file():raise FileNotFoundError('既存のerika.pthがありません。自動ダウンロードは行いません。')
        net=res_skip()
        state=torch.load(weights,map_location='cpu',weights_only=True)
        net.load_state_dict({k.removeprefix('module.'):v for k,v in state.items()});net.eval()
        detector=LineartMangaDetector(net).to('cpu')
        results=[]
        for frame in image:
            pil=Image.fromarray((frame.detach().cpu().numpy().clip(0,1)*255).astype(np.uint8))
            out=detector(pil,detect_resolution=resolution)
            results.append(torch.from_numpy(np.array(out).astype(np.float32)/255))
        guide=torch.stack(results)
        return (guide,1-guide)

class MonoInkFinish:
    """Separate already redrawn ink into black/white with an antialiased transition.

    Does not extract contours, smooth, sharpen, resize, or synthesize details.
    It is deliberately a finishing step after diffusion, never the color converter.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{'image':('IMAGE',),'threshold':('FLOAT',{'default':.78,'min':.3,'max':.95,'step':.01}),'transition':('FLOAT',{'default':.12,'min':.02,'max':.4,'step':.01})}}
    RETURN_TYPES=('IMAGE',)
    FUNCTION='finish'
    CATEGORY='モノクロ制作'
    def finish(self,image,threshold,transition):
        gray=image[...,0:1]*.299+image[...,1:2]*.587+image[...,2:3]*.114
        value=((gray-threshold)/transition+.5).clamp(0,1)
        value=value*value*(3-2*value)
        return (value.repeat(1,1,1,3),)

NODE_CLASS_MAPPINGS={'MonoLuminance':MonoLuminance,'MonoOfficialLineart':MonoOfficialLineart,'MonoInkFinish':MonoInkFinish}
NODE_DISPLAY_NAME_MAPPINGS={'MonoLuminance':'色のみ除去（線・階調は保持）','MonoOfficialLineart':'公式Manga Lineart（既存モデル・CPU）','MonoInkFinish':'AI再描画後のベタ整版（輪郭抽出なし）'}
