'use strict';
const $=id=>document.getElementById(id);
let token=document.querySelector('meta[name="app-token"]').content,uploading=false;
let catalog,preset,input=null,result=null,busy=false,maskURL=null,maskDirty=false,lastStatus='',maskImage=null,resultInput=null,resultPreset=null,serverResult=null,observedState='';
const fields=['density','lines','megapixels','steps','cfg','denoise','control','lora','second_denoise','description','instruction','seed'];
const strings=new Set(['megapixels','description','instruction']);
async function api(path,data,raw=false){
 let r;
 try{
  // Refresh before uploading: an expired session can reject a large body before
  // Chrome receives the error response. The same-origin check remains intact.
  const fresh=await fetch('/',{cache:'no-store'});
  if(!fresh.ok)throw Error('connection');
  const doc=new DOMParser().parseFromString(await fresh.text(),'text/html');
  const next=doc.querySelector('meta[name="app-token"]')?.content;
  if(!next)throw Error('connection');
  token=next;
  const headers={'X-App-Token':token};
  if(!raw)headers['Content-Type']='application/json';else headers['X-Filename']=encodeURIComponent(data.name);
  r=await fetch('/api/'+path,{method:'POST',headers,body:raw?data:JSON.stringify(data)});
 }catch(e){throw Error('アプリに接続できません。「漫画変換を起動」を開き直してください。');}
 const x=await r.json();if(!r.ok)throw Error(x.error||'操作に失敗しました。');return x;
}
function error(e){$('statusText').textContent=e.message||e;$('status').className='status error';}
function outputLabels(){for(const key of ['density','lines','denoise','control','lora','second_denoise']){const value=Number($(key).value);$(key+'Value').textContent=['density','lines'].includes(key)?(value===0?'標準':(value>0?'+':'')+value):value.toFixed(2);}}
function settings(){return Object.fromEntries(fields.map(k=>[k,strings.has(k)?$(k).value:Number($(k).value)]));}
function restoreSettings(){for(const key of fields)$(key).value=preset.defaults[key];outputLabels();}
function selectPreset(p){preset=p;$('presetCategory').textContent=p.category;$('presetTitle').textContent=p.title;$('presetDescription').textContent=p.description;$('presetMeta').textContent=(p.isUser?'自分のプリセット ｜ 元：'+p.baseTitle:p.id)+' ｜ '+(p.engine==='flux'?'画像編集AI':'SD系')+' ｜ 標準 約'+p.presetMP.toFixed(1)+'MP';
 $('deletePreset').disabled=busy||!p.isUser;$('deletePreset').textContent=p.isUser?'この自分のプリセットを削除':'基本プリセットは削除不可';$('presetSaveNotice').textContent=p.isUser?'この設定はPCに保存済みです。':'';
 $('denoiseRow').hidden=p.engine==='flux';$('controlRow').hidden=!p.hasControl;$('loraRow').hidden=!p.hasLora;$('secondRow').hidden=!p.twoPass;$('maskSection').hidden=!p.twoPass;$('cfg').max=p.engine==='flux'?5:12;$('descriptionHelp').textContent=p.engine==='flux'?'新しい原画はAIが読み取り、指示を準備します。補足が必要なときだけ入力してください。':'原画の人物や服装を補足すると安定しやすくなります（英語推奨）。';restoreSettings();maskHint();localStorage.setItem('manga-atelier-public-preset',p.id);$('presetDialog').close();}
