"""A hostile log path must retain the command's stdout/exit contract."""
import subprocess
import sys

def test_symlink_log_error_is_mapped(tmp_path):
    outside=tmp_path/'outside.jsonl'; outside.write_text('unchanged')
    b=tmp_path/'build'; b.mkdir(); (b/'log.jsonl').symlink_to(outside)
    r=subprocess.run([sys.executable,'-m','cards','check','--build',str(b)],capture_output=True,text=True)
    assert r.returncode==2 and r.stdout.startswith('ERROR\n') and 'escapes build' in r.stdout
    assert not r.stderr and outside.read_text()=='unchanged'
