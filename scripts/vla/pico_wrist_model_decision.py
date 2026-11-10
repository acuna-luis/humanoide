#!/usr/bin/env python3
"""Validate a complete one-shot SmolVLA relay and a fixed wrist candidate.

This module does not connect to the robot, send a goal or qualify VLA control.
The checkpoint and image hashes are relay claims, not runtime attestation. PC
monotonic times do not establish camera-to-PC latency or physical safety.
"""
import hashlib
import json
import math
import re
import uuid
import xml.etree.ElementTree as ET

import prepare_pico_wrist_native_probe as probe

MODEL_SHA256 = 'e707eea07b58e14b979e78463b94ba75a52b1c18abf8076aebc8aa34ac77f8da'
MAX_AGE_NS = 10_000_000_000
REFERENCE_TOLERANCE_RAD = .002
STATIONARY_RAD_S = .001


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _digest(value):
    return isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value) is not None


def _uuid(value):
    if not isinstance(value,str):
        return False
    try:
        u=uuid.UUID(value)
        return str(u)==value and u.int != 0
    except (ValueError,AttributeError):
        return False


def _named(names, positions, velocities):
    if (not isinstance(names,list) or len(names)!=20 or any(not isinstance(n,str) for n in names)
            or len(set(names))!=20 or set(names)!=set(probe.BODY)
            or not isinstance(positions,list) or len(positions)!=20
            or not isinstance(velocities,list) or len(velocities)!=20
            or any(not _finite(x) for x in positions+velocities)
            or any(abs(x)>STATIONARY_RAD_S for x in velocities)):
        raise ValueError('state20_invalid_or_not_stationary')
    return dict(zip(names,positions,strict=True))


def _reference(value):
    if (not isinstance(value,dict) or set(value)!=set(probe.BODY) or
            any(not _finite(x) for x in value.values())):
        raise ValueError('manifest_reference_invalid')
    return value


def _candidate(reference, target, arm_order, xml, task_sha):
    if (arm_order!=list(probe.ARM) or not isinstance(target,list) or len(target)!=7
            or any(not _finite(x) for x in target) or not isinstance(xml,str)
            or not _digest(task_sha) or hashlib.sha256(xml.encode()).hexdigest()!=task_sha):
        raise ValueError('candidate_identity_invalid')
    for i,name in enumerate(probe.ARM):
        expected=reference[name]+(probe.ARM_STEP if name==probe.ARM_AXIS else 0.0)
        if not math.isclose(target[i],expected,rel_tol=0,abs_tol=1e-12):
            raise ValueError('candidate_not_fixed_wrist_probe')
    try:
        root=ET.fromstring(xml)
        if root.tag!='root' or root.attrib!={'main_tree_to_execute':'MainTree'} or len(root)!=1:
            raise ValueError('candidate_xml_structure')
        tree=root[0]
        if tree.tag!='BehaviorTree' or tree.attrib!={'ID':'MainTree'} or len(tree)!=1:
            raise ValueError('candidate_xml_structure')
        seq=tree[0]
        if seq.tag!='Sequence' or seq.attrib!={'name':'pico_v4_wrist_single_probe'} or len(seq)!=1:
            raise ValueError('candidate_xml_structure')
        action=seq[0]
        expected={'ID','type','location','joint_angles','duration'}
        if (action.tag!='Action' or len(action) or set(action.attrib)!=expected or
                action.attrib['ID']!='MetaMove' or action.attrib['type']!='arm' or
                action.attrib['location']!='right' or float(action.attrib['duration'])!=probe.DURATION_S):
            raise ValueError('candidate_xml_structure')
        values=[float(x) for x in action.attrib['joint_angles'].split(';')]
        if len(values)!=7 or any(not _finite(x) or not math.isclose(x,y,rel_tol=0,abs_tol=1e-12)
                                for x,y in zip(values,target,strict=True)):
            raise ValueError('candidate_xml_target_mismatch')
    except (ET.ParseError,KeyError,TypeError,OverflowError) as exc:
        raise ValueError('candidate_xml_invalid') from exc


