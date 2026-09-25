import json
import unittest
import airesearcher_transport_v2 as repair

SCHEMA=[{'function':{'name':'case_resolved','parameters':{'properties':{},'required':[]}}}]


class NativeEnvelopeTests(unittest.TestCase):
    def test_equivalent_single_calls_preserve_values(self):
        args={'analysis_report':'exact measured report','further_plan':{'design':'D08'}}
        call={'function':{'name':'case_resolved','arguments':json.dumps(args)},'type':'function','id':'native_37'}
        for raw in [json.dumps([call]),'Tool calls: '+json.dumps([call]),
                    json.dumps({'tool_calls':[call]}),json.dumps({'tool_choice':'required','tools':[call]})]:
            _,decoded,note=repair.decode_transport(raw,SCHEMA,'required')
            self.assertEqual(decoded,{'tool':'case_resolved','arguments':args})
            self.assertIn('native_envelope',note)

    def test_ambiguity_and_fragments_are_rejected(self):
        call={'tool':'case_resolved','arguments':{}}
        for raw in [json.dumps([call,call]),'prose '+json.dumps([call]),json.dumps([]),
                    '{"tool_calls":[],"tool_calls":[]}',
                    json.dumps({'tool_choice':'invented','tools':[call]})]:
            with self.assertRaises(ValueError):repair.decode_transport(raw,SCHEMA,'required')

    def test_canonical_calls_and_auto_text_unchanged(self):
        for raw,mode in [('an ordinary idea','auto'),('["idea one", "idea two"]','auto'),
                         ('{"tool":"case_resolved","arguments":{}}','required')]:
            self.assertEqual(repair.decode_transport(raw,SCHEMA,mode),repair.compact.decode_transport(raw,SCHEMA,mode))


if __name__=='__main__':unittest.main()
