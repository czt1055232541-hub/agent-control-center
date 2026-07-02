import subprocess, json, sys, os

def run_pwsh(script):
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command', script],
        capture_output=True, text=True, timeout=15,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    )
    return r.stdout.strip() or r.stderr.strip() or ''

info = {}
info['OS'] = run_pwsh('(Get-CimInstance Win32_OperatingSystem).Caption')
info['Build'] = run_pwsh('[Environment]::OSVersion.Version.Build')
info['OSArch'] = run_pwsh('[Environment]::Is64BitProcess')
info['HyperV'] = run_pwsh('(Get-WmiObject -Class Win32_ComputerSystem).HypervisorPresent')
info['VirtFW'] = run_pwsh('(Get-CimInstance Win32_Processor | Select-Object -First 1).VirtualizationFirmwareEnabled')
info['SLAT'] = run_pwsh('(Get-CimInstance Win32_Processor | Select-Object -First 1).SecondLevelAddressTranslationExtensions')
info['BuildOK'] = run_pwsh('[Environment]::OSVersion.Version.Build -ge 19041')
info['WSL_Status'] = run_pwsh('wsl --status 2>&1')
info['Docker_Exists'] = str(os.path.exists(r'C:\Program Files\Docker\Docker\Docker Desktop.exe'))
info['FreeSpace_E'] = run_pwsh('(Get-PSDrive E).Free')

print(json.dumps(info, indent=2, ensure_ascii=False))
