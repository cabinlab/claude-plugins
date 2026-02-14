import subprocess, os, sys, re, shutil

def to_posix(p):
    p = p.replace('\\', '/')
    m = re.match(r'^([A-Za-z]):', p)
    if m:
        p = '/' + m.group(1).lower() + p[2:]
    return p

here = to_posix(os.path.dirname(os.path.abspath(__file__)))
sys.exit(subprocess.run(
    [shutil.which('bash') or 'bash', here + '/scripts/tts-subagentstop-notify.sh'],
    env=os.environ,
).returncode)
