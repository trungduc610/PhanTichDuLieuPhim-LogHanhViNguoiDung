"""Read host memory and disk resources; no environment changes."""
import ctypes
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

class MemoryStatus(ctypes.Structure):
    _fields_ = [('length',ctypes.c_ulong),('load',ctypes.c_ulong)] + [(name,ctypes.c_ulonglong) for name in ['physical_total','physical_available','pagefile_total','pagefile_available','virtual_total','virtual_available','extended_available']]

status=MemoryStatus()
status.length=ctypes.sizeof(status)
if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
    raise ctypes.WinError()
root=Path(__file__).resolve().parents[2]
result={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'os':platform.platform(),
        'python':sys.version,'python_executable':sys.executable,'memory_bytes':{name:getattr(status,name) for name,_ in MemoryStatus._fields_[2:]},
        'disk_bytes':dict(zip(['total','used','free'],shutil.disk_usage(root))),
        'temporary_directory':os.environ.get('TMP'),
        'estimated_budget_bytes':{'generated_and_spool_and_sink_main':343339148*3,
                                  'sqlite_reconciliation_allowance':2000000000,
                                  'channel_and_export_allowance':4000000000,
                                  'docker_images_allowance':4000000000},
        'budget_note':'Allow about 12 GB overall including images, channel/export, inputs/Sink and SQLite; rolling files and channel journals depend on runtime.'}
print(json.dumps(result,ensure_ascii=False,indent=2))