function maskHint(){if(preset?.twoPass)$('maskHelp').textContent=maskDirty?'緑になぞった部分は、第1段階の描写を保護します。':input?.known==='01'?'見本の原画と一致しています。保存済みの顔・手の保護範囲を使います。変更する場合はなぞってください。':'顔や手などをなぞってください。その部分は第1段階の描写を保護します。';}
let category='すべて',showHidden=false;
let hiddenPresets=new Set();
try{hiddenPresets=new Set(JSON.parse(localStorage.getItem('manga-public-hidden')||'[]'));category=localStorage.getItem('manga-public-category')||'すべて';}catch(e){}
function storeView(){localStorage.setItem('manga-public-hidden',JSON.stringify([...hiddenPresets]));localStorage.setItem('manga-public-category',category);}
function presetList(cat=category){category=cat;storeView();$('presetGrid').replaceChildren();
 $('categories').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.textContent===category));
 const rows=catalog.presets.filter(p=>showHidden?!p.isUser&&hiddenPresets.has(p.id):(!hiddenPresets.has(p.id)||p.isUser)&&(category==='すべて'||(category==='自分のプリセット'?p.isUser:p.category===category)));
 $('presetViewHint').textContent=showHidden?'非表示の基本プリセット。再表示ボタンで戻せます。':rows.length+'件表示。非表示はこのブラウザーに保存されます。';
 $('manageHidden').textContent=showHidden?'通常の一覧に戻る':'非表示の基本を管理';
 for(const p of rows){const card=document.createElement('div'),b=document.createElement('button');card.className='preset-card';b.className='preset-option'+(p.id===preset.id?' selected':'');b.setAttribute('aria-label',p.id+' '+p.title);
 const info=document.createElement('span');info.className='info';for(const [tag,cls,text] of [['span','tag',(p.isUser?'自分のプリセット・':'')+p.category],['strong','',p.title],['p','',p.description],['small','',p.isUser?'元：'+p.baseTitle:p.id+' ｜ '+(p.engine==='flux'?'画像編集AI':'SD系')]]){const e=document.createElement(tag);e.className=cls;e.textContent=text;info.append(e);}b.append(info);b.onclick=()=>selectPreset(p);card.append(b);
 if(!p.isUser){const toggle=document.createElement('button');toggle.className='visibility-toggle';toggle.textContent=hiddenPresets.has(p.id)?'再表示':'非表示';toggle.onclick=()=>{if(hiddenPresets.has(p.id))hiddenPresets.delete(p.id);else hiddenPresets.add(p.id);presetList();};card.append(toggle);}
 $('presetGrid').append(card);}
 if(!rows.length){const empty=document.createElement('p');empty.textContent='該当するプリセットはありません。基本設定の再表示、または詳細設定から自分のプリセットを保存できます。';$('presetGrid').append(empty);}
}
function openPresets(){if(busy)return;showHidden=false;presetList();$('presetDialog').showModal();}
$('hideAllBuiltins').onclick=()=>{for(const p of catalog.presets)if(!p.isUser)hiddenPresets.add(p.id);presetList();};
$('restoreAllBuiltins').onclick=()=>{hiddenPresets.clear();showHidden=false;presetList();};
$('manageHidden').onclick=()=>{showHidden=!showHidden;presetList();};
$('choosePreset').onclick=openPresets;$('presetSummary').onclick=openPresets;$('closePresets').onclick=()=>$('presetDialog').close();
function setInput(v){input=v;maskURL=null;maskDirty=false;$('inputPreview').src=v.url;$('inputPreview').hidden=false;$('inputEmpty').hidden=true;$('inputName').textContent=v.name+' ｜ '+v.width+' × '+v.height;$('generate').disabled=busy;maskHint();$('statusText').textContent='準備できました。漫画化するを押してください。';}
async function upload(file){if(!file||busy||uploading)return;uploading=true;$('chooseFile').disabled=true;$('generate').disabled=true;$('regenerate').disabled=true;$('inputName').textContent='読み込み中：'+file.name;try{setInput(await api('upload',file,true));$('status').className='status';}catch(e){$('inputName').textContent='読み込めませんでした：'+file.name;error(e);}finally{uploading=false;$('chooseFile').disabled=busy;$('generate').disabled=busy||!input;$('regenerate').disabled=busy||!input||!result;}}
function chooseFile(){if(busy||uploading)return;$('file').value='';$('file').click();}
$('chooseFile').onclick=chooseFile;$('drop').onclick=chooseFile;
// The hidden input lives inside the clickable drop area. Do not reopen its picker.
$('file').onclick=e=>e.stopPropagation();
$('file').onchange=()=>{const file=$('file').files[0];$('file').value='';upload(file);};
for(const type of ['dragenter','dragover'])$('drop').addEventListener(type,e=>{e.preventDefault();$('drop').classList.add('dragover');});
for(const type of ['dragleave','drop'])$('drop').addEventListener(type,e=>{e.preventDefault();$('drop').classList.remove('dragover');});
$('drop').addEventListener('drop',e=>upload(e.dataTransfer.files[0]));
for(const key of ['density','lines','denoise','control','lora','second_denoise'])$(key).oninput=outputLabels;
$('resetSettings').onclick=restoreSettings;
let pendingPreset=null,presetSaving=false;
function updateCatalog(next){catalog=next;$('choosePreset').textContent=catalog.presets.length+'件から選ぶ →';}
$('savePreset').onclick=()=>{if(busy)return;pendingPreset={source:preset.id,options:settings()};$('savedPresetName').value=preset.title+'・調整';$('savedPresetDescription').value=preset.isUser?preset.description:'';$('savePresetBase').textContent='元の基本プリセット：'+(preset.baseTitle||preset.title);$('presetFormError').textContent='';$('savePresetDialog').showModal();$('savedPresetName').focus();$('savedPresetName').select();};
$('cancelPresetSave').onclick=()=>{if(!presetSaving)$('savePresetDialog').close();};
$('savePresetDialog').addEventListener('cancel',e=>{if(presetSaving)e.preventDefault();});
$('savePresetForm').onsubmit=async e=>{e.preventDefault();if(presetSaving||!pendingPreset)return;presetSaving=true;$('commitPreset').disabled=$('cancelPresetSave').disabled=true;try{const r=await api('presets/create',{...pendingPreset,title:$('savedPresetName').value,description:$('savedPresetDescription').value});updateCatalog(r.catalog);selectPreset(r.preset);$('savePresetDialog').close();$('presetSaveNotice').textContent='「'+r.preset.title+'」を保存しました。再起動後も使えます。';}catch(err){$('presetFormError').textContent=err.message;}finally{presetSaving=false;$('commitPreset').disabled=$('cancelPresetSave').disabled=false;}};
$('deletePreset').onclick=async()=>{if(busy||!preset.isUser)return;const target=preset;if(!confirm('「'+target.title+'」を削除しますか？\n基本プリセットと生成済み画像は残ります。'))return;$('deletePreset').disabled=true;try{const r=await api('presets/delete',{id:target.id});updateCatalog(r.catalog);selectPreset(catalog.presets.find(p=>p.id===target.baseId)||catalog.presets[0]);$('presetSaveNotice').textContent='「'+target.title+'」を削除しました。';}catch(err){error(err);$('deletePreset').disabled=busy||!preset.isUser;}};
function lock(value){busy=value;for(const id of ['chooseFile','choosePreset','presetSummary','resetSettings','editMask','clearMask','savePreset',...fields])$(id).disabled=value;$('deletePreset').disabled=value||!preset?.isUser;$('generate').disabled=value||!input;$('regenerate').disabled=value||!input||!result;$('cancel').hidden=!value;}
async function generate(){if(busy||uploading||!input)return;try{if(preset.twoPass&&!maskDirty&&input.known!=='01'){$('editMask').click();error('顔・手など保護したい範囲をなぞってから、漫画化してください。');return;}lock(true);$('statusText').textContent='生成を開始しています…';await api('generate',{input:input.id,preset:preset.id,options:settings(),mask:preset.twoPass&&maskDirty?maskURL:null});await poll();}catch(e){lock(false);error(e);}}
$('generate').onclick=generate;$('regenerate').onclick=generate;$('cancel').onclick=async()=>{try{await api('cancel',{});$('statusText').textContent='安全に停止しています…';}catch(e){error(e);}};
function showResult(url,original=null,pid=null){result=url;resultInput=original;resultPreset=pid;$('resultPreview').src=url;$('resultPreview').hidden=false;$('resultEmpty').hidden=true;for(const id of ['enlarge','compare','save'])$(id).disabled=false;$('regenerate').disabled=busy||!input;}
async function poll(){try{const r=await fetch('/api/state',{cache:'no-store'}),s=await r.json();if(s.status==='idle')return;const stateKey=s.status+':'+s.started;if(s.status!=='running'&&stateKey===observedState)return;observedState=stateKey;if(!input&&s.input_info)setInput(s.input_info);lock(s.status==='running');$('status').className='status '+s.status;$('statusText').textContent=s.message;$('resultBadge').textContent=({running:s.phase,done:'保存済み',error:'停止',cancelled:'中止'})[s.status]||'生成待ち';$('progress').hidden=!busy;if(s.total){$('progress').max=s.total;$('progress').value=s.step||0;}else $('progress').removeAttribute('value');let bits=[];if(s.status==='done'&&s.summary){bits.push('処理時間 '+s.summary.seconds+'秒');if(s.summary.ram_peak_percent!=null)bits.push('RAM最大 '+s.summary.ram_peak_percent+'%');if(s.summary.vram_peak_mib!=null)bits.push('VRAM最大 '+(s.summary.vram_peak_mib/1024).toFixed(1)+'GB');}else{if(s.elapsed)bits.push(Math.floor(s.elapsed)+'秒経過');if(s.total)bits.push(s.step+' / '+s.total+' ステップ');if(s.ram)bits.push('RAM '+s.ram+'%');}$('metrics').textContent=bits.join(' ｜ ');if(s.result&&s.result!==serverResult&&s.status==='done'){serverResult=s.result;showResult(s.result,s.input,s.preset);$('saveMessage').textContent='自動保存先：'+s.output_path;}if(s.status==='done'&&lastStatus!=='done')await loadHistory();lastStatus=s.status;}catch(e){if(busy)error('接続を確認しています。画面を更新せず、少しお待ちください。');}}
setInterval(poll,1300);
$('openFolder').onclick=async()=>{try{await api('folder',{});}catch(e){error(e);}};
$('save').onclick=async()=>{if(!result)return;try{const name='漫画変換_'+(resultPreset||'結果')+'_'+new Date().toISOString().slice(0,19).replace(/[T:]/g,'-')+'.png';let handle;if(window.showSaveFilePicker)handle=await window.showSaveFilePicker({suggestedName:name,types:[{description:'PNG画像',accept:{'image/png':['.png']}}]});const response=await fetch(result);if(!response.ok)throw Error('画像を読み込めませんでした。');const blob=await response.blob();if(handle){const writable=await handle.createWritable();await writable.write(blob);await writable.close();$('saveMessage').textContent='選んだ場所に「'+handle.name+'」を保存しました。';}else{const a=document.createElement('a'),u=URL.createObjectURL(blob);a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),20000);$('saveMessage').textContent='ブラウザーの保存先に書き出しました。自動保存した画像は「出力フォルダ」からも開けます。';}}catch(e){if(e.name!=='AbortError')error(e);}};
async function loadHistory(){const r=await fetch('/api/history');const rows=await r.json();$('historyList').replaceChildren();for(const row of rows){const b=document.createElement('button'),img=document.createElement('img'),text=document.createElement('span');img.src=row.url;img.loading='lazy';img.alt='';text.textContent=row.name;b.append(img,text);b.onclick=()=>{showResult(row.url,row.url.replace('完成.png','元画像.png'),row.preset);$('status').className='status';$('statusText').textContent='保存済みの画像を表示しています。';$('resultBadge').textContent='履歴';$('metrics').textContent='';$('saveMessage').textContent='履歴の画像を表示中：'+row.name;};$('historyList').append(b);}}
let viewImages=[];
async function viewer(compare){if(!result)return;$('viewPanes').replaceChildren();viewImages=[];for(const [label,url] of (compare&&resultInput?[['元画像',resultInput],['生成結果',result]]:[['生成結果',result]])){const pane=document.createElement('div'),heading=document.createElement('h3'),scroll=document.createElement('div'),img=document.createElement('img');pane.className='view-pane';heading.textContent=label;scroll.className='view-scroll';img.src=url;img.alt=label;img.draggable=false;scroll.append(img);pane.append(heading,scroll);$('viewPanes').append(pane);viewImages.push({img,scroll});let drag=null;scroll.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,left:scroll.scrollLeft,top:scroll.scrollTop};scroll.setPointerCapture(e.pointerId);};scroll.onpointermove=e=>{if(drag){scroll.scrollLeft=drag.left+drag.x-e.clientX;scroll.scrollTop=drag.top+drag.y-e.clientY;}};scroll.onpointerup=scroll.onpointercancel=()=>drag=null;await img.decode();}$('viewer').showModal();requestAnimationFrame(fit);}
function scaleView(percent){for(const {img} of viewImages){img.style.width=(img.naturalWidth*percent/100)+'px';img.style.height='auto';}$('zoomValue').textContent=percent+'%';$('zoom').value=percent;}
function fit(){for(const {img,scroll} of viewImages){const ratio=Math.min(scroll.clientWidth/img.naturalWidth,scroll.clientHeight/img.naturalHeight);img.style.width=Math.floor(img.naturalWidth*ratio)+'px';img.style.height='auto';scroll.scrollTop=scroll.scrollLeft=0;}$('zoomValue').textContent='全体';}
$('enlarge').onclick=() => viewer(false);$('resultPreview').onclick=()=>viewer(false);$('compare').onclick=()=>viewer(true);$('closeViewer').onclick=()=>$('viewer').close();$('fit').onclick=fit;$('actual').onclick=()=>scaleView(100);$('zoom').oninput=()=>scaleView(Number($('zoom').value));
const overlay=document.createElement('canvas'),canvas=$('maskCanvas'),ctx=canvas.getContext('2d'),brushCtx=overlay.getContext('2d');let drawing=false,lastPoint=null;
function drawMask(){if(!maskImage)return;ctx.drawImage(maskImage,0,0,canvas.width,canvas.height);ctx.save();ctx.globalAlpha=.48;const tinted=document.createElement('canvas');tinted.width=canvas.width;tinted.height=canvas.height;const t=tinted.getContext('2d');t.drawImage(overlay,0,0);t.globalCompositeOperation='source-in';t.fillStyle='#489e62';t.fillRect(0,0,tinted.width,tinted.height);ctx.drawImage(tinted,0,0);ctx.restore();}
$('editMask').onclick=async()=>{if(!input){error('先に原画を選んでください。');return;}maskImage=new Image();maskImage.src=input.url;await maskImage.decode();const scale=Math.min(1,850/maskImage.height);canvas.width=Math.round(maskImage.width*scale);canvas.height=Math.round(maskImage.height*scale);overlay.width=canvas.width;overlay.height=canvas.height;if(maskDirty&&maskURL){const old=new Image();old.src=maskURL;await old.decode();brushCtx.drawImage(old,0,0,overlay.width,overlay.height);const pix=brushCtx.getImageData(0,0,overlay.width,overlay.height);for(let i=0;i<pix.data.length;i+=4)pix.data[i+3]=pix.data[i];brushCtx.putImageData(pix,0,0);}drawMask();$('maskDialog').showModal();};
function point(e){const r=canvas.getBoundingClientRect();return {x:(e.clientX-r.left)*canvas.width/r.width,y:(e.clientY-r.top)*canvas.height/r.height};}
canvas.onpointerdown=e=>{drawing=true;lastPoint=point(e);canvas.setPointerCapture(e.pointerId);canvas.onpointermove(e);};canvas.onpointermove=e=>{if(!drawing)return;const pt=point(e);brushCtx.strokeStyle='white';brushCtx.lineWidth=Number($('brush').value);brushCtx.lineCap='round';brushCtx.beginPath();brushCtx.moveTo(lastPoint.x,lastPoint.y);brushCtx.lineTo(pt.x+.01,pt.y);brushCtx.stroke();lastPoint=pt;maskDirty=true;drawMask();};canvas.onpointerup=canvas.onpointercancel=()=>drawing=false;
function clearMask(){brushCtx.clearRect(0,0,overlay.width,overlay.height);maskDirty=false;maskURL=null;drawMask();maskHint();}
$('clearMask').onclick=clearMask;$('eraseMask').onclick=clearMask;
$('closeMask').onclick=()=>{if(maskDirty){const out=document.createElement('canvas');out.width=overlay.width;out.height=overlay.height;const c=out.getContext('2d');c.fillStyle='black';c.fillRect(0,0,out.width,out.height);c.drawImage(overlay,0,0);maskURL=out.toDataURL('image/png');}maskHint();$('maskDialog').close();};
$('maskDialog').addEventListener('cancel',e=>{e.preventDefault();$('closeMask').click();});
(async()=>{try{catalog=await(await fetch('/api/presets')).json();$('choosePreset').textContent=catalog.presets.length+'件から選ぶ →';for(const cat of ['すべて','自分のプリセット','グレースケール','線画','漫画調','ベタ']){const b=document.createElement('button');b.textContent=cat;b.onclick=()=>{showHidden=false;presetList(cat);$('categories').querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));};$('categories').append(b);}selectPreset(catalog.presets.find(p=>p.id===localStorage.getItem('manga-atelier-public-preset'))||catalog.presets.find(p=>p.id==='A15'));await loadHistory();await poll();}catch(e){error(e);}})();
