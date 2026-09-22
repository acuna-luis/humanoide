"""Selection regressions only; no robot connections."""
import copy
import itertools
import math
import unittest

from scripts.box_handling.select_front_box import select_front_box


def pose(x, y, z):
    return dict(position=dict(x=x, y=y, z=z),
                orientation=dict(x=0, y=0, z=0, w=1))


def detection(*poses):
    return dict(frame_id='base_link', poses=list(poses))


class FrontBoxTest(unittest.TestCase):
    def test_lower_front_box_wins_over_higher_lateral_boxes_in_any_order(self):
        front = pose(.80, .10, .39)
        for poses in itertools.permutations([front, pose(.805, .723, .707),
                                             pose(.85, -.60, 1.20)]):
            d = detection(*poses)
            before = copy.deepcopy(d)
            result = select_front_box(d)
            self.assertEqual(result['selected_pose'], front)
            self.assertEqual(d, before)
            self.assertFalse(result['reachability_checked'])
            self.assertFalse(result['motion_authorized'])

    def test_height_does_not_change_horizontal_ranking(self):
        for height in (.2, .8, 1.5):
            self.assertEqual(select_front_box(detection(pose(.8, .02, height),
                pose(.7, .15, .5)))['selected_index'], 0)

    def test_unreachable_front_is_not_replaced_by_reachable_side(self):
        result = select_front_box(detection(pose(1.2, .01, .4), pose(.7, .15, .7)))
        self.assertEqual(result['selected_index'], 0)
        self.assertFalse(result['reachability_checked'])

    def test_stacked_or_similarly_centered_boxes_are_ambiguous(self):
        for side in (0., .01):
            with self.assertRaisesRegex(ValueError, 'Ambiguous'):
                select_front_box(detection(pose(.8, 0, .4), pose(.8, side, .8)))

    def test_top_of_front_stack_wins_even_when_lateral_stack_is_higher(self):
        top = pose(.78, .10, .62)
        bottom = pose(.79, .105, .40)
        lateral = pose(.85, .25, 1.20)
        for candidates in itertools.permutations([bottom, top, lateral]):
            original = copy.deepcopy(candidates)
            result = select_front_box(detection(*candidates))
            self.assertEqual(result['selected_pose'], top)
            self.assertEqual(candidates, original)
            self.assertEqual(len(result['selected_stack_indices_bottom_to_top']), 2)

    def test_three_levels_and_unreachable_top_are_not_replaced(self):
        result = select_front_box(detection(pose(1.1, 0, .4), pose(1.1, 0, .62),
            pose(1.1, 0, .84), pose(.7, .15, .5)))
        self.assertEqual(result['selected_index'], 2)
        self.assertFalse(result['reachability_checked'])

    def test_recorded_frontal_box_and_support_20260922(self):
        # Fresh perception/TF captured after the ambiguity failure. The support
        # is slightly more centered, but the operator wants the box above it.
        top = pose(.7832416746, .1373285068, .7939513163)
        support = pose(.7840892972, .1325046344, .5847200055)
        side = pose(.8137622713, 1.2787864220, .4782122118)
        self.assertEqual(select_front_box(detection(top, support, side))['selected_pose'], top)

    def test_sector_boundary_cannot_select_support_under_excluded_top(self):
        support = pose(.8, .28, .4)  # 19.29 degrees
        top = pose(.8, .31, .62)     # 21.18 degrees, same column
        for ordered in itertools.permutations([top, support]):
            with self.assertRaisesRegex(ValueError, 'No top box'):
                select_front_box(detection(*ordered))

    def test_distinct_columns_duplicates_and_bridging_chains_stay_ambiguous(self):
        cases = [
            [pose(.8, 0, .4), pose(1.1, 0, .62)],
            [pose(.8, 0, .4), pose(.801, .001, .401)],
            [pose(.8, 0, .4), pose(.87, 0, .62), pose(.94, 0, .84)],
        ]
        for candidates in cases:
            for ordered in itertools.permutations(candidates):
                with self.assertRaisesRegex(ValueError, 'Ambiguous'):
                    select_front_box(detection(*ordered))

    def test_camera_frame_is_not_treated_as_robot_frame(self):
        d = detection(pose(.8, .1, .4))
        d['frame_id'] = 'stereo_left_rectified_optical_frame'
        with self.assertRaises(ValueError):
            select_front_box(d)

    def test_empty_behind_and_side_only_rejected(self):
        for d in (detection(), detection(pose(-.8, 0, .4)), detection(pose(.8, .7, .4))):
            with self.assertRaises(ValueError):
                select_front_box(d)

    def test_invalid_candidate_is_not_silently_discarded(self):
        for value in (math.nan, math.inf, True):
            with self.assertRaises(ValueError):
                select_front_box(detection(pose(.8, 0, .4), pose(.8, value, .8)))
        p = pose(.8, 0, .4)
        p['orientation']['w'] = 0
        with self.assertRaises(ValueError):
            select_front_box(detection(p))

    def test_invalid_policy_rejected(self):
        for front, ambiguity in ((90, 2), (0, 0), (20, 20), (math.nan, 2)):
            with self.assertRaises(ValueError):
                select_front_box(detection(pose(.8, 0, .4)),
                                 front_angle_deg=front, ambiguity_deg=ambiguity)


if __name__ == '__main__':
    unittest.main()
