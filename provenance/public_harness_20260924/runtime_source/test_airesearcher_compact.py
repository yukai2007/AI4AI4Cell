import json
import unittest
from unittest import mock
import airesearcher_adapter as native
import airesearcher_compact as compact

SCHEMA = [{'type': 'function', 'function': {'name': 'evaluate_design',
          'parameters': {'type': 'object', 'properties': {'design_id': {'type': 'string'}}}}}]


class CompactTests(unittest.TestCase):
    def test_alias_preserves_every_argument(self):
        for key in ('tool', 'name'):
            args = {'design_id': 'D08', 'extra': None, 'hypothesis': 'keep exact'}
            _, decoded, note = compact.decode_transport(json.dumps({key:'evaluate_design', 'parameters':args}), SCHEMA, 'required')
            self.assertEqual(decoded, {'tool':'evaluate_design', 'arguments':args})
            self.assertEqual(note['alias'], 'parameters_to_arguments')

    def test_no_guessing_ambiguous_or_unknown_calls(self):
        for obj in ({'tool':'evaluate_design', 'arguments':{}, 'parameters':{}},
                    {'tool':'unknown', 'parameters':{}}, {'tool':'evaluate_design','parameters':None}):
            with self.assertRaises(ValueError):
                compact.decode_transport(json.dumps(obj), SCHEMA, 'required')
        with self.assertRaises(ValueError):
            compact.decode_transport('{"tool":"evaluate_design","parameters":{}}\n{"final":"x"}', SCHEMA, 'required')

    def test_original_semantics_remain(self):
        for raw, choice in [('an ordinary native idea', 'auto'),
                            ('{"tool":"evaluate_design","arguments":{"design_id":"D01"}}','required')]:
            self.assertEqual(compact.decode_transport(raw, SCHEMA, choice),
                             compact.ORIGINAL_DECODE(raw, SCHEMA, choice))

    def test_only_task_packet_removed_and_recorded(self):
        adapter = object.__new__(compact.CompactAIResearcher)
        packet = {'native_prompt_stage':'refine_query', 'stage_action':'preserve',
                  'task': {'measurements':[.5,.7], 'menu': ['D00','D01']},
                  'native_stage_inputs': {'ideas':['unchanged'], 'analysis_report':'exact text'}}
        with mock.patch.object(native.AIResearcherAdapter, '_task_prompt', return_value=json.dumps(packet)), \
             mock.patch.object(adapter, '_trace') as trace:
            result = json.loads(adapter._task_prompt('refine_query', {}))
        for key in ('native_prompt_stage','stage_action','native_stage_inputs'):
            self.assertEqual(result[key], packet[key])
        self.assertEqual(trace.call_args.kwargs['removed_packet'],packet['task'])
        self.assertNotIn('task',result)

    def test_codec_restored_after_controller_failure(self):
        adapter = object.__new__(compact.CompactAIResearcher)
        before = native._decode_transport_response
        with mock.patch.object(native.AIResearcherAdapter, 'run', side_effect=RuntimeError('test')):
            with self.assertRaises(RuntimeError): adapter.run()
        self.assertIs(native._decode_transport_response,before)


if __name__ == '__main__': unittest.main()
