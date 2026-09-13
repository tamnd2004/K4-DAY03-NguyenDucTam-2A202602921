"""Print Gemini model identifiers only; never print credentials or raw API errors."""
import os
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).resolve().parents[1]/'.env')
parser=argparse.ArgumentParser()
parser.add_argument('--probe',action='store_true')
args=parser.parse_args()
try:
    with genai.Client(api_key=os.environ['GEMINI_API_KEY']) as client:
        if args.probe:
            response=client.models.generate_content(model=os.environ.get('LLM_MODEL','gemini-3.5-flash-lite'),contents='Reply OK only.')
            print('API probe:',response.text)
        else:
            for model in client.models.list():
                if 'gemini' in model.name and 'generateContent' in (model.supported_actions or []):
                    print(model.name)
except Exception as exc:
    print('Model discovery failed:',getattr(exc,'code',type(exc).__name__))
    message=getattr(exc,'message','')
    if message:
        print(message.replace(os.environ['GEMINI_API_KEY'],'[REDACTED]')[:2000])
    sys.exit(1)
