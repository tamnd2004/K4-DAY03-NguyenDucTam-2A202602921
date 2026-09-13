"""Verify submission evidence and scan staged Git content without exposing keys."""
import json
import subprocess
import sys
from pathlib import Path
from dotenv import dotenv_values
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from tools import TOOLS_SCHEMA

def git(*args):
    return subprocess.check_output(['git','-c',f'safe.directory={ROOT.as_posix()}',*args],cwd=ROOT)

def main():
    for schema in TOOLS_SCHEMA:
        Draft202012Validator.check_schema(schema['parameters'])
    live=json.loads((ROOT/'docs/trace_waterfall.json').read_text(encoding='utf-8'))
    assert live['passed']==live['total']==8,'Live suite must pass all eight cases'
    assert len(live['runs'])==8
    for run in live['runs']:
        assert run['live'] and run['status']=='completed' and run['model']=='gemini-3.5-flash-lite'
        actions=[e for e in run['trace'] if e['action_type']=='ACTION']
        observations=[e for e in run['trace'] if e['action_type']=='OBSERVATION']
        assert [e['call_id'] for e in actions]==[e['call_id'] for e in observations]
        assert run['trace'][-1]['action_type']=='FINAL_ANSWER'
        assert len(actions)==run['tool_calls']
    secrets=[v.encode() for k,v in dotenv_values(ROOT/'.env').items() if any(t in k for t in ('KEY','TOKEN','SECRET')) and v and len(v)>16 and not v.startswith('your_')]
    files=git('ls-files','-z').decode().split('\0')
    for name in filter(None,files):
        assert name!='.env' and not name.startswith(('.venv/','.tmp/','data/')),f'Runtime file staged: {name}'
        content=git('show',':'+name)
        assert not any(secret in content for secret in secrets),f'Credential detected in {name}; remove before publishing'
    print('PASS: four JSON Schemas; 8 live runs on exact model; action/observation correlation; staged tree has no configured credentials or runtime data.')

if __name__=='__main__':main()
