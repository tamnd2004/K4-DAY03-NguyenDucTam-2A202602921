import json
from fastapi.testclient import TestClient
from web import app

def test_web_state_and_input_validation(db_path):
    with TestClient(app) as client:
        assert client.get('/').status_code==200
        state=client.get('/api/state').json()
        assert len(state['employees'])==3
        assert 'api_key' not in json.dumps(state).lower()
        assert client.post('/api/chat',json={'message':' '}).status_code==422
        assert client.post('/api/chat',json={'message':'hello','mode':'invalid'}).status_code==422
        assert client.post('/api/chat',json={'message':'hello','mode':'mock'},headers={'Origin':'https://unrelated.example'}).status_code==403

def test_streaming_chat_and_persistent_readback(db_path):
    with TestClient(app) as client:
        response=client.post('/api/chat',json={'mode':'mock','message':'Tạo đơn nghỉ phép cho NV001 từ 21/09/2026 đến 23/09/2026, lý do: việc gia đình.'})
        assert response.status_code==200
        frames=[json.loads(line) for line in response.text.splitlines()]
        assert frames[0]['type']=='event'
        result=frames[-1]['result']
        assert result['status']=='completed'
        assert result['tool_calls']==3
        assert len(client.get('/api/state').json()['requests'])==1
