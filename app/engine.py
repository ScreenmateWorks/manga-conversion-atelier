"""Adapters for the saved SD and FLUX experiments. Never edits their files."""
from pathlib import Path
import asyncio, copy, hashlib, json, math, os, subprocess, time, uuid
import aiohttp, psutil, requests
from PIL import Image, ImageOps, ImageFilter

HERE=Path(__file__).resolve().parent
from config import CONFIG, engine_config
TOOLS=HERE.parent
DATA=json.loads((HERE/'presets.json').read_text('utf-8'))
PRESETS={p['id']:p for p in DATA['presets']}
ENGINES={
 'sd':dict(port=CONFIG['engines']['sd']['port'],base=HERE.parent/'runtime/sd',start=HERE/'launch_engine.py'),
 'flux':dict(port=CONFIG['engines']['flux']['port'],base=HERE.parent/'runtime/flux',start=HERE/'launch_engine.py')}
import sys
PYTHON=Path(sys.executable)
S=requests.Session();S.trust_env=False

def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def fingerprint(im):return hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()
def identify(im):return next((i for i in DATA['inputs'] if i['fingerprint']==fingerprint(im)),None)
def node(kind,**inputs):return dict(class_type=kind,inputs=inputs)
def url(engine):return 'http://127.0.0.1:'+str(ENGINES[engine]['port'])
def get(engine,path):r=S.get(url(engine)+path,timeout=8);r.raise_for_status();return r.json()
def post(engine,path,data):r=S.post(url(engine)+path,json=data,timeout=30);r.raise_for_status();return r.json() if r.content else {}
def checked(engine):
 stats=get(engine,'/system_stats')
 if str(ENGINES[engine]['base']) not in stats['system']['argv']:raise RuntimeError('必要なポートを別のアプリが使用しています。既存環境は操作せず停止しました。')
 return stats
def busy(engine):q=get(engine,'/queue');return bool(q['queue_running'] or q['queue_pending'])
def free_idle(engine):
 checked(engine)
 if not busy(engine):post(engine,'/free',dict(unload_models=True,free_memory=True))
def stop_idle_owned(engine):
 """Only our app's isolated, idle server. Never stops the previous environments."""
 try:
  checked(engine)
  if busy(engine):return
 except requests.ConnectionError:return
 base=str(ENGINES[engine]['base'])
 owned=[]
 for proc in psutil.process_iter(['name','cmdline']):
  args=proc.info.get('cmdline') or []
  if proc.info.get('name')=='python.exe' and base in args and '--base-directory' in args:owned.append(proc)
 for proc in reversed(owned):
  try:proc.terminate()
  except psutil.NoSuchProcess:pass
 psutil.wait_procs(owned,timeout=5)
