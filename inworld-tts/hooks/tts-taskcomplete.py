import subprocess, os, sys, re, shutil

def to_posix(p):
    p = p.replace('\\', '/')
    m = re.match(r'^([A-Za-z]):', p)
    if m:
        p = '/' + m.group(1).lower() + p[2:]
    return p

def find_git_bash():
    for d in [
        os.path.join(os.environ.get('PROGRAMFILES', r'C:\Program Files'), 'Git', 'usr', 'bin'),
        os.path.join(os.environ.get('PROGRAMFILES', r'C:\Program Files'), 'Git', 'bin'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Git', 'usr', 'bin'),
        r'C:\msys64\usr\bin',
    ]:
        p = os.path.join(d, 'bash.exe')
        if os.path.exists(p):
            return p
    return shutil.which('bash') or 'bash'

bash = find_git_bash() if sys.platform == 'win32' else 'bash'
here = to_posix(os.path.dirname(os.path.abspath(__file__)))
sys.exit(subprocess.run(
    [bash, here + '/scripts/tts-taskcomplete-notify.sh'],
    env=os.environ,
).returncode)
