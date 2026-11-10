"""Offline parsing tests only; never contacts Anki."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('q1_probe', Path(__file__).resolve().parents[2]/'tools/q1_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

@pytest.mark.parametrize('body,content_type', [
    (b'{"jsonrpc":"2.0","id":2,"result":{"tools":[]}}', 'application/json'),
    (b': keepalive\r\nevent: message\r\ndata: {"jsonrpc":"2.0","method":"progress"}\r\n\r\ndata: {"jsonrpc":"2.0",\r\ndata: "id":2,"result":{"tools":[]}}\r\n\r\n', 'text/event-stream')])
def test_reply_decoding(body, content_type):
    assert probe.decode_reply(body, content_type, 2)['result']['tools'] == []