def ensure(engine,update,cancel):
 for other in ENGINES:
  try:checked(other)
  except requests.ConnectionError:continue
  if busy(other):raise RuntimeError('検証用エンジンが別の画像を処理中です。完了後にもう一度お試しください。')
  if other!=engine:stop_idle_owned(other)
  else:free_idle(other)
 try:checked(engine);return
 except requests.ConnectionError:pass
 update(message='画像処理エンジンを起動しています…',phase='準備')
 log=(HERE.parent/'記録/エンジン起動.log').open('a',encoding='utf-8')
 env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONIOENCODING='utf-8')
 with log:
  proc=subprocess.Popen([str(PYTHON),'-X','utf8',str(ENGINES[engine]['start']),engine],env=env,cwd=HERE,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  deadline=time.monotonic()+150
  while time.monotonic()<deadline:
   if cancel.is_set():raise RuntimeError('中止しました。')
   try:checked(engine);get(engine,'/object_info');return
   except requests.ConnectionError:pass
   if proc.poll() not in (None,0):raise RuntimeError('エンジンを起動できませんでした。記録フォルダの起動ログを確認してください。')
   time.sleep(1)
 raise RuntimeError('エンジンの起動待ちが時間切れになりました。')

def dimensions(p,im,options):
 mp=p['presetMP'] if options['megapixels']=='preset' else float(options['megapixels'])
 # Keep the recorded dimensions when input shape matches; otherwise preserve its aspect ratio.
 if options['megapixels']=='preset' and abs(im.width/im.height-p['width']/p['height'])<.015:return p['width'],p['height']
 align=16 if p['engine']=='flux' else 8
 factor=math.sqrt(mp*1024**2/(im.width*im.height))
 return max(align,round(im.width*factor/align)*align),max(align,round(im.height*factor/align)*align)

def prune(g,output):
 keep=set()
 def visit(key):
  if key in keep:return
  keep.add(key)
  for v in g[key]['inputs'].values():
   if isinstance(v,list) and len(v)==2 and isinstance(v[0],str) and v[0] in g:visit(v[0])
 visit(output)
 return {k:v for k,v in g.items() if k in keep}

def style_adjustment(options):
 parts=[]
 density=options['density'];lines=options['lines']
 if density>0:parts.append(f'Give deeper, more connected black shadow shapes in existing shadow recesses (strength {density}/100), while preserving bright skin, eyes, highlights and clothing details.')
 if density<0:parts.append(f'Use lighter, more restrained shadows (strength {-density}/100), with open white space and delicate gray transitions; preserve the key outlines.')
 if lines>0:parts.append(f'Use more pronounced, confident and tapered pen strokes (strength {lines}/100), keeping individual hair strands and clear eyes. No added contours or sharpness filter.')
 if lines<0:parts.append(f'Use finer, lighter, delicate continuous pen strokes (strength {-lines}/100), without losing eyes, hair strands or clothing seams.')
 if options['instruction']:parts.append(options['instruction'])
 return ' '.join(parts)

def sd_graph(p,im,image_name,options,known,mask_name=None):
 g=json.loads((HERE/'プリセット原本'/p['id']/'workflow.json').read_text('utf-8'))
 g['3']['inputs']['image']=image_name
 w,h=dimensions(p,im,options)
 for key,item in g.items():
  kind=item['class_type'];v=item['inputs']
  if kind=='ImageScale':v.update(width=w,height=h)
  if kind=='KSampler':v.update(seed=options['seed'],steps=options['steps'],cfg=options['cfg'])
  if kind=='ControlNetApplyAdvanced' and key=='12':v['strength']=options['control']
  if kind=='LoraLoader':v['strength_model']=v['strength_clip']=options['lora']
 g['13']['inputs']['denoise']=options['denoise']
 description=options['description'].strip() or (known['description'] if known else 'same subject, same pose, same hairstyle, same clothing and accessories as the reference image')
 old_descriptions=['{{subject}}']
 for key in ['7','43']:
  if key not in g:continue
  text=g[key]['inputs']['text']
  for old in old_descriptions:text=text.replace(old,description)
  g[key]['inputs']['text']=text+(' '+style_adjustment(options) if style_adjustment(options) else '')
 if p['twoPass']:
  if not mask_name:raise ValueError('顔・手など、保護する範囲をなぞってください。')
  g['41']['inputs']['image']=mask_name
  g['46']['inputs'].update(denoise=options['second_denoise'],seed=(options['seed']+1)%(2**53))
 if p['id']=='A15-中間-再描画直後':g['20']['inputs']['images']=['14',0]
 g['20']['inputs']['filename_prefix']='漫画変換アプリ/'+uuid.uuid4().hex
 return remap_models(prune(g,'20')),'20'

def flux_instruction(p,config,options):
 # User-approved experiment prompts are already complete; keep them byte-for-byte
 # at defaults, then add only the user's explicit adjustments.
 if config.get('literal_prompt'):
  parts=[config['prompt'],style_adjustment(options)]
  if options['description']:parts.append('Additional description of the input: '+options['description'])
  return ' '.join(part for part in parts if part)
 common='Use only the supplied image as reference. Preserve the same subjects, identities, expressions, gaze, poses, hands, hairstyle, clothing, accessories, composition, proportions and background. Do not add objects, text, patterns or new costume details. Redraw it as a finished monochrome manga illustration, not a desaturation or edge-detection filter. '
 text=config.get('prompt','')
 if text:
  text=text.replace('and white background','and the original background').replace('same adult character','same subject')
 else:
  styles={
   'F3-22':'Prioritize delicate flowing hair lines, natural soft grayscale shading, bright skin and restrained cloth reflections. Keep the volume of fabric with calm gray transitions. Avoid exaggerated outlines and flat gray skin.',
   'F3-23':'Use connected solid black in the recessed hair roots, the cast shadow beneath the chin and along the neck, neckline recesses where visible, and deep garment folds. Keep lit skin, face and hands white and readable. Use fine continuous tapered lines in lit areas. No indiscriminate darkening.',
   'F3-25':'Use connected solid black in recessed hair roots, cast shadows below the chin and neck, neckline recesses where visible, and deepest garment folds. Keep illuminated skin, eyes and hands readable. Use a few long clean tapered white accents inside black garment shadows, preserving delicate lace and hair strands. Confident continuous strokes, no grain, scratchy clusters, gray gradients or stippling.'}
  text=common+styles[p['id']]
 return text+' '+style_adjustment(options)+((' Additional description of the input: '+options['description']) if options['description'] else '')

def flux_graph(p,im,image_name,options,caption):
 g=json.loads((HERE/'プリセット原本'/p['id']/'workflow.json').read_text('utf-8'))
 g['6']['inputs']['image']=image_name;g['4']['inputs']['text']=caption
 g['8']['inputs'].update(seed=options['seed'],steps=options['steps'],cfg=options['cfg'])
 w,h=dimensions(p,im,options)
 # Reference stays at its original size; output size is explicit and aspect-preserving.
 g['12']=node('EmptyFlux2LatentImage',width=w,height=h,batch_size=1)
 g['8']['inputs']['latent_image']=['12',0]
 g['10']['inputs']['filename_prefix']='漫画変換アプリ/'+uuid.uuid4().hex
 return remap_models(prune(g,'10')),'10'

def remap_models(g):
 for n in g.values():
  for k,v in n['inputs'].items():
   if k in ['ckpt_name','lora_name','control_net_name','unet_name','clip_name','vae_name']:
    n['inputs'][k]=CONFIG.get('model_names',{}).get(v,v)
 return g

def expansion(image,prompt,seed):
 from prompt_expansion import graph
 return remap_models(graph(image,prompt,seed))

async def execute(engine,g,folder,label,update,cancel,metrics):
 if busy(engine):raise RuntimeError('画像処理エンジンが使用中です。完了後にお試しください。')
 vm=psutil.virtual_memory()
 if vm.percent>=90 or vm.available<3.5*2**30:raise RuntimeError(f'空きメモリが不足しています（RAM {vm.percent}%）。ほかの重いアプリを閉じてからお試しください。')
 save(folder/(label+'_workflow.json'),g)
 client=uuid.uuid4().hex;pid=None;start=time.monotonic();last_gpu=0;gpu=None
 async with aiohttp.ClientSession(trust_env=False) as session:
  async with session.ws_connect(url(engine).replace('http:','ws:')+'/ws?clientId='+client,max_msg_size=16*1024**2) as ws:
   async with session.post(url(engine)+'/prompt',json=dict(prompt=g,client_id=client)) as response:
    receipt=await response.json()
    if response.status!=200:raise RuntimeError('設定を受け付けられませんでした: '+json.dumps(receipt,ensure_ascii=False)[:1800])
   pid=receipt['prompt_id'];save(folder/(label+'_受付.json'),receipt)
   try:
    while True:
     vm=psutil.virtual_memory();elapsed=time.monotonic()-start
     if time.monotonic()-last_gpu>2:
      try:
       proc=await asyncio.create_subprocess_exec('nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
       stdout,_=await asyncio.wait_for(proc.communicate(),3);gpu=int(stdout.decode().strip().splitlines()[0])
      except Exception:gpu=None
      last_gpu=time.monotonic()
     row=dict(phase=label,elapsed=round(elapsed,2),ram_percent=vm.percent,ram_used=vm.used,ram_available=vm.available,vram_mib=gpu)
     metrics.append(row)
     update(ram=vm.percent,vram=gpu)
     if cancel.is_set():raise RuntimeError('生成を中止しました。')
     if vm.percent>=94 or vm.available<2.5*2**30:raise RuntimeError(f'RAMが停止基準に達したため中止しました（使用率{vm.percent}%・空き{vm.available/2**30:.1f}GiB）。ほかのアプリを閉じてお試しください。')
     if elapsed>900:raise RuntimeError('処理が15分を超えたため停止しました。記録をご確認ください。')
     try:
      msg=await ws.receive(timeout=.7)
      if msg.type==aiohttp.WSMsgType.TEXT:
       event=json.loads(msg.data);data=event.get('data',{})
       if data.get('prompt_id',pid)==pid:
        if event['type']=='progress':update(step=data.get('value'),total=data.get('max'))
        if event['type']=='executing' and data.get('node'):
         kind=g.get(str(data['node']),{}).get('class_type','')
         names={'MonoOfficialLineart':'原画から構造ガイドを作成','KSampler':'AIが描き直しています','VAEDecodeTiled':'画像に仕上げています','VAEDecode':'画像に仕上げています','TextGenerate':'原画を読んで指示を準備しています','CheckpointLoaderSimple':'モデルを読み込んでいます','UNETLoader':'モデルを読み込んでいます'}
         if kind in names:update(message=('2回目の仕上げを描いています' if kind=='KSampler' and str(data['node'])=='46' else names[kind]))
     except asyncio.TimeoutError:pass
     async with session.get(url(engine)+'/history/'+pid,timeout=aiohttp.ClientTimeout(total=12)) as resp:history=(await resp.json()).get(pid)
     if history:
      save(folder/(label+'_履歴.json'),history)
      if history.get('status',{}).get('status_str')!='success':raise RuntimeError('画像生成に失敗しました。実行履歴を記録しました。')
      return history
   except BaseException:
    if pid:
     try:
      q=get(engine,'/queue')
      if any(x[1]==pid for x in q['queue_running']):post(engine,'/interrupt',{'prompt_id':pid})
      if any(x[1]==pid for x in q['queue_pending']):post(engine,'/queue',{'delete':[pid]})
      # Wait for our own running task to stop before another job can be submitted.
      for _ in range(60):
       if not any(x[1]==pid for x in get(engine,'/queue')['queue_running']):break
       await asyncio.sleep(.5)
     except requests.RequestException:pass
    raise
   finally:save(folder/'メモリ計測.json',metrics)

def generate(p,source,options,folder,update,cancel,mask=None):
 engine=p['engine'];engine_config(engine);metrics=[];start=time.monotonic()
 with Image.open(source) as src:im=src.convert('RGB')
 known=identify(im);name='漫画変換_'+uuid.uuid4().hex+'.png';base=ENGINES[engine]['base']
 ensure(engine,update,cancel)
 im.save(base/'input'/name)
 save(folder/'設定.json',dict(preset=p['id'],options=options,recognized_input=known['id'] if known else None,source_fingerprint=fingerprint(im)))
 try:
  mask_name=None
  if p['twoPass']:
   w,h=dimensions(p,im,options)
   if mask:
    with Image.open(mask) as raw:edit=ImageOps.invert(raw.convert('L')).resize((w,h),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(3))
   else:raise ValueError('この2段階プリセットでは、原画上で顔・手など保護する部分をなぞってください。')
   mask_name='漫画変換_保護_'+uuid.uuid4().hex+'.png';edit.save(base/'input'/mask_name);edit.save(folder/'編集範囲.png')
  if engine=='sd':g,out=sd_graph(p,im,name,options,known,mask_name)
  else:
   config=json.loads((HERE/'プリセット原本'/p['id']/'settings.json').read_text('utf-8'))
   instruction=flux_instruction(p,config,options)
   (folder/'変換指示.txt').write_text(instruction,'utf-8')
   update(message='原画に合わせた指示を準備しています…',phase='原画の理解',step=None,total=None)
   h=asyncio.run(execute(engine,expansion(name,instruction,0),folder,'01_指示拡張',update,cancel,metrics))
   caption=h['outputs']['4']['text'][0]
   if not caption.strip():raise RuntimeError('原画の読み取り結果が空でした。')
   free_idle(engine)
   (folder/'拡張済み指示.txt').write_text(caption,'utf-8')
   if config.get('post_expansion_suffix'):
    caption+=config['post_expansion_suffix']
   (folder/'最終指示.txt').write_text(caption,'utf-8')
   g,out=flux_graph(p,im,name,options,caption)
  update(message='AIで漫画に描き直します…',phase='漫画化',step=None,total=None)
  history=asyncio.run(execute(engine,g,folder,'02_漫画化',update,cancel,metrics))
  file=history['outputs'][out]['images'][0]
  r=S.get(url(engine)+'/view',params=file,timeout=60);r.raise_for_status()
  result=folder/'完成.png';result.write_bytes(r.content)
  with Image.open(result) as check:check.verify()
  summary=dict(seconds=round(time.monotonic()-start,1),ram_peak_percent=max((x['ram_percent'] for x in metrics),default=None),vram_peak_mib=max((x['vram_mib'] for x in metrics if x['vram_mib'] is not None),default=None))
  save(folder/'実行結果.json',summary)
  return result,summary
 finally:
  try:free_idle(engine);stop_idle_owned(engine)
  except requests.RequestException:pass
