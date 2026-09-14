"""Refine selected distance lower bounds offline without excluding any pairs."""
import math

import numpy as np


def refinement_indices(prior, labels, *, candidate, route, error_rad, sources, model_sources):
    if prior.get('candidate') != candidate or prior.get('route') != route:
        raise ValueError('Refinement candidate/route mismatch')
    if prior.get('model_sources') != model_sources:
        raise ValueError('Refinement model mismatch')
    if any(prior.get('sources_sha256', {}).get(p) != h for p, h in sources.items()):
        raise ValueError('Refinement input files differ')
    audit = prior['audit']
    if audit['timed_out'] or audit['base_margin_m'] != .002:
        raise ValueError('Refinement requires a completed review with the canonical margin')
    if not math.isclose(audit['joint_error_scenario_rad'], error_rad, rel_tol=0., abs_tol=1e-15):
        raise ValueError('Refinement angular scenario mismatch')
    if [p['pair'] for p in audit['pairs']] != labels or any(p['exempted'] for p in audit['pairs']):
        raise ValueError('Refinement pair set mismatch or exemptions')
    return [i for i, p in enumerate(audit['pairs']) if p['status'] == 'UNRESOLVED']


class RefinedPairDistances:
    def __init__(self, base, indices, solid_distance):
        self.base = base
        self.indices = tuple(sorted(set(indices)))
        if any(type(i) is not int or not 0 <= i < len(base.labels) for i in self.indices):
            raise ValueError('Invalid refinement index')
        self.solid_distance = solid_distance
        self.solid_queries = 0
        self.improved_queries = 0
        self.maximum_lower_bound_gain_m = 0.

    def __getattr__(self, name):
        return getattr(self.base, name)

    def distances(self, q):
        # The base call places every object at this q, and still evaluates ALL
        # pairs. Only far-pair AABB shortcuts are candidates for refinement.
        result = np.asarray(self.base.distances(q), dtype=float).copy()
        for i in self.indices:
            if result[i] <= .04:
                continue
            a, b = self.base.pairs[i]
            value = float(self.solid_distance(self.base.shapes[a], self.base.shapes[b]))
            self.solid_queries += 1
            if not math.isfinite(value) or value < 0:
                raise ValueError('Invalid solid distance')
            if value + 1e-7 < result[i]:
                raise ValueError('Solid/AABB lower bounds inconsistent; do not certify')
            gain = max(0., value-result[i])
            self.improved_queries += int(gain > 1e-9)
            self.maximum_lower_bound_gain_m = max(self.maximum_lower_bound_gain_m, gain)
            # Both use the same complete conservative solids and subtract the
            # same numeric geometry error. No margin or geometry is reduced.
            result[i] = max(result[i], value)
        return result

    def selected_distances(self,q,indices):
        if not hasattr(self.base,'selected_distances'):
            return self.distances(q)[indices]
        result=np.asarray(self.base.selected_distances(q,indices),dtype=float).copy()
        for k,i in enumerate(indices):
            if i not in self.indices or result[k]<=.04:continue
            a,b=self.base.pairs[i]
            value=float(self.solid_distance(self.base.shapes[a],self.base.shapes[b]))
            self.solid_queries+=1
            if not math.isfinite(value) or value<0 or value+1e-7<result[k]:
                raise ValueError('Invalid or inconsistent selective solid distance')
            gain=max(0.,value-result[k]);self.improved_queries+=int(gain>1e-9)
            self.maximum_lower_bound_gain_m=max(self.maximum_lower_bound_gain_m,gain)
            result[k]=max(result[k],value)
        return result

    def summary(self):
        return dict(method='SELECTED_SOLID_DISTANCES_ALL_PAIRS_RETAINED',
                    refined_pairs=[self.labels[i] for i in self.indices],
                    solid_queries=self.solid_queries, improved_queries=self.improved_queries,
                    maximum_lower_bound_gain_m=self.maximum_lower_bound_gain_m)
