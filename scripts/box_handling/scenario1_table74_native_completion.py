"""Pure, bounded native-log completion evidence for one table74 MetaClamp.

Vendor ArmTask SUCCEED can also mean an early force-triggered exit. This helper
requires the expected native task's complete log transaction, nominal elapsed
time and no observed fault. It never proves table support or free pins. The
caller must bind the bounded live log window, pinned container and action UUID.
"""
import hashlib
import math
import re
import xml.etree.ElementTree as ET


MAX_LOG_BYTES = 16*1024*1024
# Last completed supervised support returned at~11.84s for nominal12s;
# native tick/feedback timing is not an exact full-motion clock. This tolerance
# alone never proves completion: known force exits remain independently fatal.
MIN_DURATION_TOLERANCE_S = .5
MAX_DURATION_OVERRUN_S = 5.
TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
META_ROOT = '/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/'
_ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
_DOCKER = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)\s+')
_NUMBER = r'(?:\d+(?:\.\d*)?|\.\d+)'
_TASK = re.compile(r'local_table74_(current|lower|release)/([0-9a-f]{64})_(approach|lower|release)')
_FAULTS = (
    re.compile(r'\b(?:Dection|Detection)ForceCollision\b', re.I),
    re.compile(r'\bCollision force on\b.*\bexceeded limit\b', re.I),
    re.compile(r'\bself collision detected\b', re.I),
    re.compile(r'\b(?:force|wrench)\b.*\b(?:monitoring|maintain|tracking)\b.*\b(?:failed|failure|triggered)\b', re.I),
    re.compile(r'\b(?:IK|inverse kinematics|HQP)\b.*\b(?:failed|failure|infeasible)\b', re.I),
    re.compile(r'\b(?:MoveToGoalFailed|GoalAborted)\b', re.I),
    re.compile(r'\b(?:timed out|timeout occurred|watchdog expired|lease expired)\b', re.I),
    re.compile(r'\b(?:BTree tick|task execution)\s+(?:failed|aborted)\b', re.I),
)
GUARD_POLICY = 'feria_native_terminal_v1'
_RESULT_FAILURE = re.compile(r'\bresult\s*:\s*(?:FAILURE|FAILED|ABORTED|ERROR|CANCELED|CANCELLED)\b', re.I)
_RAW_CLAMP_STATUS = re.compile(r'\bclamp_status\s*:\s*(.*?)\s*$', re.I)
_READER_FAILURE = re.compile(r'^(?:Error grabbing logs:|Error response from daemon:|Error: No such container:)', re.I)


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _expected(bundle):
    """Bind labels/duration to the candidate bytes, never an arbitrary log name."""
    try:
        task = bundle['task_name']; manifest = bundle['manifest']; files = bundle['tasks']
        match = _TASK.fullmatch(task) if type(task) is str else None
        if match is None or manifest['task_name'] != task or manifest['id'] != match[2]:
            raise ValueError('Task name and immutable bundle identity differ')
        if (match[1],match[3]) not in (('current','approach'),('lower','lower'),('release','release')):
            raise ValueError('Unsupported native completion namespace')
        yaml_path, xml_path = META_ROOT+task+'.yaml', TASK_ROOT+task+'.xml'
        if not isinstance(files,dict) or set(files) != {yaml_path,xml_path}:
            raise ValueError('Native completion requires exactly its candidate YAML and XML')
        for path in (yaml_path,xml_path):
            if type(files[path]) is not str or len(files[path].encode()) > 262144:
                raise ValueError('Native completion candidate text invalid or oversized')
            if _sha(files[path]) != manifest['robot_files'][path]:
                raise ValueError('Native completion candidate checksum differs')
        meta = re.findall(r'^meta_name:\s*([A-Za-z_][A-Za-z_0-9]*)\s*$',files[yaml_path],re.M)
        durations = re.findall(r'^  duration:\s*('+_NUMBER+r')\s*$',files[yaml_path],re.M)
        if meta != ['MetaClamp'] or len(durations) != 1:
            raise ValueError('Native completion MetaClamp identity/duration missing or ambiguous')
        duration = float(durations[0])
        if not math.isfinite(duration) or duration not in (2.,12.) or bundle['review']['nominal_duration_s'] != duration:
            raise ValueError('Native completion requires the reviewed two/twelve-second phase')
        actions = list(ET.fromstring(files[xml_path]).iter('Action'))
        if len(actions) != 1 or actions[0].attrib != {'ID':'MetaClamp','name':task}:
            raise ValueError('Native completion requires one exact MetaClamp action')
        return task,manifest['id'],duration
    except (KeyError,TypeError,ET.ParseError) as exc:
        raise ValueError('Malformed native completion candidate') from exc


