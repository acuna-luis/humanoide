#!/usr/bin/env python3
"""Prepare offline ENTRY410 stages; no installation, ROS or execution transport."""
from prepare_entry360_stages import main

if __name__ == '__main__':
    main(expected_candidate='episode_000410')
