#!/usr/bin/env python3

import argparse
import csv
import io
import json
import re
import sys

from pprint import pprint

from openai import OpenAI


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('batch_id')
    parser.add_argument('--failed_messages_file', type=argparse.FileType('w'))
    parser.add_argument('output_file', type=argparse.FileType('w'), nargs='?', default=sys.stdout)
    args = parser.parse_args()

    client = OpenAI()
    batch_info = client.batches.retrieve(args.batch_id)

    many_eol_re = re.compile(r'(\\n *){2,}')
    if batch_info.status == 'completed':
        file_id = batch_info.output_file_id
        file_response = client.files.content(file_id).content
        output_text = io.StringIO(file_response.decode('utf-8'))
        results = []
        for line in output_text:
            line = line.strip()
            message_output = json.loads(line.strip())
            results.append(message_output)
        output_writer = csv.DictWriter(args.output_file, fieldnames=['date', 'user_id', 'theme', 'message'])
        output_writer.writeheader()
        failed_messages = []
        for result in results:
            task_id = result['custom_id']
            index = task_id.split('-')[-1]
            result_text = result['response']['body']['choices'][0]['message']['content']
            if not result_text.endswith('}'):
                result_text = re.sub(many_eol_re, '', result_text)
                result_text += '}' 
            try:
                output_writer.writerow(json.loads(result_text))
            except json.decoder.JSONDecodeError:
                failed_messages.append(result_text)
        failed_messages_msg = ''
        if failed_messages and args.failed_messages_file:
            for message in failed_messages:
                args.failed_messages_file.write(message + '\n')
            failed_messages_msg = ' {len(failed_messages)} failed messages written to {args.failed_messages_file.name}'
        print(f'DONE{failed_messages_msg}', file=sys.stderr)
    else:
        pprint(batch_info)
