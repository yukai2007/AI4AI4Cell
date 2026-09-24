"""CPU-only native-source and text-envelope regressions; no biological fits."""
import asyncio
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import airesearcher_adapter as adapter_module


def schema(name='plan_dataset'):
    return [{'type': 'function', 'function': {'name': name, 'description': 'native description',
        'parameters': {'type': 'object', 'properties': {'task_definition': {'type': 'string'}},
                       'required': ['task_definition']}}}]


class SequenceBackend:
    def __init__(self, responses):
        self.responses, self.messages, self.receipts = responses, [], []

    def __call__(self, messages, *, purpose):
        index = len(self.receipts)
        self.messages.append(copy.deepcopy(messages))
        receipt = dict(raw_response=self.responses[index], call_id=index, model='FAKE-TRANSPORT-TEST',
                       input_tokens=10, output_tokens=12, seconds=0., seed=42)
        self.receipts.append(receipt)
        return receipt


class MinimalBroker:
    def status(self):
        return dict(task='synthetic_transport_test', used_slots=0, remaining_slots=6, test_read=False)


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='airesearcher_transport_test_')
        self.output = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_rejects_multiple_json_prose_and_truncated_planning(self):
        valid = '{"tool":"plan_dataset","arguments":{"task_definition":"fixed task"}}'
        failures = [valid + '\n' + '{"tool":"case_resolved","arguments":{}}',
                    'First plan the dataset:\n```json\n' + valid + '\n```',
                    '{"tool":"plan_dataset","arguments":{"task_definition":"fixed task',
                    '{"tool":"auto","arguments":{}}',
                    '{"tool":"plan_dataset","arguments":null}',
                    '{"tool":"plan_dataset","arguments":[]}',
                    '{"tool":"plan_dataset","arguments":{},"unexpected":"outer field"}',
                    '{"final":"not a required tool call"}',
                    '{"tool":"plan_dataset","arguments":{"task_definition":NaN}}']
        for raw in failures:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                adapter_module._transport_response(raw, schema(), 'required')
        self.assertEqual(adapter_module._transport_response(valid, schema(), 'required')[1]['tool'], 'plan_dataset')
        self.assertEqual(adapter_module._transport_response('{"final":"short reasoning"}', schema(), 'auto'),
                         ('short reasoning', None))

    def test_description_adaptation_preserves_names_signatures_and_types(self):
        original = schema()
        adapted = adapter_module._transport_schema(original)
        self.assertEqual(original, schema())  # Do not mutate live native schemas.
        self.assertIn('natural-language', adapted[0]['function']['description'])
        adapted[0]['function']['description'] = original[0]['function']['description']
        adapted[0]['function']['parameters']['properties']['task_definition'].pop('description')
        self.assertEqual(adapted, original)

    def test_argument_values_are_preserved_and_current_tool_name_is_enforced(self):
        current = [{'function': {'name': 'case_resolved', 'parameters': {'properties': {
            'suggestion': {'type': 'object', 'additionalProperties': {'type': 'string'}}}, 'required': []}}}]
        for arguments in ({}, {'task_definition': 7}, {'task_definition': None},
                          {'task_definition': ['arbitrary', 'JSON']},
                          {'task_definition': 'fixed', 'context_variables': {}, 'extra': False}):
            payload = json.dumps({'tool': 'plan_dataset', 'arguments': arguments})
            with self.subTest(arguments=arguments):
                self.assertEqual(adapter_module._transport_response(payload, schema(), 'required')[1]['arguments'], arguments)
        for suggestion in (None, {'x': 4}, ['a'], 'text', 7, False):
            payload = json.dumps({'tool': 'case_resolved', 'arguments': {'suggestion': suggestion}})
            with self.subTest(suggestion=suggestion):
                self.assertEqual(adapter_module._transport_response(payload, current, 'required')[1]['arguments'], {'suggestion': suggestion})
        handoff = schema('transfer_to_judge_agent')
        payload = '{"tool":"transfer_to_judge_agent","arguments":{"task_definition":"review"}}'
        self.assertEqual(adapter_module._transport_response(payload, handoff, 'required')[1]['tool'], 'transfer_to_judge_agent')
        with self.assertRaises(ValueError):
            adapter_module._transport_response(payload, current, 'required')

    def test_format_retry_preserves_all_raw_receipts_without_fragment_dispatch(self):
        good = '{"tool":"plan_dataset","arguments":{"task_definition":"fixed task"}}'
        malformed = good + '\n{"tool":"case_resolved","arguments":{}}'
        backend = SequenceBackend([malformed, good])
        adapter = adapter_module.AIResearcherAdapter(MinimalBroker(), backend, self.output)
        response = asyncio.run(adapter._completion(messages=[{'role': 'system', 'content': 'test'}], tools=schema(), tool_choice='required'))
        self.assertEqual(len(adapter.receipts), 2)
        self.assertEqual(response.choices[0].message.tool_calls[0].function.name, 'plan_dataset')
        self.assertEqual(adapter.receipts[0]['raw_response'], malformed)
        self.assertIn('no plan or action in it was recorded', backend.messages[1][-1]['content'])
        trace = [json.loads(line) for line in adapter.trace_path.read_text().splitlines()]
        trace = [item for item in trace if item['event'] == 'model_completion']
        self.assertEqual([item['transport_accepted'] for item in trace], [False, True])
        self.assertEqual(adapter.usage()['calls'], 2)

    def test_auto_plain_text_is_native_final_without_format_repair(self):
        for raw in ('D08', '{"design_id": "D07"}', '["D07", "D08"]',
                    '{"analysis":{"metric":0.5}}',
                    '```json\n{"design_id": "D07"}\n```', '```\nD08\n```',
                    'Choose D04 because its registered regularization may improve development generalization.'):
            with self.subTest(raw=raw):
                backend = SequenceBackend([raw])
                adapter = adapter_module.AIResearcherAdapter(MinimalBroker(), backend, self.output)
                response = asyncio.run(adapter._completion(messages=[{'role': 'system', 'content': 'test'}],
                    tools=schema(), tool_choice='auto'))
                self.assertEqual(response.choices[0].message.content, raw)
                self.assertFalse(response.choices[0].message.tool_calls)
                self.assertEqual(len(backend.receipts), 1)
                with self.assertRaises(ValueError):
                    adapter_module._transport_response(raw, schema(), 'required')

    def test_auto_malformed_claimed_tool_call_is_not_plain_final(self):
        for raw in ('{"tool":"auto","arguments":{}}',
                    'I will call {"tool":"plan_dataset","arguments":{}}',
                    '{"tool":"plan_dataset","arguments":{}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                adapter_module._transport_response(raw, schema(), 'auto')

    def test_only_zero_arity_tool_can_omit_empty_argument_object(self):
        zero = [{'function': {'name': 'case_resolved', 'parameters': {'properties': {}, 'required': []}}}]
        raw = '{"tool":"case_resolved"}'
        self.assertEqual(adapter_module._transport_response(raw, zero, 'required'),
                         (None, {'tool': 'case_resolved', 'arguments': {}}))
        with self.assertRaises(ValueError):
            adapter_module._transport_response('{"tool":"plan_dataset"}', schema(), 'required')
        optional = copy.deepcopy(zero)
        optional[0]['function']['parameters']['properties']['note'] = {'type': 'string'}
        with self.assertRaises(ValueError):
            adapter_module._transport_response(raw, optional, 'required')
        backend = SequenceBackend([raw])
        adapter = adapter_module.AIResearcherAdapter(MinimalBroker(), backend, self.output)
        response = asyncio.run(adapter._completion(messages=[{'role': 'system', 'content': 'test'}], tools=zero, tool_choice='required'))
        self.assertEqual(response.choices[0].message.tool_calls[0].function.arguments, '{}')
        receipt = json.loads(adapter.trace_path.read_text().splitlines()[-1])
        self.assertEqual(receipt['raw_response'], raw)
        self.assertEqual(receipt['transport_normalization'], 'omitted_empty_argument_object_for_zero_arity_tool')

    def test_explicit_single_call_codec_preserves_arguments_and_records_shapes(self):
        arguments = {'task_definition': 'fixed 中文 \\n literal', 'extra': None, 'nested': {'x': [1, False]}}
        forms = [({'tool': 'plan_dataset', 'arguments': arguments}, 'tool_arguments', 'object'),
                 ({'name': 'plan_dataset', 'arguments': arguments}, 'name_arguments', 'object'),
                 ({'name': 'plan_dataset', 'arguments': json.dumps(arguments)}, 'name_arguments', 'json_string'),
                 ({'function': {'name': 'plan_dataset', 'arguments': arguments}}, 'function_wrapper', 'object'),
                 ({'id': 'explicit-call', 'type': 'function', 'function': {'name': 'plan_dataset',
                   'arguments': json.dumps(arguments)}}, 'function_wrapper', 'json_string'),
                 ({'plan_dataset': arguments}, 'exposed_tool_key', 'object')]
        for payload, shape, encoding in forms:
            raw = json.dumps(payload, ensure_ascii=False)
            for policy in ('required', 'auto'):
                with self.subTest(shape=shape, encoding=encoding, policy=policy):
                    backend = SequenceBackend([raw])
                    adapter = adapter_module.AIResearcherAdapter(MinimalBroker(), backend, self.output)
                    response = asyncio.run(adapter._completion(messages=[{'role': 'system', 'content': 'test'}],
                        tools=schema(), tool_choice=policy))
                    call = response.choices[0].message.tool_calls[0].function
                    self.assertEqual(call.name, 'plan_dataset')
                    self.assertEqual(json.loads(call.arguments), arguments)
                    receipt = json.loads(adapter.trace_path.read_text().splitlines()[-1])
                    self.assertEqual(receipt['raw_response'], raw)
                    self.assertEqual(receipt['normalization_shape'],
                                     {'shape': shape, 'wrappers': [], 'arguments_encoding': encoding})
                    self.assertEqual(len(backend.receipts), 1)

    def test_whole_fence_and_tool_call_wrappers_normalize_without_prose_extraction(self):
        payload = '{"plan_dataset":{"task_definition":"fixed"}}'
        cases = [('```json\n' + payload + '\n```', ['json_fence']),
                 ('```\n' + payload + '\n```', ['json_fence']),
                 ('<tool_call>' + payload + '</tool_call>', ['tool_call_wrapper']),
                 ('<tool_call>```json\n' + payload + '\n```</tool_call>', ['tool_call_wrapper', 'json_fence']),
                 ('```json\n<tool_call>' + payload + '</tool_call>\n```', ['json_fence', 'tool_call_wrapper'])]
        for raw, wrappers in cases:
            with self.subTest(raw=raw):
                _, decoded, metadata = adapter_module._decode_transport_response(raw, schema(), 'required')
                self.assertEqual(decoded, {'tool': 'plan_dataset', 'arguments': {'task_definition': 'fixed'}})
                self.assertEqual(metadata['wrappers'], wrappers)
                for bad in ('Here is the call: ' + raw, raw + '\nExplanation', raw + '\n' + raw):
                    with self.assertRaises(ValueError):
                        adapter_module._transport_response(bad, schema(), 'auto')

    def test_ambiguous_unknown_and_nonobject_calls_are_never_normalized(self):
        other = schema('other_tool')
        live = schema() + other
        bad_calls = [
            {'plan_dataset': {}, 'other_tool': {}}, {'plan_dataset': {}, 'extra': 'prose'},
            {'plan_dataset': []}, {'plan_dataset': None}, {'plan_dataset': '{}'},
            {'tool': 'unknown', 'arguments': {}}, {'name': 'unknown', 'arguments': {}},
            {'function': {'name': 'unknown', 'arguments': {}}},
            {'tool': 'plan_dataset', 'arguments': {}, 'function': {'name': 'other_tool', 'arguments': {}}},
            {'function': {'name': 'plan_dataset', 'arguments': {}}, 'extra': {}},
            {'function': {'name': 'plan_dataset', 'arguments': {}}, 'type': 'other'},
            {'function': {'name': 'plan_dataset', 'arguments': {}}, 'id': 3},
            {'function': {'name': 'plan_dataset'}}, {'name': 'plan_dataset', 'arguments': []},
            {'tool_calls': [{'function': {'name': 'plan_dataset', 'arguments': {}}}]},
        ]
        for payload in bad_calls:
            for policy in ('required', 'auto'):
                with self.subTest(payload=payload, policy=policy), self.assertRaises(ValueError):
                    adapter_module._transport_response(json.dumps(payload), live, policy)
        for raw in ('{"unknown_tool":{}}', '{"name":"plan_dataset"}', '{"arguments":{}}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                adapter_module._transport_response(raw, live, 'required')
        for raw in ('<tool_call>{"unknown_tool":{}}</tool_call>',
                    '{"plan_dataset":{},"plan_dataset":{"task_definition":"second"}}',
                    '<tool_call>{"plan_dataset":{}}</tool_call><tool_call>{"other_tool":{}}</tool_call>'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                adapter_module._transport_response(raw, live, 'auto')

    def test_standard_argument_strings_decode_exactly_once_as_a_single_object(self):
        for encoded in ('null', '[]', '"{}"', '{} {}', '{"x":1,"x":2}', '```json\n{}\n```', '{"x":NaN}'):
            raw = json.dumps({'function': {'name': 'plan_dataset', 'arguments': encoded}})
            with self.subTest(encoded=encoded), self.assertRaises(ValueError):
                adapter_module._transport_response(raw, schema(), 'required')
        for payload in ({'tool': 'plan_dataset', 'arguments': '{}'}, {'plan_dataset': '{}'}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                adapter_module._transport_response(json.dumps(payload), schema(), 'required')

    def test_retries_are_bounded_and_count_toward_global_cap(self):
        backend = SequenceBackend(['not JSON'] * 3)
        adapter = adapter_module.AIResearcherAdapter(MinimalBroker(), backend, self.output)
        kwargs = dict(messages=[{'role': 'system', 'content': 'test'}], tools=schema(), tool_choice='required')
        with self.assertRaisesRegex(adapter_module.NativeRunIncomplete, '3 format attempts'):
            asyncio.run(adapter._completion(**kwargs))
        self.assertEqual(len(adapter.receipts), 3)
        capped = adapter_module.AIResearcherAdapter(MinimalBroker(), SequenceBackend(['bad'] * 2), self.output, max_model_calls=2)
        with self.assertRaisesRegex(adapter_module.NativeRunIncomplete, 'Global model-call cap'):
            asyncio.run(capped._completion(**kwargs))
        self.assertEqual(len(capped.receipts), 2)

    def test_unknown_design_remains_broker_policy_not_transport_policy(self):
        tools = [{'function': {'name': 'evaluate_design', 'parameters': {'properties': {
            key: {'type': 'string'} for key in ('design_id', 'hypothesis', 'experiment', 'expected_effect')},
            'required': ['design_id', 'hypothesis', 'experiment', 'expected_effect']}}}]
        raw = json.dumps(dict(tool='evaluate_design', arguments=dict(design_id='D0X', hypothesis='test', experiment='test', expected_effect='test')))
        self.assertEqual(adapter_module._transport_response(raw, tools, 'required')[1]['arguments']['design_id'], 'D0X')

    def test_native_plan_functions_keep_state_and_premature_completion_error(self):
        adapter = adapter_module.AIResearcherAdapter(MinimalBroker(), SequenceBackend([]), self.output)
        adapter._build()
        agent = adapter.flow.coding_plan_agent.agent
        functions = {function.__name__: function for function in agent.functions}
        context = {'model_survey': 'Native code-survey state fixture'}
        with self.assertRaisesRegex(KeyError, 'dataset_plan'):
            functions['case_resolved'](context)
        plans = {
            'plan_dataset': dict(dataset_description='fixed task', dataset_location='trusted broker', task_definition='fixed task',
                read_data_step='trusted pipeline', data_preprocessing_step='unchanged', data_dataloader_step='ten clients'),
            'plan_training': dict(training_pipeline='trusted fitter', loss_function='native', optimizer='native',
                training_configurations='100 rounds', monitor_and_logging='development only'),
            'plan_testing': dict(test_metric='registered primary', test_data='development partition', test_code='trusted evaluator'),
        }
        for name, arguments in plans.items():
            result = functions[name](**arguments)
            context.update(result.context_variables)
            self.assertTrue(functions[name].__code__.co_filename.endswith('tools/inno_tools/planning_tools.py'))
        self.assertIn('Dataset Plan', functions['case_resolved'](context))
        instructions = agent.instructions(context)
        self.assertNotIn('MISSING', instructions)
        planning_record = next(record for record in adapter.source_records if record['path'].endswith('planning_tools.py'))
        self.assertEqual(planning_record['edits'], [])

    def test_untyped_native_text_schema_correction_keeps_function_signature(self):
        adapter = adapter_module.AIResearcherAdapter(MinimalBroker(), SequenceBackend([]), self.output)
        adapter._build()
        original = next(function for function in adapter.flow.ml_agent.agent.functions if function.__name__ == 'case_resolved')
        signature = adapter_module.inspect.signature(original)
        self.assertIs(signature.parameters['task_response'].annotation, adapter_module.inspect.Parameter.empty)
        native = adapter.native['util'].function_to_json(original)
        self.assertEqual(native['function']['parameters']['properties']['task_response']['type'], 'object')
        adapted = adapter_module._transport_schema([native])
        self.assertEqual(adapted[0]['function']['parameters']['properties']['task_response']['type'], 'string')
        self.assertEqual(adapter_module.inspect.signature(original), signature)
        self.assertEqual(original('original native report'), 'original native report')

    def test_native_failed_completion_receipt_does_not_count_as_stage_completion(self):
        backend = SequenceBackend(['{"tool":"case_resolved","arguments":{}}'])
        adapter = adapter_module.AIResearcherAdapter(MinimalBroker(), backend, self.output, max_stage_messages=2)
        adapter._build()
        with mock.patch.object(adapter.native['core'], 'acompletion', adapter._completion):
            with self.assertRaisesRegex(adapter_module.NativeRunIncomplete, 'failed completion/tool receipt'):
                asyncio.run(adapter.flow.client.run_async(adapter.flow.coding_plan_agent.agent,
                    [{'role': 'user', 'content': 'transport regression'}], context_variables={'model_survey': 'native fixture'}))

    def test_complete_judge_null_call_passes_through_original_native_runner(self):
        raw = '{"tool":"case_resolved","arguments":{"fully_correct":true,"suggestion":null}}'
        backend = SequenceBackend([raw])
        adapter = adapter_module.AIResearcherAdapter(MinimalBroker(), backend, self.output)
        adapter._build()
        judge = adapter.flow.judge_agent.agent
        native_function = next(function for function in judge.functions if function.__name__ == 'case_resolved')
        self.assertTrue(native_function.__code__.co_filename.endswith('agents/inno_agent/judge_agent.py'))
        native_schema = adapter.native['util'].function_to_json(native_function)
        self.assertEqual(native_schema['function']['parameters']['properties']['suggestion']['type'], 'object')
        with mock.patch.object(adapter.native['core'], 'acompletion', adapter._completion):
            response = asyncio.run(adapter.flow.client.run_async(judge,
                [{'role': 'user', 'content': 'native null compatibility regression'}], context_variables={}))
        self.assertEqual(response.context_variables['suggestion_dict'], {'fully_correct': True, 'suggestion': None})
        self.assertEqual(response.messages[-1]['name'], 'case_resolved')
        self.assertNotIn('[Tool Call Error]', response.messages[-1]['content'])
        self.assertEqual(backend.receipts[0]['raw_response'], raw)
        self.assertEqual(len(backend.receipts), 1)
        completions = [json.loads(line) for line in adapter.trace_path.read_text().splitlines()
                       if json.loads(line)['event'] == 'model_completion']
        self.assertEqual([(item['transport_accepted'], item['format_attempt']) for item in completions], [(True, 0)])

    def test_keyed_case_resolved_calls_actual_native_experiment_analysis_function(self):
        arguments = {'analysis_report': 'CPU codec regression only; no biological evidence.',
                     'further_plan': {'explicit-test-plan': 'Preserve the supplied plan unchanged.'}}
        raw = json.dumps({'case_resolved': arguments})
        backend = SequenceBackend([raw])
        adapter = adapter_module.AIResearcherAdapter(MinimalBroker(), backend, self.output)
        adapter._build()
        agent = adapter.flow.exp_analyser.agent
        function = next(function for function in agent.functions if function.__name__ == 'case_resolved')
        self.assertTrue(function.__code__.co_filename.endswith('agents/inno_agent/exp_analyser.py'))
        with mock.patch.object(adapter.native['core'], 'acompletion', adapter._completion):
            response = asyncio.run(adapter.flow.client.run_async(agent,
                [{'role': 'user', 'content': 'native codec regression'}], context_variables={}))
        self.assertEqual(response.context_variables['experiment_report'], [arguments])
        self.assertEqual(response.messages[-1]['name'], 'case_resolved')
        self.assertNotIn('[Tool Call Error]', response.messages[-1]['content'])
        self.assertEqual(len(backend.receipts), 1)
        receipt = json.loads(adapter.trace_path.read_text().splitlines()[-1])
        self.assertEqual(receipt['raw_response'], raw)
        self.assertEqual(receipt['normalization_shape']['shape'], 'exposed_tool_key')
        self.assertTrue(receipt['transport_accepted'])

    def test_missing_and_extra_arguments_produce_real_native_invocation_errors(self):
        adapter = adapter_module.AIResearcherAdapter(MinimalBroker(), SequenceBackend([]), self.output)
        adapter._build()
        judge = adapter.flow.judge_agent.agent
        core = adapter.native['core']
        live_schema = [adapter.native['util'].function_to_json(function) for function in judge.functions]
        for arguments, error in (({}, "missing 1 required positional argument: 'fully_correct'"),
                                 ({'fully_correct': True, 'unexpected': 'x'}, "unexpected keyword argument 'unexpected'")):
            with self.subTest(arguments=arguments):
                raw = json.dumps({'tool': 'case_resolved', 'arguments': arguments})
                adapter.backend = SequenceBackend([raw])
                transport = asyncio.run(adapter._completion(messages=[{'role': 'system', 'content': 'test'}],
                    tools=live_schema, tool_choice='required'))
                # Invoke the original source dispatcher, not an adapter-created
                # result or schema error. Its real TypeError is retained.
                response = core.MetaChain.handle_tool_calls(adapter.flow.client,
                    transport.choices[0].message.tool_calls, judge.functions, {}, debug=False)
                self.assertEqual(len(adapter.backend.receipts), 1)
                self.assertTrue(response.messages[-1]['content'].startswith('[Tool Call Error]'))
                self.assertIn(error, response.messages[-1]['content'])
                self.assertNotIn('suggestion_dict', response.context_variables)
                completion = json.loads(adapter.trace_path.read_text().splitlines()[-1])
                self.assertTrue(completion['transport_accepted'])
                self.assertEqual(completion['format_attempt'], 0)

    def budget_run(self, designs):
        from broker import Broker, BrokerConfig, DESIGNS, TASK_DESCRIPTIONS
        from test_broker import FakeFitter
        root = self.output / ('all_invalid' if all(name.startswith('BAD') for name in designs) else 'mixed_invalid')
        native = root/'native'
        broker = Broker(BrokerConfig(task='ptpc_neural', seed=42, harness='GLOBAL-BUDGET-UNIT-TEST',
            output_dir=str(root/'development'), upstream_repo=str(adapter_module.DEFAULT_UPSTREAM),
            upstream_commit=adapter_module.PINNED_COMMIT, native_trace_path=str(native/'native_trace.jsonl')),
            fitter=FakeFitter([(0.5, 1.), (0.6, .9)]), test_binding={'test_only': True})
        def call(name, **arguments):
            return json.dumps({'tool': name, 'arguments': arguments})
        responses = [json.dumps({'final': 'unit test menu reasoning'})] * 7
        responses += [call('plan_dataset', dataset_description='fixed', dataset_location='broker', task_definition='fixed',
                          read_data_step='trusted', data_preprocessing_step='unchanged', data_dataloader_step='ten clients'),
                      call('plan_training', training_pipeline='trusted', loss_function='native', optimizer='native',
                           training_configurations='100 rounds', monitor_and_logging='development'),
                      call('plan_testing', test_metric='primary', test_data='development', test_code='trusted'),
                      call('case_resolved')]
        responses += [call('evaluate_design', design_id=name, hypothesis='unit test', experiment='unit test',
                           expected_effect='unit test') for name in designs]
        backend = SequenceBackend(responses)
        adapter = adapter_module.AIResearcherAdapter(broker, backend, native)
        adapter.registered_designs, adapter.task_description = DESIGNS, TASK_DESCRIPTIONS['ptpc_neural']
        result = adapter.run()
        self.assertEqual(len(backend.receipts), 17)  # No model request after the sixth charged proposal.
        self.assertEqual(broker.status()['used_slots'], 6)
        self.assertEqual(result['termination_reason'], 'global_proposal_budget_exhausted')
        self.assertEqual(len(list((root/'development/requests').glob('slot_*.json'))), 6)
        self.assertFalse((root/'development/requests/slot_07.json').exists())
        self.assertEqual([event['agent'] for event in adapter.stage_events].count('Machine Learning Agent'), 1)
        return broker, root, result

    def test_multiple_invalid_and_duplicate_attempts_in_one_native_stage_use_global_budget(self):
        from broker import read
        broker, root, result = self.budget_run(['D01', 'D01', 'BAD2', 'BAD3', 'BAD4', 'BAD5'])
        self.assertEqual(broker.status()['incumbent']['development']['primary'], .6)
        receipts = [read(path) for path in sorted((root/'development/requests').glob('slot_*.json'))]
        self.assertEqual(receipts[0]['status'], 'COMPLETE')
        self.assertEqual(receipts[1]['status'], 'DUPLICATE')
        self.assertTrue(all(item['status'] == 'INVALID' for item in receipts[2:]))

    def test_six_invalid_attempts_seal_the_valid_fixed_D00_incumbent(self):
        from broker import read
        broker, root, result = self.budget_run([f'BAD{i}' for i in range(6)])
        self.assertEqual(broker.status()['incumbent'], broker.status()['baseline'])
        self.assertTrue((root/'development/selection_seal.json').is_file())
        self.assertTrue(all(read(path)['status'] == 'INVALID' for path in (root/'development/requests').glob('slot_*.json')))

    def test_natural_return_at_six_slots_uses_same_sealing_path(self):
        class NaturalBroker:
            def __init__(self):
                self.used = 0
            def initialize(self):
                return self.status()
            def status(self):
                return {'used_slots': self.used, 'status': 'READY'}
            def seal_selection(self):
                self.assert_budget = self.used == 6
                return {'test_only': True}
        class NaturalAdapter(adapter_module.AIResearcherAdapter):
            def _build(self):
                # Unit fixture for the outer exit/seal path, not an alternate framework.
                from types import SimpleNamespace
                self.native = {'core': SimpleNamespace(acompletion=None)}
                async def completed_flow(**kwargs):
                    self.broker.used = 6
                self.flow = completed_flow
        broker = NaturalBroker()
        adapter = NaturalAdapter(broker, SequenceBackend([]), self.output/'natural_return')
        result = adapter.run()
        self.assertEqual(result['termination_reason'], 'native_return')
        self.assertTrue(broker.assert_budget)


if __name__ == '__main__':
    unittest.main()
