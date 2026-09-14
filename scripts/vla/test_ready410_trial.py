import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import yaml
from prepare_entry360_stages import JOINT_ORDER,staged_path,stage_xml
from prepare_vla_entry_bundle import digest
from ready410_trial_contract import load_trial_stage,all_trial_stages,qualify_trial


class TrialTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.ref=self.root/'reference.json';self.ref.write_text('{}')
        q0=np.zeros(20);ready=np.linspace(-.2,.2,20);ready[JOINT_ORDER.index('head_pitch_joint')]=-.63
        self.reviews={};self.stages={}
        for part,start,end in [('access',q0,ready),('entry',ready,np.linspace(-.3,.3,20))]:
            directory=self.root/part;directory.mkdir();points,stages=staged_path(start,end)
            r=dict(schema='cruzr-measured-start-ready-access-offline-v1' if part=='access' else 'cruzr-entry410-stages-offline-v1',
                candidate='episode_000410',joint_order=JOINT_ORDER,stages=stages,
                position_source='/mc/whole_joint_states:name',actuator_coordinates_used_for_geometry=False,
                access_waypoints_20d_rad=[x.tolist() for x in points],
                sources_sha256={str(self.ref):digest(self.ref)},model_sources={str(self.ref):digest(self.ref)},
                configured_limits_check=dict(configuration_files_match_current_hashes=True),
                geometry_audit=dict(timed_out=False,pairs=[dict(pair=['hand','scene:table'],status='CERTIFIED_AFFINE_INTERVALS')]),drafts_sha256={})
            for i,s in enumerate(stages,1):
                for d in ('forward','reverse'):
                    name=f'DRAFT_access_{i:02d}_{d}.xml' if part=='access' else f'DRAFT_{i:02d}_{s["type"]}_{s["location"]}_{d}.xml'
                    xml=directory/name;xml.write_text(stage_xml(s,d=='reverse'));r['drafts_sha256'][name]=digest(xml)
            path=directory/'review.json';path.write_text(json.dumps(r));self.reviews[part]=path;self.stages[part]=stages
        groups={}
        for s in self.stages['access']:
            key=(s['location']+'_arm' if s['type']=='arm' else s['type'])+'_controller'
            groups[key]=dict(joints=s['joint_names'],controller_dof=len(s['joint_names']))
        records={'/cruzr_s2_v1_mc_config/config/controllers_config.yaml':groups,
                 '/ecat_hardware/transmissions.yaml':dict(transmissions={n:dict(joint=dict(name=n,limit=dict(lower=-2,upper=2))) for n in JOINT_ORDER})}
        import hashlib
        self.hw=self.root/'hardware.json';self.hw.write_text(json.dumps({p:dict(text=yaml.safe_dump(v),sha256=hashlib.sha256(yaml.safe_dump(v).encode()).hexdigest()) for p,v in records.items()}))
        self.manifests={}
        for part in ('access','entry'):
            values=dict(access_review=str(self.reviews['access']),entry_review=str(self.reviews['entry']),reference=str(self.ref),hardware_snapshot=str(self.hw))
            sources=[Path(v) for v in values.values()]+[Path(__file__).with_name(n) for n in ('ready410_trial_contract.py','audit_ready_controller_contract.py')]
            m=dict(schema='cruzr-ready410-head063-trial-v1',part=part,bindings={str(f.resolve()):digest(f) for f in sources},**values)
            path=self.root/(part+'.json');path.write_text(json.dumps(m));self.manifests[part]=path

    def mutate_manifest(self,part,fn):
        path=self.manifests[part];m=json.loads(path.read_text());fn(m);path.write_text(json.dumps(m))

    def test_twenty_tasks_and_reverse(self):
        tasks=set()
        for part,p in self.manifests.items():
            for i in range(1,6):
                a,b=(load_trial_stage(p,i,d) for d in ('forward','reverse'))
                self.assertEqual(a['start'],b['end']);self.assertEqual(a['end'],b['start'])
                self.assertFalse(a['physical_approval']);tasks.update((a['task'],b['task']))
        self.assertEqual(len(tasks),20)

    def test_missing_binding_rejected(self):
        self.mutate_manifest('access',lambda m:m['bindings'].pop(str(self.reviews['entry'])))
        with self.assertRaises(ValueError):load_trial_stage(self.manifests['access'],1,'forward')

    def test_changed_other_part_rejected(self):
        self.reviews['entry'].write_text('{}')
        with self.assertRaises(ValueError):load_trial_stage(self.manifests['access'],1,'forward')

    def test_xml_change_rejected(self):
        xml=self.reviews['access'].parent/'DRAFT_access_01_forward.xml';xml.write_text('<changed/>')
        with self.assertRaises(ValueError):load_trial_stage(self.manifests['access'],1,'forward')

    def test_hardware_limit_rejected_even_after_rehash(self):
        hw=json.loads(self.hw.read_text());p='/ecat_hardware/transmissions.yaml';v=yaml.safe_load(hw[p]['text'])
        v['transmissions']['head_pitch_joint']['joint']['limit']['lower']=-.5
        import hashlib
        hw[p]['text']=yaml.safe_dump(v);hw[p]['sha256']=hashlib.sha256(hw[p]['text'].encode()).hexdigest();self.hw.write_text(json.dumps(hw))
        self.mutate_manifest('access',lambda m:m['bindings'].update({str(self.hw):digest(self.hw)}))
        with self.assertRaises(ValueError):load_trial_stage(self.manifests['access'],1,'forward')

    def test_no_release_from_owner_boolean(self):
        p=self.root/'release.json';p.write_text('{"authorized":true}')
        with self.assertRaises(ValueError):qualify_trial(p,load_trial_stage(self.manifests['access'],1,'forward'))

    def test_bundle_integrity(self):
        b=self.root/'bundle.json';m=dict(schema='cruzr-ready410-head063-bundle-v1',manifests={k:str(v) for k,v in self.manifests.items()},manifests_sha256={str(v):digest(v) for v in self.manifests.values()})
        b.write_text(json.dumps(m));self.assertEqual(len(all_trial_stages(b)),20)
        m['manifests_sha256'].pop(str(self.manifests['entry']));b.write_text(json.dumps(m))
        with self.assertRaises(ValueError):all_trial_stages(b)


if __name__=='__main__':unittest.main()
