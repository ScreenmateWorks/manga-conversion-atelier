"""Start an isolated local ComfyUI process using configured installed software."""
from pathlib import Path
import json, os, shutil, subprocess, sys, time
import requests
from config import ROOT, engine_config

def main(kind):
 c=engine_config(kind);base=ROOT/'runtime'/kind;base.mkdir(parents=True,exist_ok=True)
 for name in ['input','output','user','temp','custom_nodes']:(base/name).mkdir(exist_ok=True)
 session=requests.Session();session.trust_env=False
 address='http://127.0.0.1:'+str(c['port'])
 try:
  r=session.get(address+'/system_stats',timeout=2);r.raise_for_status()
  if str(base) not in r.json()['system']['argv']:raise RuntimeError('ポートが他のアプリに使われています。ポート設定を変更してください。')
  return
 except requests.ConnectionError:pass
 # These flags must be supported before starting; never update the user's install.
 help_result=subprocess.run([str(c['python']),str(c['comfyui']/'main.py'),'--help'],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
 flags=['--base-directory','--disable-all-custom-nodes','--reserve-vram','--cache-none','--disable-pinned-memory','--disable-async-offload','--database-url']
 missing=[f for f in flags if f not in help_result.stdout]
 if help_result.returncode or missing:raise RuntimeError('ComfyUIが起動引数に未対応です。既存環境は更新せず、AI_INSTALL.mdの独立環境を使用してください: '+', '.join(missing))
 env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
 if kind=='sd':
  env.update(MANGA_AUX_PATH=str(c['aux_path']),MANGA_ERIKA_PATH=str(c['erika_path']))
  dest=base/'custom_nodes/mono_local';dest.mkdir(exist_ok=True)
  shutil.copy2(ROOT/'app/adapters/mono_local/__init__.py',dest/'__init__.py')
 # Reference existing model directories without copying weights or changing ComfyUI.
 roots=[c['comfyui']/'models']+c['model_roots']
 paths={}
 for i,root in enumerate(roots):
  paths['manga_'+str(i)]={'base_path':str(root),**{k:k for k in ['checkpoints','loras','controlnet','diffusion_models','text_encoders','vae','clip','unet']}}
 for k,folders in c['model_paths'].items():
  paths['custom_'+k]={k:'\n'.join(str(p) for p in folders)}
 # JSON is valid YAML and avoids Windows path escaping ambiguity.
 model_config=base/'model_paths.yaml';model_config.write_text(json.dumps(paths,ensure_ascii=False,indent=2),'utf-8')
 command=[str(c['python']),'-X','utf8',str(c['comfyui']/'main.py'),'--base-directory',str(base),'--listen','127.0.0.1','--port',str(c['port']),'--disable-auto-launch','--disable-all-custom-nodes','--reserve-vram','1','--cache-none','--disable-pinned-memory','--disable-async-offload','--preview-method','none','--extra-model-paths-config',str(model_config),'--database-url','sqlite:///'+(base/'user/app.db').as_posix()]
 if kind=='sd':command+=['--whitelist-custom-nodes','mono_local']
 with (base/'server.log').open('a',encoding='utf-8') as log:
  proc=subprocess.Popen(command,cwd=base,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  (base/'server.pid').write_text(str(proc.pid),'ascii')
 for _ in range(120):
  if proc.poll() is not None:raise RuntimeError('ComfyUIが終了しました。runtime内のserver.logを確認してください。')
  try:r=session.get(address+'/object_info',timeout=2);r.raise_for_status();return
  except requests.RequestException:time.sleep(1)
 raise RuntimeError('起動待ちが時間切れになりました。runtime内のserver.logを確認してください。')

if __name__=='__main__':main(sys.argv[1])
