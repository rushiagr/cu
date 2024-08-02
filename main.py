import json
from typing import List, Dict, Any

def process_json(input_file: str, output_file1: str, output_file2: str, keys_to_retain: List[str]) -> None:
    with open(input_file, 'r') as infile, open(output_file1, 'w') as outfile1, open(output_file2, 'w') as outfile2:
        for line in infile:
            json_obj: Dict[str, Any] = json.loads(line.strip())
            output_obj1: Dict[str, Any] = {}
            output_obj2: Dict[str, Any] = {}

            for key, value in json_obj.items():
                if isinstance(value, dict) and any(k in value for k in keys_to_retain):
                    retained: Dict[str, Any] = {k: value[k] for k in keys_to_retain if k in value}
                    remaining: Dict[str, Any] = {k: v for k, v in value.items() if k not in keys_to_retain}
                    if retained:
                        output_obj1[key] = retained
                    if remaining:
                        output_obj2[key] = remaining
                else:
                    output_obj1[key] = value
                    output_obj2[key] = value

            json.dump(output_obj1, outfile1)
            outfile1.write('\n')
            json.dump(output_obj2, outfile2)
            outfile2.write('\n')

# Usage
input_file: str = 'input.json'
output_file1: str = 'output1.json'
output_file2: str = 'output2.json'
keys_to_retain: List[str] = ['timestamp', 'last_price']

process_json(input_file, output_file1, output_file2, keys_to_retain)