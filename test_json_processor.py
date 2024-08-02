import unittest
import json
import tempfile
import os
from typing import List, Dict, Any
from main import process_json


class TestJsonProcessor(unittest.TestCase):
    def setUp(self) -> None:
        self.test_data: List[Dict[str, Any]] = [
            {
                "BFO:BANKEX24JUL50700CE": {
                    "instrument_token": 287434501,
                    "timestamp": "2024-07-29T09:16:20",
                    "last_price": 7966.9,
                    "volume": 0
                },
                "_meta": {"timestamp": "2024-07-29T06:26:08.347727"}
            },
            {
                "Another:Key": {
                    "timestamp": "2024-07-29T10:00:00",
                    "price": 100.0
                }
            }
        ]

    def test_process_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file: str = os.path.join(tmpdir, 'input.json')
            output_file1: str = os.path.join(tmpdir, 'output1.json')
            output_file2: str = os.path.join(tmpdir, 'output2.json')

            # Write test data to input file
            with open(input_file, 'w') as f:
                for item in self.test_data:
                    json.dump(item, f)
                    f.write('\n')

            keys_to_retain: List[str] = ['timestamp', 'last_price']

            # Run the function
            process_json(input_file, output_file1, output_file2, keys_to_retain)

            # Check output files
            with open(output_file1, 'r') as f:
                output1: List[Dict[str, Any]] = [json.loads(line) for line in f]

            with open(output_file2, 'r') as f:
                output2: List[Dict[str, Any]] = [json.loads(line) for line in f]

            # Assertions for output1
            self.assertEqual(len(output1), 2)
            self.assertEqual(output1[0]['BFO:BANKEX24JUL50700CE']['timestamp'], "2024-07-29T09:16:20")
            self.assertEqual(output1[0]['BFO:BANKEX24JUL50700CE']['last_price'], 7966.9)
            self.assertNotIn('instrument_token', output1[0]['BFO:BANKEX24JUL50700CE'])
            self.assertEqual(output1[0]['_meta']['timestamp'], "2024-07-29T06:26:08.347727")
            self.assertEqual(output1[1]['Another:Key']['timestamp'], "2024-07-29T10:00:00")
            self.assertNotIn('price', output1[1]['Another:Key'])

            # Assertions for output2
            self.assertEqual(len(output2), 2)
            self.assertEqual(output2[0]['BFO:BANKEX24JUL50700CE']['instrument_token'], 287434501)
            self.assertEqual(output2[0]['BFO:BANKEX24JUL50700CE']['volume'], 0)
            self.assertNotIn('timestamp', output2[0]['BFO:BANKEX24JUL50700CE'])
            self.assertNotIn('last_price', output2[0]['BFO:BANKEX24JUL50700CE'])
            self.assertEqual(output2[0]['_meta']['timestamp'], "2024-07-29T06:26:08.347727")
            self.assertEqual(output2[1]['Another:Key']['price'], 100.0)
            self.assertNotIn('timestamp', output2[1]['Another:Key'])


if __name__ == '__main__':
    unittest.main()