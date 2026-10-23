"""Local-only UI, one serial job, immutable presets and dated output folders."""
import base64, io, json, math, mimetypes, os, secrets, subprocess, sys, threading, time, traceback, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote
import psutil, requests
from PIL import Image, ImageOps
import engine
from user_presets import UserPresets

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;PORT=engine.CONFIG['ui_port'];APP_ID='manga-atelier-public-v1'
(ROOT/'記録').mkdir(exist_ok=True)
UPLOADS=ROOT/'runtime/uploads';UPLOADS.mkdir(parents=True,exist_ok=True)
OUTPUT=ROOT/'出力';OUTPUT.mkdir(exist_ok=True)
TOKEN=secrets.token_urlsafe(32)
STATE={'status':'idle','message':'原画とプリセットを選んでください','result':None,'phase':'待機','step':None,'total':None}
LOCK=threading.RLock();CANCEL=threading.Event();INPUTS={}
Image.MAX_IMAGE_PIXELS=24_000_000

def update(**kwargs):
 with LOCK:STATE.update(kwargs)
def state():
 with LOCK:result=dict(STATE)
 if result.get('started'):result['elapsed']=round(result.get('finished',time.time())-result['started'],1)
 return result
def safe(root,rel):
 p=(root/rel).resolve()
 if not p.is_relative_to(root.resolve()) or not p.is_file():raise ValueError('ファイルがありません。')
 return p
def normal_image(data):
 with Image.open(io.BytesIO(data)) as source:
  if source.width*source.height>24_000_000:raise ValueError('画像は2400万画素以内にしてください。')
  image=ImageOps.exif_transpose(source).convert('RGBA')
  bg=Image.new('RGBA',image.size,'white');bg.alpha_composite(image);return bg.convert('RGB')
def register(data,name):
 im=normal_image(data);key=uuid.uuid4().hex;path=UPLOADS/(key+'.png');im.save(path)
 known=engine.identify(im)
 INPUTS[key]=dict(path=path,name=name,width=im.width,height=im.height,known=known)
 return dict(id=key,name=name,width=im.width,height=im.height,url='/input/'+key+'.png',known=known['id'] if known else None)
def options_for(p,data):
 if not isinstance(data,dict):raise ValueError('詳細設定の形式が不正です。')
 opts=dict(p['defaults']);opts.update({k:v for k,v in data.items() if k in opts})
 ranges={'density':(-100,100),'lines':(-100,100),'steps':(4,40),'seed':(0,2**53-1),'cfg':((.5 if p['engine']=='flux' else 1), (5 if p['engine']=='flux' else 12)),'denoise':(.1,1),'control':(0,1.5),'lora':(0,1.2),'second_denoise':(.05,.5)}
 for k,(lo,hi) in ranges.items():
  if isinstance(opts[k],bool) or not isinstance(opts[k],(float,int)) or not math.isfinite(opts[k]) or not lo<=opts[k]<=hi:raise ValueError('設定が範囲外です: '+k)
 for k in ['steps','seed','density','lines']:
  if int(opts[k])!=opts[k]:raise ValueError('整数で指定してください: '+k)
  opts[k]=int(opts[k])
 if str(opts['megapixels']) not in ['preset','1','2']:raise ValueError('解像度は標準・1MP・2MPから選んでください。')
 opts['megapixels']=str(opts['megapixels'])
 for k in ['description','instruction']:
  if not isinstance(opts[k],str) or len(opts[k])>2500:raise ValueError('追加説明が長すぎます。')
 return opts

USER_PRESETS=UserPresets(ROOT/'自分のプリセット/プリセット.json',engine.PRESETS,options_for)
def catalog():
 with LOCK:return dict(engine.DATA,presets=[dict(p,isUser=False) for p in engine.DATA['presets']]+USER_PRESETS.catalog())
