#!/usr/bin/env python3

import argparse
import json
import sys
import tempfile

from pprint import pprint

from openai import OpenAI

from message_models import activate_db, Message
from extract_messages import gather_messages

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--min_words", type=int, default=3, help="Minimum number of words in a message to be included in the output.")
    parser.add_argument("--start_date", type=str, default='2021-05-10', help="Start date for filtering messages (YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, default='2022-05-17', help="End date for filtering messages (YYYY-MM-DD).")
    parser.add_argument("db_path", type=str, help="Path to the SQLite database file.")
    parser.add_argument("system_message_file", type=argparse.FileType(), help="Path to the system message file, used to setup the ChatGPT prompt")
    parser.add_argument("chatgpt_output", type=argparse.FileType('w'), nargs='?', default=sys.stdout, help="Path to the output file for ChatGPT responses")
    args = parser.parse_args()

    filtered_messages = gather_messages(args.db_path, args.start_date, args.end_date, args.min_words)
    message_strings = []
    for message in filtered_messages:
        message_strings.append(f"{'-'.join([str(e) for e in [message.year, message.month, message.day]])} {message.from_id} ({message.from_name}) ::: {message.text.rstrip()} ::: msg_id{message.id} \n")

    system_msg = args.system_message_file.read()
    tasks = []
    for index, message in enumerate(message_strings):
        task = {
            "custom_id": f"task-{index}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                # This is what you would have in your Chat Completions API call
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "response_format": { 
                    "type": "json_object"
                },
                "messages": [
                    {
                        "role": "system",
                        "content": system_msg
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
            }
        }
        tasks.append(task)

    task_filename = ''
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl') as task_file:
        task_filename = task_file.name
        for obj in tasks:
            json_data = json.dumps(obj).encode() + b'\n'
            try:
                json.loads(json_data)
            except json.JSONDecodeError as e:
                print(f'Error loading task object {json_data.decode()}:', e, file=sys.stderr)
                sys.exit(1)
            task_file.write(json_data)
    
    # authentication is done using the API key stored in the environment variable OPENAI_API_KEY
    client = OpenAI()
    batch_file = client.files.create(
        file=open(task_filename, 'rb'),
        purpose='batch'
    )

    batch_job = client.batches.create(
        input_file_id=batch_file.id,
        endpoint='/v1/chat/completions',
        completion_window='24h'
    )

    pprint(batch_job, stream=args.chatgpt_output)
