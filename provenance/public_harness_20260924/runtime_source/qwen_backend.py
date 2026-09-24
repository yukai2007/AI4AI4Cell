"""Local text transport for source-native public-harness controller adapters.

This backend makes no design decisions and executes no model-generated code.
Each native controller retains its own messages; generation settings match the
original main-table Qwen researcher. Every completion is recorded separately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

MODEL = Path('/liziqing/yukai/.cache/modelscope/Qwen2.5-7B-Instruct')


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.tmp-{os.getpid()}')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    os.replace(tmp, path)


class LocalQwenBackend:
    def __init__(self, output_dir, *, seed=42, device='cuda:0', max_calls=160,
                 max_new_tokens=512, max_input_tokens=28000):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        torch.set_num_threads(2)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if list(self.output_dir.glob('call_*.json')):
            raise ValueError('Use a fresh backend directory; completion history must not be overwritten.')
        self.seed = seed
        self.device = device
        self.max_calls = max_calls
        self.max_new_tokens = max_new_tokens
        self.max_input_tokens = max_input_tokens
        self.receipts = []
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(MODEL, local_files_only=True,
            torch_dtype=torch.bfloat16, device_map={'': device}, attn_implementation='sdpa').eval()
        metadata = dict(model=str(MODEL), generation_backend='local Transformers',
                        torch_version=torch.__version__, device=device,
                        model_config={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in [MODEL/'config.json', MODEL/'generation_config.json',
                                                MODEL/'tokenizer_config.json', MODEL/'model.safetensors.index.json']
                                      if p.is_file()}, seed=seed,
                        sampling=dict(temperature=.7, top_p=.9, max_new_tokens=max_new_tokens),
                        max_calls=max_calls, max_input_tokens=max_input_tokens,
                        token_budget_note='Per-call cap matches main Qwen. Native controller call counts may differ and are reported.',
                        generated_code_executed=False)
        dump(self.output_dir/'backend.json', metadata)

    def __call__(self, messages, *, purpose):
        if len(self.receipts) >= self.max_calls:
            raise RuntimeError('Native-controller completion cap reached; no implicit fallback.')
        if not messages or any(m.get('role') not in {'system', 'user', 'assistant', 'tool'}
                               or not isinstance(m.get('content'), str) for m in messages):
            raise ValueError('Text backend requires explicit text-only native messages.')
        call_id = len(self.receipts)
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        batch = self.tokenizer(prompt, return_tensors='pt').to(self.device)
        input_tokens = int(batch.input_ids.shape[1])
        if input_tokens > self.max_input_tokens:
            raise RuntimeError('Native context exceeds declared token limit; no silent truncation.')
        seed = self.seed + call_id
        self.torch.manual_seed(seed)
        start = time.monotonic()
        with self.torch.inference_mode():
            tokens = self.model.generate(**batch, max_new_tokens=self.max_new_tokens,
                do_sample=True, temperature=.7, top_p=.9,
                pad_token_id=self.tokenizer.eos_token_id)
        generated = tokens[0, input_tokens:]
        receipt = dict(call_id=call_id, purpose=purpose, model=str(MODEL),
            raw_response=self.tokenizer.decode(generated, skip_special_tokens=True),
            input_tokens=input_tokens, output_tokens=int(generated.shape[0]),
            seconds=time.monotonic()-start, seed=seed,
            sampling=dict(temperature=.7, top_p=.9, max_new_tokens=self.max_new_tokens),
            messages=messages, generated_code_executed=False)
        dump(self.output_dir/f'call_{call_id:04d}.json', receipt)
        self.receipts.append(receipt)
        dump(self.output_dir/'usage.json', self.usage())
        return receipt

    def usage(self):
        return dict(calls=len(self.receipts),
                    input_tokens=sum(r['input_tokens'] for r in self.receipts),
                    output_tokens=sum(r['output_tokens'] for r in self.receipts),
                    generation_seconds=sum(r['seconds'] for r in self.receipts),
                    model=str(MODEL), seed=self.seed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', default='cuda:0')
    args = parser.parse_args()
    backend = LocalQwenBackend(args.output, device=args.device, max_calls=2)
    receipt = backend([{'role': 'system', 'content': 'Return JSON only. Do not use tools.'},
                       {'role': 'user', 'content': 'Return exactly {"ready": true}.'}], purpose='transport_smoke')
    response = receipt['raw_response'].strip()
    start = response.index('{')
    parsed, _ = json.JSONDecoder().raw_decode(response[start:])
    assert parsed == {'ready': True}, receipt['raw_response']
    print(json.dumps(dict(status='TRANSPORT_SMOKE_PASS', usage=backend.usage())))


if __name__ == '__main__':
    main()
