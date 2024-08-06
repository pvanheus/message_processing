#!/usr/bin/env python3

import argparse
import csv
import io
import json
import sys

from pprint import pprint

from openai import OpenAI


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('batch_id')
    parser.add_argument('output_file', type=argparse.FileType('w'), nargs='?', default=sys.stdout)
    args = parser.parse_args()

    client = OpenAI()
    batch_info = client.batches.retrieve(args.batch_id)

    if batch_info.status == 'completed':
        file_id = batch_info.output_file_id
        file_response = client.files.content(file_id).content
        output_text = io.StringIO(file_response.decode('utf-8'))
        results = []
        for line in output_text:
            results.append(json.loads(line.strip()))
        output_writer = csv.DictWriter(args.output_file, fieldnames=['date', 'user_id', 'theme', 'message'])
        output_writer.writeheader()   
        for result in results:
            task_id = result['custom_id']
            index = task_id.split('-')[-1]
            result_text = result['response']['body']['choices'][0]['message']['content']
            output_writer.writerow(json.loads(result_text))
        print('DONE', file=sys.stderr)
    else:
        pprint(batch_info)
