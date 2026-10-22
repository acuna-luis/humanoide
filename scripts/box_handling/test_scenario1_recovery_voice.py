"""Recovery fault injection and speech fakes; no audio, ROS or network."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_voice as voice
from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_box_alignment as alignment
from scripts.box_handling.test_scenario1_box_alignment_runtime import AlignmentRuntimeTests, posture, SUCCESS


class RecoveryTests(unittest.TestCase):
    def machine(self):
        helper = AlignmentRuntimeTests()
        machine = helper.machine()
        self.addCleanup(helper.doCleanups)
        machine.payload['empty_home_recovery'] = True
        machine.health = Mock(return_value=posture())
        machine.stationary_base = Mock()
        machine.action = Mock(return_value=copy.deepcopy(SUCCESS))
        machine.checkpoint = contract.fail_stage(contract.begin_stage(machine.checkpoint, 'grasp'),
            'grasp', 'BOX_ALIGNMENT_LIMIT: attempts')
        return machine

    def test_known_empty_planning_failure_returns_home_once_and_preserves_failure(self):
        m = self.machine(); before=copy.deepcopy(m.checkpoint)
        m.recover_empty_home('grasp','empty', RuntimeError('BOX_ALIGNMENT_LIMIT: attempts'))
        self.assertEqual(m.action.call_count, 1)
        self.assertEqual(m.action.call_args.args[1], {'task_name':'cruzr/home','yaml_args':'{}'})
        self.assertTrue(m.empty_home_recovered)
        self.assertEqual(m.checkpoint,before)
        self.assertEqual(json.loads((m.session/'empty-home-recovery.json').read_text())['status'],'home_measured')
        m.recover_empty_home('grasp','empty', RuntimeError('BOX_ALIGNMENT_LIMIT: attempts'))
        self.assertEqual(m.action.call_count, 1)
        self.assertEqual(m.health.call_args_list[-1].kwargs, {'require_home':True})

    def test_stage_failure_journals_home_intent_before_dispatch_and_preserves_original_error(self):
        helper=AlignmentRuntimeTests();self.addCleanup(helper.doCleanups)
        m=helper.machine([helper.observation(.9)])
        m.payload['empty_home_recovery']=True
        m.stationary_base=Mock()
        calls=[]
        def action(kind, goal, timeout, **kwargs):
            calls.append(goal['task_name'])
            if goal['task_name']=='cruzr/home':
                self.assertEqual(json.loads((m.session/'empty-home-recovery.json').read_text())['status'],'dispatched')
                self.assertIsNotNone(json.loads((m.session/'checkpoint.json').read_text())['failure'])
            return copy.deepcopy(SUCCESS)
        m.action.side_effect=action
        with self.assertRaisesRegex(ValueError,'BOX_ALIGNMENT_OUTSIDE_ENVELOPE'):
            m.stage({'stage':'grasp'})
        self.assertEqual(calls,[alignment.HEAD_TASK,'cruzr/home'])
        self.assertTrue(m.empty_home_recovered)
        self.assertEqual(m.checkpoint['failure']['stage'],'grasp')
        self.assertFalse(m.native_grasp_started)

    def test_uncertain_cancel_contact_health_held_or_started_grasp_never_homes(self):
        cases=[('grasp','empty','WORKER_REQUEST_FAILED: Correction made no significant progress',False),
               ('grasp','empty','BOX_ALIGNMENT_LIMIT: attempts',True),
               ('grasp','held','BOX_ALIGNMENT_LIMIT: attempts',False),
               ('deposit','empty','BOX_ALIGNMENT_LIMIT: attempts',False),
               ('grasp','empty','COLLISION',False)]
        for stage,box,reason,started in cases:
            m=self.machine();m.native_grasp_started=started
            m.recover_empty_home(stage,box,RuntimeError(reason))
            m.action.assert_not_called()

    def test_any_new_health_or_worker_failure_blocks_home(self):
        for gate in ('connected','health','stationary_base','quick_health','hashes'):
            m=self.machine();getattr(m,gate).side_effect=RuntimeError('synthetic failed gate')
            m.recover_empty_home('grasp','empty',RuntimeError('BOX_ALIGNMENT_LIMIT: attempts'))
            m.action.assert_not_called()
            self.assertFalse(m.empty_home_recovered)

    def test_failed_home_is_not_repeated_and_not_declared_measured(self):
        m=self.machine();m.action.side_effect=RuntimeError('uncertain HOME')
        m.recover_empty_home('grasp','empty',RuntimeError('BOX_ALIGNMENT_LIMIT: attempts'))
        self.assertFalse(m.empty_home_recovered)
        self.assertEqual(m.action.call_count,1)

    def test_opt_in_is_required_and_unexpected_posture_blocks_recovery(self):
        m=self.machine();m.payload['empty_home_recovery']=False
        m.recover_empty_home('grasp','empty',RuntimeError('BOX_ALIGNMENT_LIMIT: attempts'))
        m.action.assert_not_called()
        m=self.machine();m.health.return_value=posture(body=.2)
        m.recover_empty_home('grasp','empty',RuntimeError('BOX_ALIGNMENT_LIMIT: attempts'))
        m.action.assert_not_called()

    def test_completed_but_flat_alignment_can_remeasure_and_try_next_goal(self):
        helper=AlignmentRuntimeTests();self.addCleanup(helper.doCleanups)
        observations=[helper.observation(.8),helper.observation(.799,stamp=101_000_000_000),
                      helper.observation(.785,stamp=102_000_000_000)]
        m=helper.machine(observations,attempts=3)
        with patch.object(alignment,'validate_arrival',return_value=[]),patch.object(alignment,'validate_association',return_value={}):
            m.stage({'stage':'grasp'})
        self.assertEqual(helper.kinds(m), ['motion','navigation','navigation','motion'])
        self.assertTrue(any(c.kwargs.get('code')=='position_retry' for c in m.emit.call_args_list))

    def test_two_flat_completed_corrections_stop_without_native_grasp(self):
        helper=AlignmentRuntimeTests();self.addCleanup(helper.doCleanups)
        m=helper.machine([helper.observation(.8),helper.observation(.799,stamp=101_000_000_000),
                          helper.observation(.798,stamp=102_000_000_000)],attempts=7)
        with patch.object(alignment,'validate_arrival',return_value=[]),patch.object(alignment,'validate_association',return_value={}):
            with self.assertRaisesRegex(RuntimeError,'two consecutive'):m.stage({'stage':'grasp'})
        self.assertFalse(m.native_grasp_started)
        self.assertEqual(helper.kinds(m),['motion','navigation','navigation'])


class VoiceTests(unittest.TestCase):
    def test_voice_is_optional_and_recovery_requires_explicit_option(self):
        args=cli.parser('assume','optimistic_v1').parse_args([])
        self.assertEqual(args.voice,'robot-en')
        self.assertFalse(args.empty_home_recovery)

    def test_spanish_local_speech_is_queued_deduplicated_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(voice.threading.Thread,'start'), \
             patch.object(voice.shutil,'which',return_value='/usr/bin/espeak-ng'), \
             patch.object(voice.subprocess,'run',return_value=Mock(returncode=0)) as run:
            v=voice.Voice('pc',directory,'/not-used')
            e={'event':'recovery','code':'position_retry'}
            v.feed(e);v.feed(e);v.close();v.work()
            self.assertEqual(run.call_count,1)
            self.assertIn('Error al posicionarse',run.call_args.args[0][-1])
            self.assertEqual(run.call_args.kwargs['timeout'],12)
            self.assertNotIn('shell',run.call_args.kwargs)

    def test_pc_reader_archives_recovery_without_promoting_failed_checkpoint(self):
        import io,queue
        with tempfile.TemporaryDirectory() as directory:
            c=cli.Connection.__new__(cli.Connection)
            c.evidence=Path(directory);c.events=queue.Queue();c.present=Mock()
            record={'status':'home_measured','original_error':'BOX_ALIGNMENT_LIMIT: attempts'}
            c.process=Mock(stdout=io.StringIO(json.dumps({'event':'recovery','code':'home_recovered','record':record})+'\n'))
            c.read()
            self.assertEqual(json.loads((c.evidence/'empty-home-recovery.json').read_text()),record)
            self.assertFalse((c.evidence/'checkpoint.json').exists())

    def test_robot_mode_calls_only_existing_speech_script(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(voice.threading.Thread,'start'), \
             patch.object(voice.subprocess,'run',side_effect=OSError('synthetic speech unavailable')) as run:
            v=voice.Voice('robot-en',directory,'/repo/scripts/cruzr_say_english.sh')
            v.feed({'event':'recovery','code':'home_recovered'});v.close();v.work()
            self.assertEqual(run.call_args.args[0][:2],['bash','/repo/scripts/cruzr_say_english.sh'])
            records=[json.loads(x) for x in (Path(directory)/'voice.jsonl').read_text().splitlines()]
            self.assertEqual(records[-1]['status'],'failed')


if __name__=='__main__':unittest.main()
