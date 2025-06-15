#!/usr/bin/env python3

import argparse
import json
import sys
import string
import tempfile

from pprint import pprint

from openai import OpenAI
from sqlmodel import Session
from sqlalchemy import select, and_

from message_models import activate_db, Message
from check_for_spam import load_spam_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip_chatgpt', action='store_true', help='Skip ChatGPT')
    parser.add_argument('--starting_message_num', type=int, default=0)
    parser.add_argument('--batch_size', type=int, default=1000000)
    parser.add_argument('db_path', help='Path to the database file')
    parser.add_argument('system_message_file', type=argparse.FileType(), help='Path to the system message file, used to setup the ChatGPT prompt')
    parser.add_argument('spam_messages_file', type=argparse.FileType(), help='File of spammy messages to exclude from analysis')
    parser.add_argument('year', type=int, help='Year of the chat log to select')
    parser.add_argument('month', type=int, help='Month of the chat log to select')
    parser.add_argument('start_day', type=int, help='Start day of the chat log to select')
    parser.add_argument('end_day', type=int, help='End day of the chat log to select')
    parser.add_argument('chatgpt_output', type=argparse.FileType('w'), nargs='?', default=sys.stdout, help='Path to the output file')
    args = parser.parse_args()

    spammy_messages = set()
    if args.spam_messages_file:
        spammy_messages = load_spam_file(args.spam_messages_file)

    engine = activate_db(args.db_path)
    message_strings = []
    end_message_num = args.starting_message_num + args.batch_size
    with Session(engine) as session:
        query = select(Message).where(and_(Message.year == args.year, Message.month == args.month,
                                           Message.day >= args.start_day, Message.day <= args.end_day))
        messages = session.exec(query).all()  # type: ignore
        count = 0
        for message_row in messages:
            message = message_row[0]
            if message.text in spammy_messages:
                continue
            if len(message.text.split()) > 3:
                count += 1
                if count >= end_message_num:
                    break
                elif count >= args.starting_message_num:
                    message_strings.append(f"{'-'.join([str(e) for e in [message.year, message.month, message.day]])} {message.from_id} ({message.from_name}) ::: {message.text.rstrip()} ::: msg_id{message.id} \n")

    message_count = len(message_strings)
    print('uploading', message_count, 'messages', file=sys.stderr)

    if args.skip_chatgpt:
        sys.exit()

    client = OpenAI()

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

    # this is the non-batched way to use chatGPT
    # response = client.chat.completions.create(
    #         model="gpt-4o-mini-2024-07-18",
    #         temperature=0.1,
    #         response_format={
    #             "type": "json_object"
    #         },
    #         messages=[
    #             {
    #                 "role": "system",
    #                 "content": system_msg
    #             },
    #             {
    #                 "role": "user",
    #                 "content": ' ^^^ '.join(message_strings)
    #             }
    #         ],
    # )
    # print(response.choices[0].message.content)

