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
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('batch_id')
    parser.add_argument('--failed_messages_file', type=argparse.FileType('w'))
    parser.add_argument('output_file', type=argparse.FileType('w'), nargs='?', default=sys.stdout)
    args = parser.parse_args()

    client = OpenAI()
    batch_info = client.batches.retrieve(args.batch_id)

    failed_message_count = 0
    good_message_count = 0
    many_eol_re = re.compile(r'(\\n *){2,}')
    if args.debug and batch_info.status == 'in_progress':
        if batch_info.input_file_id is not None:
            print('Batch input file ID:', batch_info.input_file_id, file=sys.stderr)
            input_file_response = client.files.content(batch_info.input_file_id).content
            input_text = io.StringIO(input_file_response.decode('utf-8'))
            print('Batch input file:', file=sys.stderr)
            for line in input_text:
                print(line.strip(), file=sys.stderr)
            print('Batch completed successfully', file=sys.stderr)
    if batch_info.status == 'completed':
        if args.debug and batch_info.input_file_id is not None:
            input_file_response = client.files.content(batch_info.input_file_id).content
            input_text = io.StringIO(input_file_response.decode('utf-8'))
            print('Batch input file:', file=sys.stderr)
            for line in input_text:
                print(line.strip(), file=sys.stderr)
            print('Batch completed successfully', file=sys.stderr)
        if batch_info.error_file_id is not None:
            error_file_response = client.files.content(batch_info.error_file_id).content
            error_text = io.StringIO(error_file_response.decode('utf-8'))
            print('Batch completed with errors:', file=sys.stderr)
            for line in error_text:
                print(line.strip(), file=sys.stderr)
            sys.exit(1)
        file_id = batch_info.output_file_id
        assert file_id is not None, 'Batch output file ID is missing'
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
            failed_message = False
            task_id = result['custom_id']
            index = task_id.split('-')[-1]
            result_text = result['response']['body']['choices'][0]['message']['content'].replace("\n", ' ')

            if not result_text.endswith('}'):
                result_text = re.sub(many_eol_re, '', result_text)
                result_text += '}' 
            try:
                output_writer.writerow(json.loads(result_text))
                good_message_count += 1
            except json.decoder.JSONDecodeError:
                # print(f'Error decoding JSON for task {task_id}: {result_text}', file=sys.stderr)
                failed_messages.append(result_text)
                failed_message = True
            except ValueError as e:
                failed_messages.append(result_text)
                failed_message = True
            finally:
                if failed_message:
                    output_writer.writerow({'date': '', 'user_id': '', 'theme': '', 'message': result_text})
        failed_message_count = len(failed_messages)
        failed_messages_msg = ''
        if failed_messages and args.failed_messages_file:
            for message in failed_messages:
                args.failed_messages_file.write(message + '\n')
            failed_messages_msg = f' {len(failed_messages)} failed messages written to {args.failed_messages_file.name}'
        print(f'DONE: {good_message_count}.' + failed_messages_msg, file=sys.stderr)
    else:
        pprint(batch_info)
