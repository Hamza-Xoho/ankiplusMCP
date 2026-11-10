#!/usr/bin/env python3
"""Manual Q-1 spike. Deliberately outside the offline cards package."""
import json
import urllib.request

URL = 'http://127.0.0.1:3141/'

def decode_reply(body, content_type, request_id):
    text = body.decode('utf-8')
    if 'text/event-stream' not in content_type:
        return json.loads(text)
    # SSE events may contain several data lines; ignore comments and notifications.
    data = []
    for line in text.replace('\r\n', '\n').split('\n') + ['']:
        if line.startswith('data:'):
            data.append(line[5:].lstrip(' '))
        elif not line and data:
            value = json.loads('\n'.join(data))
            data = []
            if value.get('id') == request_id:
                return value
    raise ValueError('SSE response has no matching JSON-RPC reply')

def request(method, request_id, params=None, session=None):
    payload = {'jsonrpc': '2.0', 'id': request_id, 'method': method}
    if params is not None:
        payload['params'] = params
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
    if session:
        headers['Mcp-Session-Id'] = session
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=10) as reply:
        # Read through the matching event instead of waiting for a persistent SSE stream to close.
        if 'text/event-stream' in reply.headers.get('Content-Type', ''):
            chunks = []
            for raw in reply:
                chunks.append(raw)
                if raw.strip() == b'':
                    try:
                        response = decode_reply(b''.join(chunks), 'text/event-stream', request_id)
                        break
                    except ValueError:
                        continue
            else:
                raise ValueError('SSE stream ended without reply')
        else:
            response = decode_reply(reply.read(), 'application/json', request_id)
        if response.get('id') != request_id or response.get('jsonrpc') != '2.0':
            raise ValueError('invalid JSON-RPC response')
        if 'error' in response:
            raise ValueError(str(response['error']))
        return response['result'], reply.headers.get('Mcp-Session-Id', session)

def main():
    try:
        _, session = request('initialize', 1, {'protocolVersion': '2024-11-05', 'capabilities': {},
                                            'clientInfo': {'name': 'cards-q1-probe', 'version': '0.1.0'}})
        result, _ = request('tools/list', 2, session=session)
        tools = result['tools']
        if not isinstance(tools, list):
            raise ValueError('tools is not a list')
        print(f'Q1 OK: {len(tools)} tools')
        return 0
    except Exception as exc:
        print(f'Q1 FAIL: {str(exc).replace(chr(10), " ")}')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
