#!/usr/bin/env python3
"""Offline exact-match English localization, including dynamic field values.

Unknown Chinese is rejected, never replaced by a generic success/error message.
This helper is not connected to the robot's TtsClient.
"""
import argparse,json,re,sys
from pathlib import Path

def localize(text,catalog):
 table={r['zh']:r['en'] for r in catalog if r.get('en') and r.get('kind')!='dynamic'}
 if text in table:return table[text]
 if not re.search('[\u4e00-\u9fff]',text):return text
 raise ValueError('Unmapped Chinese text: extend reviewed catalog before dispatch')
def main():
 p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--text',required=True);a=p.parse_args()
 print(localize(a.text,json.loads(a.catalog.read_text())))
if __name__=='__main__':main()
