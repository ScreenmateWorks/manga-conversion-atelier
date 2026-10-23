"""Read-only installation checks. Does not start ComfyUI or download models."""
import argparse, importlib.metadata, json, sys
from config import ROOT, CONFIG, engine_config

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--engine',choices=['sd','flux'])
 parser.add_argument('--preset',help='Check only the dependencies of this preset ID')
 args=parser.parse_args()
 for name in ['aiohttp','requests','psutil','Pillow']:print(name,importlib.metadata.version(name))
 data=json.loads((ROOT/'app/presets.json').read_text('utf8'))['presets']
 manifest=json.loads((ROOT/'docs/preset-dependencies.json').read_text('utf8'))
 ids=[p['id'] for p in data]
 if len(ids)!=len(set(ids)):raise ValueError('Duplicate preset IDs')
 for p in data:
  g=json.loads((ROOT/'app/プリセット原本'/p['id']/'workflow.json').read_text('utf8'))
  for n in g.values():
   for value in n['inputs'].values():
    if isinstance(value,list) and len(value)==2 and isinstance(value[0],str) and value[0] not in g:raise ValueError('Broken node link: '+p['id'])
 print('Preset files:',len(ids),'OK; UI port:',CONFIG['ui_port'])
 if args.preset and args.preset not in ids:raise ValueError('Unknown preset ID')
 kind=args.engine or (manifest[args.preset]['engine'] if args.preset else None)
 if not kind:
  print('Only package structure checked. Use --engine sd/flux for configured paths and weights.');return
 if args.preset and manifest[args.preset]['engine']!=kind:raise ValueError('Preset/backend mismatch')
 c=engine_config(kind)
 rows=[manifest[args.preset]] if args.preset else [p for p in manifest.values() if p['engine']==kind]
 names={m for p in rows for m in p['models']}
 if kind=='flux':
  names.add('qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors')
  from prompt_expansion import template_prompts
  template_prompts();print('Official prompt template: OK')
 roots=[c['comfyui']/'models']+c['model_roots']
 missing=[]
 for original in sorted(names):
  name=CONFIG.get('model_names',{}).get(original,original)
  found=any((root/folder/name).is_file() for root in roots for folder in ['checkpoints','loras','controlnet','diffusion_models','text_encoders','vae','clip','unet']) or any((folder/name).is_file() for paths in c['model_paths'].values() for folder in paths)
  print(('OK ' if found else 'MISSING ')+name)
  if not found:missing.append(name)
 print('Required nodes:',', '.join(sorted({n for p in rows for n in p['nodes']})))
 if missing:raise ValueError('Missing model files; nothing was downloaded.')
 print('Configured files found. GPU capacity, node compatibility and generation are not tested by this command.')

if __name__=='__main__':
 try:main()
 except Exception as exc:print('CHECK FAILED:',exc,file=sys.stderr);sys.exit(1)
