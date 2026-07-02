import subprocess, sys, time

port = sys.argv[1] if len(sys.argv) > 1 else '8888'

ps = '''
$proc = Get-NetTCPConnection -LocalPort {0} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
if ($proc) {{
    Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
    Write-Output "Stopped process $proc on port {0}"
}} else {{
    Write-Output "No process on port {0}"
}}
'''.format(port)

r = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True, timeout=10)
out = (r.stdout or '') + (r.stderr or '')
print(out.strip()[:300])
time.sleep(1.5)
print('Done')
sys.exit(0)
