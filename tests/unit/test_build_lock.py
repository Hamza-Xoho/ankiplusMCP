from filelock import FileLock

from test_build_command import cli, fixture


def test_continue_refuses_while_another_process_owns_build_lock(tmp_path):
    folder, _ = fixture(tmp_path)
    with FileLock(folder / '.build.lock'):
        result = cli('build', '--continue', '--build', folder, cwd=tmp_path)
    assert result.returncode == 3
    assert 'busy' in result.stdout.lower()
