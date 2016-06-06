import subprocess

import sys

# Arguments to start gunicorn
args = [
    "gunicorn", "-w", "4", "--daemon", "--pid", sys.argv[2], "-b",
    "unix:bin/pipotserver.sock", "-m", "007", "-g", "www-data", "-u",
    "root",
    "--chdir=%s" % sys.argv[1], "--log-level", "debug",
    "--access-logfile", "%s/logs/access.log" % sys.argv[1],
    "--capture-output", "--log-file", "%s/logs/error.log" % sys.argv[1],
    "run:app"
]

subprocess.Popen(args)
