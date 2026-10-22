"""Synthetic complete native logs plus the archived real false-success case."""
import copy
import json
from pathlib import Path
import unittest

from scripts.box_handling import scenario1_table74_native_completion as native
from scripts.box_handling.test_scenario1_table74_current_lower import bundle as lowering
from scripts.box_handling.test_scenario1_table74_current_release import bundle as releasing


def log(bundle,*,spent=None,status='NoneException',docker=False):
    task=bundle['task_name'];duration=bundle['review']['nominal_duration_s']
    lines=['I2026-10-22 19:24:19.881435 [3559.788292] 100 [meta_node.cpp:83:TickStart]: Start MetaClamp: '+task,
        'duration: '+str(duration)]
    if status is not None:lines.append('I2026-10-22 19:24:31.910941 [3571.817798] 10579 [meta_clamp.cpp:1576:tick]: clamp_status: '+status)
    lines+=['I2026-10-22 19:24:31.914403 [3571.821260] 10579 [meta_node.cpp:96:TickEnd]: End MetaClamp: '+task,
        'W2026-10-22 19:24:31.914433 [3571.821290] 10579 [meta_node.cpp:97:TickEnd]: meta_name: MetaClamp',
        'action_name: '+task,'result: SUCCESS','spent_time: '+str(duration+.032 if spent is None else spent)+' s',
        'I2026-10-22 19:24:31.921584 [3571.828441] 100 [client.cpp:251:GetBTreeStatus]: BTree tick succeeded']
    if docker:lines=['2026-10-22T11:24:31.921584123Z '+line for line in lines]
    return '\n'.join('\x1b[33m'+line+'\x1b[m'for line in lines)+'\n'


class NativeCompletionTests(unittest.TestCase):
    def test_accepts_complete_exact_task_and_records_no_physical_support_claim(self):
        for bundle in (lowering(),lowering('support'),releasing()):
            for docker in (False,True):
                with self.subTest(task=bundle['task_name'],docker=docker):
                    evidence=native.validate_native_log(log(bundle,docker=docker),bundle)
                    self.assertIs(evidence['verified'],True)
                    self.assertEqual(evidence['bundle_id'],bundle['manifest']['id'])
                    self.assertEqual(evidence['task_name'],bundle['task_name'])
                    self.assertEqual(evidence['clamp_status'],'NoneException')
                    self.assertIs(evidence['physical_support_verified'],False)
                    self.assertIs(evidence['pin_disengagement_verified'],False)

    def test_missing_status_is_not_invented_normal_but_transaction_is_still_required(self):
        bundle=lowering();result=native.validate_native_log(log(bundle,status=None),bundle)
        self.assertIsNone(result['clamp_status']);self.assertTrue(result['verified'])

    def test_known_force_false_success_and_other_faults_block_even_with_complete_success_block(self):
        bundle=lowering()
        for message in ('Collision force on right_hand axis[2] exceeded limit 3 times, exiting.',
                        'DectionForceCollision','DetectionForceCollision','self collision detected, stop right away',
                        'force monitoring failed','IK solver failed','HQP infeasible','MoveToGoalFailed',
                        'watchdog expired','BTree tick failed','query timed out'):
            text=log(bundle).replace('duration: 12.0','duration: 12.0\n'+message)
            with self.subTest(message=message),self.assertRaisesRegex(ValueError,'NATIVE_FAULT'):
                native.validate_native_log(text,bundle)
        for status in ('DectionForceCollision','JointTrackingError','IKFailed','SUCCESS',''):
            with self.subTest(status=status),self.assertRaises(ValueError):native.validate_native_log(log(bundle,status=status),bundle)

    def test_early_or_stalled_phase_never_becomes_complete_from_generic_result_success(self):
        for bundle in (lowering(),releasing()):
            duration=bundle['review']['nominal_duration_s']
            for spent in (0.,duration-native.MIN_DURATION_TOLERANCE_S-.001,duration+5.001):
                with self.subTest(duration=duration,spent=spent),self.assertRaisesRegex(ValueError,'NATIVE_DURATION'):
                    native.validate_native_log(log(bundle,spent=spent),bundle)
            native.validate_native_log(log(bundle,spent=duration-native.MIN_DURATION_TOLERANCE_S+.001),bundle)
        bundle=lowering('support')
        native.validate_native_log(log(bundle,spent=11.61),bundle)

    def test_other_task_missing_end_duplicate_start_or_summary_and_reordered_markers_fail(self):
        bundle=lowering();text=log(bundle);task=bundle['task_name']
        mutations=[text.replace(task,task+'other'),text.replace('End MetaClamp:','End MetaMove:'),
            text+text,text.replace('result: SUCCESS','result: FAILURE'),
            text.replace('spent_time: 12.032 s','spent_time: nan s'),
            text.replace('Start MetaClamp:','End MetaClamp:').replace('TickEnd]: End MetaClamp:','TickEnd]: Start MetaClamp:'),
            text+'\nStart MetaClamp: another/task\n',text+'\naction_name: '+task+'\n',
            text.replace('meta_name: MetaClamp','meta_name: MetaMove')]
        for mutated in mutations:
            with self.subTest(text=mutated[-160:]),self.assertRaises(ValueError):native.validate_native_log(mutated,bundle)

    def test_candidate_byte_hash_identity_and_single_action_are_required(self):
        bundle=lowering();text=log(bundle)
        for mutation in ('identity','duration','hash','extra_action'):
            bad=copy.deepcopy(bundle);name=bad['task_name'];yaml=native.META_ROOT+name+'.yaml';xml=native.TASK_ROOT+name+'.xml'
            if mutation=='identity':bad['manifest']['id']='0'*64
            elif mutation=='duration':bad['review']['nominal_duration_s']=2.
            elif mutation=='hash':bad['tasks'][yaml]+='\n'
            else:
                bad['tasks'][xml]=bad['tasks'][xml].replace('</Sequence>','<Action ID="MetaMove" /></Sequence>')
                bad['manifest']['robot_files'][xml]=native._sha(bad['tasks'][xml])
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):native.validate_native_log(text,bad)

    def test_no_log_or_invalid_unbounded_text_is_never_verified(self):
        bundle=lowering()
        for text in ('','BTree tick succeeded\n',None,'bad\0log'):
            with self.subTest(text=text),self.assertRaises(ValueError):native.validate_native_log(text,bundle)
        with self.assertRaises(ValueError):native.validate_native_log('x'*(native.MAX_LOG_BYTES+1),bundle)

    def test_archived_real_collision_block_is_rejected_without_relying_on_private_fixture(self):
        # Identical semantic lines to the observed22Oct force exit. Source task
        # identity is replaced with this synthetic bundle, so rejection tests
        # force handling rather than merely mismatched names or short time.
        bundle=lowering();text=log(bundle,spent=12.032,status='DectionForceCollision')
        text=text.replace('duration: 12.0','duration: 12.0\n'
            'W2026-10-22 19:24:30.830893 [3570.737750] 10579 '
            '[clamp_abnormality_helper.cpp:752:CheckCollisionForce]: '
            'Collision force on right_hand axis[2] exceeded limit 3 times, exiting.')
        with self.assertRaisesRegex(ValueError,'NATIVE_FAULT'):native.validate_native_log(text,bundle)


if __name__=='__main__':unittest.main()
