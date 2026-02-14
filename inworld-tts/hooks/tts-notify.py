import subprocess, os, sys, re, shutil

def to_posix(p):
    p = p.replace('\\', '/')
    m = re.match(r'^([A-Za-z]):', p)
    if m:
        p = '/' + m.group(1).lower() + p[2:]
    return p

bash = shutil.which('bash') or 'bash'
here = to_posix(os.path.dirname(os.path.abspath(__file__)))
sys.exit(subprocess.run(
    [bash, here + '/scripts/inworld-tts-notify.sh'],
    env=os.environ,
).returncode)
