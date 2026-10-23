"""Use the user's separately obtained official template; do not ship its prompt."""
import json
from config import engine_config

def template_prompts():
 template=json.loads(engine_config('flux')['prompt_template'].read_text('utf-8-sig'))
 try:
  sub=next(g for g in template['definitions']['subgraphs'] if g['name']=='Prompt Upsampler')
  system=next(n for n in sub['nodes'] if n['id']==114)['widgets_values'][0]
  form=next(n for n in sub['nodes'] if n['id']==134)['widgets_values'][0]
  if not isinstance(system,str) or not isinstance(form,str) or '{a}' not in form:raise ValueError()
  return system,form
 except (KeyError,StopIteration,IndexError,ValueError):
  raise ValueError('公式テンプレートの構造が対応版と異なります。AI_INSTALL.mdの固定revisionを確認してください。') from None

def graph(image,prompt,seed):
 system,form=template_prompts()
 def node(kind,**inputs):return dict(class_type=kind,inputs=inputs)
 settings={'clip':['1',0],'image':['2',0],'prompt':form.replace('{a}',prompt.strip()),'system_prompt':system,
  'max_length':3584,'sampling_mode':'on','sampling_mode.temperature':1.,'sampling_mode.top_k':1,
  'sampling_mode.top_p':.95,'sampling_mode.min_p':0.,'sampling_mode.repetition_penalty':1.,
  'sampling_mode.seed':seed,'sampling_mode.presence_penalty':0.,'thinking':False,
  'use_default_template':True,'mtp':'off'}
 return {'1':node('CLIPLoader',clip_name='qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors',type='flux3',device='default'),
  '2':node('LoadImage',image=image),'3':node('TextGenerate',**settings),'4':node('PreviewAny',source=['3',0])}
