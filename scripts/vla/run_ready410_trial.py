#!/usr/bin/env python3
"""One corrected READY access or ENTRY stage; requires an evidence-bound release."""
from ready410_trial_contract import load_trial_stage, qualify_trial
from run_entry410_stage import main

if __name__=='__main__':
    main(loader=load_trial_stage,qualifier=qualify_trial,description=__doc__,label='READY410 H63')
