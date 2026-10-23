"""User settings only. Immutable built-ins remain in presets.json."""
import copy,json,os,shutil,uuid
from datetime import datetime
from pathlib import Path

class UserPresets:
 def __init__(self,path,builtins,validate_options):
  self.path=Path(path);self.builtins=builtins;self.validate_options=validate_options
  self.rows=[]
  if self.path.exists():
   document=json.loads(self.path.read_text('utf8'))
   if document.get('version')!=1 or not isinstance(document.get('presets'),list):raise ValueError('自分のプリセットの保存形式を確認してください。')
   ids=set()
   for row in document['presets']:
    if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id'].startswith('USER-') or row['id'] in ids:raise ValueError('自分のプリセットのIDが不正です。')
    self._text(row.get('title'),'名前',80,True);self._text(row.get('description'),'説明',500)
    base=self.builtins.get(row.get('baseId'))
    if not base:raise ValueError('自分のプリセットの元の基本設定が見つかりません。')
    row['options']=self.validate_options(base,row['options']);ids.add(row['id'])
    self.rows.append(row)
 def _text(self,value,label,limit,required=False):
  if not isinstance(value,str) or len(value)>limit or (required and not value.strip()):raise ValueError(label+'を'+str(limit)+'文字以内で入力してください。')
  return value.strip()
 def catalog(self):
  return [self.expand(r) for r in self.rows]
 def expand(self,row):
  p=copy.deepcopy(self.builtins[row['baseId']]);p.update(id=row['id'],title=row['title'],description=row['description'] or '保存した詳細設定。',defaults=copy.deepcopy(row['options']),isUser=True,baseId=row['baseId'],baseTitle=self.builtins[row['baseId']]['title'],createdAt=row['createdAt'])
  return p
 def get(self,pid):
  if pid in self.builtins:return self.builtins[pid]
  row=next((r for r in self.rows if r['id']==pid),None)
  return self.expand(row) if row else None
 def _commit(self,rows):
  self.path.parent.mkdir(parents=True,exist_ok=True)
  temp=self.path.with_name(self.path.name+'.'+uuid.uuid4().hex+'.tmp')
  try:
   with temp.open('w',encoding='utf8') as f:
    json.dump(dict(version=1,presets=rows),f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
   if self.path.exists():shutil.copy2(self.path,self.path.with_suffix('.前回.json'))
   os.replace(temp,self.path)
  finally:
   if temp.exists():temp.unlink()
  self.rows=rows
 def create(self,source,title,description,options):
  p=self.get(source)
  if not p:raise ValueError('元のプリセットが見つかりません。画面を更新してください。')
  title=self._text(title,'名前',80,True);description=self._text(description,'説明',500)
  if len(self.rows)>=1000:raise ValueError('保存上限の1000件です。不要なプリセットを削除してください。')
  row=dict(id='USER-'+uuid.uuid4().hex,baseId=p.get('baseId',p['id']),title=title,description=description,options=self.validate_options(p,options),createdAt=datetime.now().astimezone().isoformat())
  self._commit(self.rows+[row]);return self.expand(row)
 def delete(self,pid):
  if pid in self.builtins:raise ValueError('基本プリセットは削除できません。')
  if not any(r['id']==pid for r in self.rows):raise ValueError('削除するプリセットが見つかりません。')
  self._commit([r for r in self.rows if r['id']!=pid])
