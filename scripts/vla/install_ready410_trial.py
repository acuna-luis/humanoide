#!/usr/bin/env python3
"""Plan or install the corrected READY/ENTRY tasks on disk; never reload or move."""
from pathlib import Path
from install_entry410_stages import main
from ready410_trial_contract import all_trial_stages

if __name__=='__main__':
    main(stage_loader=all_trial_stages,profile='ready410_head063',description=__doc__,
         extra_sources=tuple(Path(__file__).with_name(n) for n in (
             'install_ready410_trial.py','ready410_trial_contract.py','audit_ready_controller_contract.py')))
