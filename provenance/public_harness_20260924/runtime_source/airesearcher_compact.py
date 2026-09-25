"""Versioned task-prompt/codec repair; the frozen v6 adapter is unchanged.

The current system task packet contains the registered menu, broker state and
all measured candidate evidence. Stage prompts therefore need only their
native action and inherited reasoning, rather than another complete task copy.
Native stages, inherited reasoning, tool results and research budgets remain.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import airesearcher_adapter as native

VERSION = 'airesearcher-task-transport-compact-v1'
ORIGINAL_DECODE = native._decode_transport_response


def decode_transport(raw, schema, tool_choice):
    """Accept one unambiguous parameters->arguments envelope alias only."""
    try:
        payload, wrappers = native._unwrap_transport(raw)
        obj = native._json_object(payload)
    except ValueError:
        return ORIGINAL_DECODE(raw, schema, tool_choice)
    if set(obj) in ({'tool', 'parameters'}, {'name', 'parameters'}):
        obj['arguments'] = obj.pop('parameters')
        content, decoded, normal = ORIGINAL_DECODE(json.dumps(obj, ensure_ascii=False), schema, tool_choice)
        if decoded is None:
            raise ValueError('An explicit parameter envelope must name an available tool')
        normal = dict(normal, alias='parameters_to_arguments', original_wrappers=wrappers)
        return content, decoded, normal
    return ORIGINAL_DECODE(raw, schema, tool_choice)


class CompactAIResearcher(native.AIResearcherAdapter):
    def _task_prompt(self, stage, state):
        original = super()._task_prompt(stage, state)
        packet = json.loads(original)
        repeated = packet.pop('task')
        packet['task_context'] = (
            'The current system message contains the complete registered task, '
            'design menu, budget state and all measured candidate evidence. '
            'read_task_artifact also returns this packet. Use the inherited '
            'native-stage reasoning below for this stage.')
        self._trace('task_packet_deduplicated', version=VERSION, stage=stage,
                    removed_packet=repeated,
                    original_prompt_sha256=hashlib.sha256(original.encode()).hexdigest(),
                    removed_characters=len(json.dumps(repeated, ensure_ascii=False)),
                    inherited_stage_inputs_unchanged=True)
        return json.dumps(packet, ensure_ascii=False)

    def _provenance(self):
        super()._provenance()
        path = self.output / 'provenance.json'
        record = json.loads(path.read_text())
        record['transport_revision'] = {
            'version': VERSION, 'source_sha256': native._sha(__file__),
            'context_policy': 'One authoritative current task packet in each system prompt; stage prompts preserve native actions and inherited reasoning, without repeated full task packets. Full removed packets recorded in trace.',
            'codec_alias': 'Exactly tool/parameters or name/parameters maps to the corresponding arguments envelope; no argument values, actions or fragments inferred.',
            'unchanged': ['upstream control flow', 'native reasoning history', 'tool results', 'model weights', '28000 input token cap', '512 output token cap', '160 model calls', '6 proposal slots', '100 training rounds', 'development selection', 'held-out scorer'],
        }
        native._dump(path, record)

    def run(self):
        # A runner process has one controller. Restore the module's codec even
        # on failure; never modify the frozen source or upstream worktree.
        previous = native._decode_transport_response
        native._decode_transport_response = decode_transport
        try:
            return super().run()
        finally:
            native._decode_transport_response = previous


def run_airesearcher(broker, text_backend, *, trace_dir, registered_designs,
                    task_description, task_name, seed, upstream_repo=native.DEFAULT_UPSTREAM):
    adapter = CompactAIResearcher(broker, text_backend, trace_dir, upstream=upstream_repo)
    adapter.task_description = task_description
    adapter.task_name = task_name
    adapter.registered_designs = copy.deepcopy(registered_designs)
    adapter.seed = seed
    return adapter.run()
