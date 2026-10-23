"""Local configuration. No discovery, downloading, updating or credential access."""
from pathlib import Path
import json, os

ROOT=Path(__file__).resolve().parent.parent
CONFIG_PATH=Path(os.environ.get('MANGA_CONFIG',ROOT/'config.local.json')).resolve()
CONFIG=json.loads((CONFIG_PATH if CONFIG_PATH.is_file() else ROOT/'config.example.json').read_text('utf-8-sig'))
ports=[CONFIG['ui_port']]+[x['port'] for x in CONFIG['engines'].values()]
if any(type(p)!=int or not 1024<=p<=65535 for p in ports) or len(set(ports))!=len(ports):
 raise ValueError('config: ポートは重複しない1024～65535の整数で指定してください。')

def existing_path(value,kind='file'):
 if not value:raise ValueError('config.local.json のパスが未設定です。AI_INSTALL.mdを参照してください。')
 path=Path(value).expanduser()
 if not path.is_absolute():path=CONFIG_PATH.parent/path
 path=path.resolve()
 if not (path.is_dir() if kind=='dir' else path.is_file()):raise ValueError('設定したパスが見つかりません: '+str(path))
 return path

def engine_config(kind):
 c=dict(CONFIG['engines'][kind])
 if not c.get('enabled'):raise ValueError(kind+' は未設定です。AI_INSTALL.mdに従いconfig.local.jsonを設定してください。')
 c['python']=existing_path(c['python']);c['comfyui']=existing_path(c['comfyui'],'dir')
 if not (c['comfyui']/'main.py').is_file():raise ValueError('ComfyUIのmain.pyが見つかりません。')
 c['model_roots']=[existing_path(p,'dir') for p in c.get('model_roots',[])]
 allowed={'checkpoints','loras','controlnet','diffusion_models','text_encoders','vae','clip','unet'}
 c['model_paths']={k:[existing_path(p,'dir') for p in v] for k,v in c.get('model_paths',{}).items() if k in allowed}
 if kind=='flux':c['prompt_template']=existing_path(c.get('prompt_template'))
 else:
  c['aux_path']=existing_path(c.get('aux_path'),'dir')
  c['erika_path']=existing_path(c.get('erika_path'))
 return c