def _message(line):
    line = _DOCKER.sub('',line)
    # Native prefix: I<local time> [monotonic] thread [source.cpp:line:fn]:
    if ']:' in line:
        line = line.split(']:',1)[1]
    return line.strip()


def validate_native_log(text,bundle):
    """Return audit evidence, or reject missing, early, contradictory or faulted logs.

    A normal clamp_status may be absent at a different log verbosity. If emitted
    it must be exactly NoneException. Missing status is reported as missing,
    never synthesized as normal. An otherwise complete log still measures only
    native execution; a recorded physical recipe remains an assumption.
    """
    task,bundle_id,nominal = _expected(bundle)
    if type(text) is not str or not text.strip() or len(text.encode()) > MAX_LOG_BYTES or '\x00' in text:
        raise ValueError('TABLE74_NATIVE_LOG_INVALID: missing or unbounded native log')
    clean = _ANSI.sub('',text)
    messages = [_message(line) for line in clean.splitlines()]
    for line in messages:
        if any(pattern.search(line) for pattern in _FAULTS):
            raise ValueError('TABLE74_NATIVE_FAULT: '+line[:500])
    starts = [(i,re.fullmatch(r'Start (Meta[A-Za-z_0-9]+):\s*(\S+)',line))
              for i,line in enumerate(messages) if re.match(r'^Start Meta',line)]
    ends = [(i,re.fullmatch(r'End (Meta[A-Za-z_0-9]+):\s*(\S+)',line))
            for i,line in enumerate(messages) if re.match(r'^End Meta',line)]
    if (len(starts) != 1 or len(ends) != 1 or starts[0][1] is None or ends[0][1] is None or
            starts[0][1].groups() != ('MetaClamp',task) or ends[0][1].groups() != ('MetaClamp',task) or
            starts[0][0] >= ends[0][0]):
        raise ValueError('TABLE74_NATIVE_IDENTITY: expected one ordered start/end of the exact task')
    summaries = [i for i,line in enumerate(messages) if line.startswith('meta_name:')]
    if len(summaries) != 1:
        raise ValueError('TABLE74_NATIVE_SUMMARY: missing or ambiguous MetaClamp result block')
    index = summaries[0]
    if index <= ends[0][0] or index+3 >= len(messages):
        raise ValueError('TABLE74_NATIVE_SUMMARY: result block order or completeness invalid')
    if messages[index:index+3] != ['meta_name: MetaClamp','action_name: '+task,'result: SUCCESS']:
        raise ValueError('TABLE74_NATIVE_SUMMARY: task/result differs from the expected action')
    spent_line = re.fullmatch(r'spent_time:\s*('+_NUMBER+r')\s+s',messages[index+3])
    if spent_line is None:
        raise ValueError('TABLE74_NATIVE_DURATION: missing or malformed spent_time')
    if sum(line.startswith('action_name:') for line in messages) != 1 or sum(line.startswith('spent_time:') for line in messages) != 1:
        raise ValueError('TABLE74_NATIVE_SUMMARY: duplicate native transaction fields')
    spent = float(spent_line[1])
    if (not math.isfinite(spent) or spent < nominal-MIN_DURATION_TOLERANCE_S or
            spent > nominal+MAX_DURATION_OVERRUN_S):
        raise ValueError('TABLE74_NATIVE_DURATION: early or abnormally long native phase '+str(spent)+'/'+str(nominal))
    statuses = [(i,line.removeprefix('clamp_status:').strip()) for i,line in enumerate(messages)
                if line.startswith('clamp_status:')]
    if (len(statuses)>1 or any(value != 'NoneException' or not starts[0][0]<i<ends[0][0]
                               for i,value in statuses)):
        raise ValueError('TABLE74_NATIVE_STATUS: non-normal or contradictory native clamp status')
    return dict(verified=True,task_name=task,bundle_id=bundle_id,meta_name='MetaClamp',
        result='SUCCESS',spent_time_s=spent,nominal_duration_s=nominal,
        minimum_duration_s=nominal-MIN_DURATION_TOLERANCE_S,
        clamp_status=statuses[0][1] if statuses else None,
        native_log_sha256=_sha(text),native_log_bytes=len(text.encode()),
        evidence_kind='complete_native_transaction_without_observed_fault',
        physical_support_verified=False,pin_disengagement_verified=False,
        scope='Caller must bind this bounded live window to the pinned container and native goal UUID.')


