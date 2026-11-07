"""One-command reproducible analysis. Run from any directory."""
from pathlib import Path
import subprocess,sys,os
root=Path(__file__).resolve().parent
for filename in ['run_analysis.py','build_reports.py']:
    subprocess.run([sys.executable,str(root/'src'/filename)],check=True,cwd=root)
print('Done. Open reports/dashboard.html and reports/results.md.')