def _parse_rows(stream):
    if isinstance(stream,bytes):
        try: stream=stream.decode('utf-8')
        except UnicodeError as exc: raise ValueError('relay_not_utf8') from exc
    if isinstance(stream,str):
        if not stream.endswith('\n') or len(stream)>1_000_000:
            raise ValueError('relay_truncated_or_too_large')
        def pairs(items):
            result={}
            for k,v in items:
                if k in result: raise ValueError('duplicate_relay_json_key')
                result[k]=v
            return result
        def bad_constant(value): raise ValueError('nonfinite_relay_json')
        try:
            stream=[json.loads(line,object_pairs_hook=pairs,parse_constant=bad_constant)
                    for line in stream.splitlines() if line]
        except (json.JSONDecodeError,UnicodeError) as exc:
            raise ValueError('relay_json_invalid') from exc
    if not isinstance(stream,list) or len(stream)!=4 or any(not isinstance(x,dict) for x in stream):
        raise ValueError('relay_incomplete_or_wrong_record_count')
    if [row.get('event') for row in stream]!=['model_ready','prediction','done','summary']:
        raise ValueError('relay_lifecycle_invalid')
    ready,pred,done,summary=stream
    if (ready.get('model_sha256')!=MODEL_SHA256 or ready.get('physical_control_qualified') is not False
            or type(ready.get('movement_commands')) is not int or ready['movement_commands']!=0
            or type(done.get('samples')) is not int or done['samples']!=1
            or done.get('physical_control_qualified') is not False
            or type(summary.get('predictions')) is not int or summary['predictions']!=1
            or type(summary.get('observations_sent')) is not int or summary['observations_sent']!=1
            or type(summary.get('observations_dropped')) is not int or summary['observations_dropped']<0
            or type(summary.get('movement_commands')) is not int or summary['movement_commands']!=0):
        raise ValueError('relay_checkpoint_or_completion_invalid')
    return pred


def _semantic(data):
    if (data['schema']!='cruzr_wrist_model_decision_v1' or data['model_sha256']!=MODEL_SHA256
            or data['physical_control_qualified'] is not False
            or type(data['physical_commands_sent']) is not int or data['physical_commands_sent']!=0
            or not _digest(data['image_sha256']) or type(data['image_source_ns']) is not int
            or data['image_source_ns']<=0 or type(data['sample_index']) is not int or data['sample_index']!=0
            or not _uuid(data['pc_boot_id'])):
        raise ValueError('decision_identity_invalid')
    stamps=[data[k] for k in ('state_received_monotonic_ns','prediction_received_monotonic_ns','decision_monotonic_ns')]
    if any(type(x) is not int or x<=0 for x in stamps) or not stamps[0]<=stamps[1]<=stamps[2]:
        raise ValueError('decision_pc_times_invalid')
    measured=_named(data['state_names'],data['state_positions'],data['state_velocities'])
    reference=_reference(data['reference_20d'])
    if any(abs(reference[name]-measured[name])>REFERENCE_TOLERANCE_RAD for name in reference):
        raise ValueError('manifest_state_reference_mismatch')
    action,differences=data['model_action_original'],data['model_arm_deltas_rad']
    if (not isinstance(action,list) or len(action)!=8 or any(not _finite(x) for x in action)
            or not isinstance(differences,list) or len(differences)!=7
            or any(not _finite(x) for x in differences)):
        raise ValueError('model_action_invalid')
    for i,name in enumerate(probe.ARM):
        if not math.isclose(action[i]-measured[name],differences[i],rel_tol=1e-6,abs_tol=1e-6):
            raise ValueError('model_delta_state_mismatch:'+name)
    _candidate(reference,data['target_rad'],data['arm_joint_order'],data['task_xml'],data['task_sha256'])
    observed=measured[probe.ARM_AXIS]
    delta=data['target_rad'][-1]-observed
    proposed=action[6]-observed
    if not 0.0<delta<=proposed:
        raise ValueError('fixed_target_not_within_model_proposal')


def _decision_hash(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),
                                     allow_nan=False,ensure_ascii=False).encode('utf-8')).hexdigest()