def assess_native_log(text, bundle, query_error=None):
    """Assess supplementary logs without replacing an authenticated SDK terminal.

    Candidate identity/checksums and observed native faults remain hard errors.
    Missing or ambiguous diagnostic formatting returns an honest inconclusive
    report. In particular this does not turn absent status into NoneException,
    claim physical support, or authorize a retry. The caller must still validate
    the action UUID/result and all live health gates independently.
    """
    task, bundle_id, nominal = _expected(bundle)  # Invalid candidates are not diagnostics.
    if query_error is not None and type(query_error) is not str:
        raise TypeError('query_error must be diagnostic text or None')
    messages = ([_message(line) for line in _ANSI.sub('', text).splitlines()]
                if type(text) is str else [])
    reader_failure = None
    for message in messages:
        # Scan independently of transaction formatting. A truncated header or
        # an extra MetaWaypointGeneral must never conceal an explicit fault.
        if any(pattern.search(message) for pattern in _FAULTS) or _RESULT_FAILURE.search(message):
            raise ValueError('TABLE74_NATIVE_FAULT: '+message[:500])
        status = _RAW_CLAMP_STATUS.search(message)
        if status and status[1] and status[1] != 'NoneException':
            raise ValueError('TABLE74_NATIVE_STATUS: '+status[1][:500])
        if _READER_FAILURE.match(message):
            reader_failure = message
    try:
        report = validate_native_log(text, bundle)
    except ValueError as exc:
        reason = str(exc)
        if reason.startswith(('TABLE74_NATIVE_FAULT:', 'TABLE74_NATIVE_STATUS:')):
            raise
        if reason.startswith('TABLE74_NATIVE_DURATION:'):
            # This error is reached only after the exact identity and ordered
            # SUCCESS summary were established by the strict validator. A
            # positive early spent_time remains evidence of incomplete motion.
            durations = [re.fullmatch(r'spent_time:\s*('+_NUMBER+r')\s+s', message)
                         for message in messages if message.startswith('spent_time:')]
            if len(durations) == 1 and durations[0] is not None:
                spent = float(durations[0][1])
                if math.isfinite(spent) and spent < nominal-MIN_DURATION_TOLERANCE_S:
                    raise
        elif not reason.startswith(('TABLE74_NATIVE_LOG_INVALID:', 'TABLE74_NATIVE_IDENTITY:',
                                    'TABLE74_NATIVE_SUMMARY:')):
            # Do not conceal programming/import errors or a changed contract.
            raise
        report = None
    else:
        reason = None
    unavailable = query_error is not None or reader_failure is not None
    if report is not None and not unavailable:
        return dict(report, diagnostic_status='complete', guard_policy=GUARD_POLICY,
                    critical_fault_observed=False, reason=None)
    diagnostics = [part for part in (query_error, reader_failure, reason) if part]
    return dict(verified=False, diagnostic_status='unavailable' if unavailable else 'inconclusive',
        guard_policy=GUARD_POLICY, critical_fault_observed=False,
        reason='; '.join(diagnostics) if diagnostics else 'Native log query did not provide diagnostic evidence',
        task_name=task, bundle_id=bundle_id, expected_meta_name='MetaClamp',
        nominal_duration_s=nominal, clamp_status=None, spent_time_s=None,
        native_log_sha256=_sha(text) if type(text) is str else None,
        native_log_bytes=len(text.encode()) if type(text) is str else None,
        evidence_kind='supplementary_native_log_without_verified_transaction',
        physical_support_verified=False, pin_disengagement_verified=False,
        scope='Diagnostic only; an authenticated SDK terminal and live physical guards remain independently required.')