def worker(p,item,opts,folder,mask):
 try:
  engine.save(folder/'プリセット.json',p)
  runtime=dict(p,id=p.get('baseId',p['id']))
  result,summary=engine.generate(runtime,item['path'],opts,folder,update,CANCEL,mask)
  relative=result.relative_to(OUTPUT).as_posix()
  update(status='done',message='完成しました。出力フォルダにも保存済みです。',phase='完了',result='/output/'+relative,output_path=str(result),summary=summary,step=None,total=None,finished=time.time())
 except Exception as error:
  (folder/'エラー.txt').write_text(traceback.format_exc(),'utf-8')
  update(status='cancelled' if CANCEL.is_set() else 'error',message=str(error),phase='停止',step=None,total=None,finished=time.time())
 finally:
  config_file=folder/'設定.json'
  if p.get('isUser') and config_file.exists():
   config=json.loads(config_file.read_text('utf8'));config.update(preset=p['id'],base_preset=p['baseId'],preset_title=p['title']);engine.save(config_file,config)
  engine.save(folder/'状態.json',state())

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,code,data):
  body=json.dumps(data,ensure_ascii=False).encode('utf-8');self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
 def valid_host(self):return self.headers.get('Host') in [f'127.0.0.1:{PORT}',f'localhost:{PORT}']
 def file(self,path,html=False):
  body=path.read_bytes()
  if html:body=body.replace(b'__TOKEN__',TOKEN.encode())
  self.send_response(200);self.send_header('Content-Type',('text/html; charset=utf-8' if html else mimetypes.guess_type(path.name)[0] or 'application/octet-stream'));self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store' if html else 'no-cache');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
 def do_GET(self):
  if not self.valid_host():return self.reply(403,{'error':'ローカル画面から開いてください。'})
  path=unquote(urlparse(self.path).path)
  try:
   if path=='/api/health':return self.reply(200,dict(app=APP_ID))
   if path=='/api/presets':return self.reply(200,catalog())
   if path=='/api/state':return self.reply(200,state())
   if path=='/api/history':
    rows=[]
    for folder in sorted(OUTPUT.iterdir(),reverse=True):
     if (folder/'完成.png').is_file():
      try:config=json.loads((folder/'設定.json').read_text('utf-8'));rows.append(dict(name=folder.name,preset=config['preset'],url='/output/'+folder.name+'/完成.png'))
      except (ValueError,KeyError):continue
     if len(rows)>=30:break
    return self.reply(200,rows)
   if path=='/':return self.file(HERE/'web/index.html',True)
   for prefix,root in [('/web/',HERE/'web'),('/input/',UPLOADS),('/output/',OUTPUT)]:
    if path.startswith(prefix):return self.file(safe(root,path[len(prefix):]))
   return self.reply(404,{'error':'見つかりません。'})
  except (ValueError,OSError):return self.reply(404,{'error':'ファイルが見つかりません。'})
 def do_POST(self):
  origin=self.headers.get('Origin')
  if not self.valid_host() or self.headers.get('X-App-Token')!=TOKEN or (origin and origin not in [f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}']):return self.reply(403,{'error':'画面を更新してからお試しください。'})
  try:
   length=int(self.headers.get('Content-Length','0'))
   if not 0<length<=50*1024**2:raise ValueError('画像は50MB以内にしてください。')
   body=self.rfile.read(length);path=urlparse(self.path).path
   if path=='/api/upload':return self.reply(200,register(body,unquote(self.headers.get('X-Filename','画像'))))
   data=json.loads(body)
   if not isinstance(data,dict):raise ValueError('送信内容の形式が不正です。')
   if path in ['/api/presets/create','/api/presets/delete']:
    with LOCK:
     if STATE['status']=='running':return self.reply(409,{'error':'生成が終わってからプリセットを保存・削除してください。'})
     if path.endswith('/create'):
      p=USER_PRESETS.create(data.get('source'),data.get('title'),data.get('description',''),data.get('options',{}))
      return self.reply(200,dict(preset=p,catalog=catalog()))
     USER_PRESETS.delete(data.get('id'));return self.reply(200,dict(catalog=catalog()))
   if path=='/api/cancel':CANCEL.set();return self.reply(200,dict(ok=True))
   if path=='/api/shutdown':
    if state()['status']=='running':return self.reply(409,{'error':'生成中は終了できません。'})
    self.reply(200,dict(ok=True));threading.Thread(target=self.server.shutdown,daemon=True).start();return
   if path=='/api/folder':subprocess.Popen(['explorer.exe',str(OUTPUT)]);return self.reply(200,dict(ok=True))
   if path=='/api/generate':
    with LOCK:p=USER_PRESETS.get(data.get('preset'))
    item=INPUTS.get(data.get('input'))
    if not p or not item:raise ValueError('原画とプリセットを選んでください。')
    opts=options_for(p,data.get('options',{}));mask=None
    if p['twoPass'] and not data.get('mask'):raise ValueError('顔や手など保護する範囲を、原画の上でなぞってください。')
    with LOCK:
     if STATE['status']=='running':return self.reply(409,{'error':'生成中です。完了または中止後にお試しください。'})
     folder=OUTPUT/(time.strftime('%Y%m%d_%H%M%S')+'_'+p['id']+'_'+uuid.uuid4().hex[:6]);folder.mkdir()
     if data.get('mask'):
      raw=base64.b64decode(data['mask'].split(',',1)[-1],validate=True)
      image=normal_image(raw);mask=folder/'保護範囲.png';image.save(mask)
     # Preserve original upload alongside output and the exact job settings.
     (folder/'元画像.png').write_bytes(item['path'].read_bytes())
     CANCEL.clear();STATE.clear();STATE.update(status='running',message='準備しています…',phase='準備',result=None,preset=p['id'],input='/input/'+item['path'].name,input_info=dict(id=data['input'],name=item['name'],width=item['width'],height=item['height'],url='/input/'+item['path'].name,known=item['known']['id'] if item['known'] else None),started=time.time(),step=None,total=None)
     threading.Thread(target=worker,args=(p,item,opts,folder,mask),daemon=True).start()
    return self.reply(202,state())
   return self.reply(404,{'error':'見つかりません。'})
  except (ValueError,KeyError,TypeError,OSError,Image.DecompressionBombError) as error:return self.reply(400,{'error':str(error)})

def browser():
 address=f'http://127.0.0.1:{PORT}'
 candidates=[Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Google/Chrome/Application/chrome.exe',Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe']
 exe=next((p for p in candidates if p.is_file()),None)
 if exe:subprocess.Popen([str(exe),'--app='+address,'--user-data-dir='+str(ROOT/'runtime/browser'),'--no-first-run','--disable-sync','--window-size=1280,940'],creationflags=subprocess.CREATE_NO_WINDOW)
 else:os.startfile(address)
def main():
 session=requests.Session();session.trust_env=False
 try:
  response=session.get(f'http://127.0.0.1:{PORT}/api/health',timeout=2)
  if response.json().get('app')==APP_ID:
   if '--open' in sys.argv:browser()
   return
 except (requests.RequestException,ValueError):pass
 server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler);server.daemon_threads=True
 if '--open' in sys.argv:threading.Timer(.7,browser).start()
 server.serve_forever()
if __name__=='__main__':
 try:main()
 except Exception:
  (ROOT/'記録/起動エラー.txt').write_text(traceback.format_exc(),'utf-8')
  import ctypes
  ctypes.windll.user32.MessageBoxW(None,'起動できませんでした。記録フォルダの「起動エラー.txt」を確認してください。','漫画変換',0x10)