def decision_from_stream(stream, manifest, *, now_ns, boot_id):
    """Consume complete relay output; return auditable decision, no authority.

    `stream` may be newline-terminated JSONL bytes/text or a complete list of
    four decoded records. The caller must wait for actual EOF and successful
    relay exit before passing it; records do not authenticate their producer.
    `now_ns` and the boot ID must come from this PC in the same live run.
    """
    pred=_parse_rows(stream)
    if (not isinstance(manifest,dict) or not isinstance(manifest.get('input'),dict)
            or not isinstance(manifest.get('candidate'),dict)):
        raise ValueError('manifest_invalid')
    candidate=manifest['candidate']
    state=pred.get('paired_state20')
    if (not isinstance(state,dict) or pred.get('physical_control_qualified') is not False
            or type(now_ns) is not int or now_ns<=0):
        raise ValueError('paired_prediction_invalid')
    try:
        data={'schema':'cruzr_wrist_model_decision_v1','model_sha256':MODEL_SHA256,
              'image_sha256':pred['image_sha256'],'image_source_ns':pred['image_source_ns'],
              'sample_index':pred['index'],'model_action_original':pred['prediction'],
              'model_arm_deltas_rad':pred['proposed_minus_observed_rad'],
              'state_names':state['names'],'state_positions':state['positions'],
              'state_velocities':state['velocities'],
              'state_received_monotonic_ns':state['received_monotonic_ns'],
              'prediction_received_monotonic_ns':pred['prediction_received_monotonic_ns'],
              'decision_monotonic_ns':now_ns,'pc_boot_id':boot_id,
              'reference_20d':manifest['input']['reference_20d'],
              'target_rad':candidate['target_rad'],'arm_joint_order':candidate['arm_joint_order'],
              'task_xml':candidate['xml'],'task_sha256':candidate['xml_sha256'],
              'physical_control_qualified':False,'physical_commands_sent':0}
    except KeyError as exc:
        raise ValueError('paired_prediction_or_manifest_missing_field') from exc
    if (candidate.get('moved_axis')!=probe.ARM_AXIS or candidate.get('step_rad_experimental')!=probe.ARM_STEP
            or candidate.get('duration_s_experimental')!=probe.DURATION_S or type(candidate.get('actions')) is not int
            or candidate.get('actions')!=1
            or candidate.get('automatic_return') is not False or candidate.get('home_requested') is not False):
        raise ValueError('candidate_probe_metadata_invalid')
    _semantic(data)
    # Copy nested data: subsequent mutations to caller-owned records/manifest
    # must not silently alter the decision without invalidating its hash.
    data=json.loads(json.dumps(data,sort_keys=True,allow_nan=False))
    data['decision_sha256']=_decision_hash(data)
    return data


def make_dispatch_permission(decision, goal_id, task_sha256, *, boot_id, now_ns,
                             max_state_age_ns, max_prediction_age_ns):
    """Return a bounded decision receipt or None if decision has not arrived.

    This is data for a separate guarded coordinator, not a physical enablement.
    The caller must independently preserve/compare the decision hash and
    enforce the remaining budget over transport and before dispatch.
    """
    if decision is None:
        return None
    if (not isinstance(decision,dict) or not _uuid(goal_id) or not _uuid(boot_id)
            or type(now_ns) is not int or now_ns<=0 or not _digest(task_sha256)
            or any(type(x) is not int or not 0<x<=MAX_AGE_NS
                   for x in (max_state_age_ns,max_prediction_age_ns))):
        raise ValueError('permission_inputs_invalid')
    data=dict(decision);digest=data.pop('decision_sha256',None)
    if not _digest(digest) or _decision_hash(data)!=digest:
        raise ValueError('decision_hash_mismatch')
    try: _semantic(data)
    except KeyError as exc: raise ValueError('decision_field_missing') from exc
    if data['pc_boot_id']!=boot_id or data['task_sha256']!=task_sha256:
        raise ValueError('permission_boot_or_task_mismatch')
    if now_ns<data['decision_monotonic_ns']:
        raise ValueError('permission_pc_time_future')
    remaining=min(max_state_age_ns-(now_ns-data['state_received_monotonic_ns']),
                  max_prediction_age_ns-(now_ns-data['prediction_received_monotonic_ns']))
    if remaining<=0:
        raise ValueError('permission_pc_receipt_expired')
    return {'goal_id':goal_id,'task_sha256':task_sha256,'decision_sha256':digest,'budget_ns':remaining}
