"""CLI protocol adapters. Model names are verified by preflight, never guessed here."""
import json
from pathlib import Path
from core import Stop, require

def build_argv(c,cwd,schema,output,session=None):
    if c['provider']=='codex':
        a=[c['cli'],'--no-daemon','-a','never','-s',c.get('sandbox','workspace-write'),'exec']
        if session: a+=['resume']
        else: a+=['-C',str(cwd)]
        a+=['-m',c['model']]
        if c['effort']!='model-default': a+=['-c','model_reasoning_effort='+json.dumps(c['effort'])]
        a+=['--json','--output-schema',str(schema),'-o',str(output)]
        if c.get('images'):
            require(not session or len(c['images'])==1,'Multiple resume image attachments require verified CLI support')
            a+=['--image',*c['images']]
        if session: a+=[session]
        return a+['-']
    if c['provider']=='claude':
        # No permission bypass, model alias, implicit resume or provider fallback.
        require(not c.get('images'),'Claude image attachment needs local verification; NEEDS_USER_INPUT')
        a=[c['cli'],'-p','--model',c['model'],'--output-format','json',
           '--permission-mode','dontAsk','--strict-mcp-config',
           '--settings',json.dumps({'fallbackModel':[],'switchModelsOnFlag':False})]
        if c['effort']!='model-default': a+=['--effort',c['effort']]
        if Path(schema).exists(): a+=['--json-schema',Path(schema).read_text()]
        if session: a+=['--resume',session]
        return a
    if c['provider']=='fake':
        return [c['cli'],*c.get('prefix_args',[]),'--model',c['model'],'--effort',c['effort'],
                '--session',session or '', '--output',str(output)]
    raise Stop('Unknown provider')

def parse_output(provider,text,final_text=''):
    if provider=='codex':
        try: events=[json.loads(x) for x in text.splitlines() if x.strip()]
        except ValueError as e: raise Stop('Malformed/truncated JSONL output') from e
        require(events and any(e.get('type')=='turn.completed' for e in events),'CLI turn did not complete')
        require(not any(e.get('type') in ('turn.failed','error') for e in events),'CLI reported failure')
        ids=[e['thread_id'] for e in events if e.get('type')=='thread.started' and e.get('thread_id')]
        require(ids and len(set(ids))==1,'Missing or conflicting session ID')
        messages=[e.get('item',{}).get('text') for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
        payload=final_text.strip() or (messages[-1] if messages else '')
        try: report=json.loads(payload)
        except ValueError as e: raise Stop('Missing structured final report') from e
        usage=[e.get('usage') for e in events if e.get('type')=='turn.completed']
        return {'session_id':ids[0],'report':report,'usage':usage[-1] if usage else None,
                'cost':None,'compaction_observed':any('compact' in e.get('type','') for e in events)}
    try: result=json.loads(text)
    except ValueError as e: raise Stop('Malformed/truncated JSON result') from e
    if provider=='claude':
        require(result.get('type')=='result' and not result.get('is_error') and result.get('subtype','success')=='success','Claude invocation did not complete')
        report=result.get('structured_output')
        if report is None:
            try: report=json.loads(result.get('result',''))
            except ValueError as e: raise Stop('Missing Claude structured report') from e
    else: report=result.get('report')
    require(result.get('session_id') and isinstance(report,dict),'Missing session ID or report')
    return {'session_id':result['session_id'],'report':report,'usage':result.get('usage'),
            'cost':result.get('total_cost_usd'),'compaction_observed':False}
