#!/usr/bin/env python3

import argparse
import json
import sys
import string
import tempfile

from pprint import pprint

from openai import OpenAI
from sqlmodel import Session
from sqlalchemy.engine.base import Engine
from sqlalchemy import select, and_

from message_models import activate_db, Message


# system_msg = """
# You are an academic research assistant. Your goal is to identify the themes in a chat log. You will be provided with the raw chat log,
# with messages separated by '^^^'. You should identify the top 10 themes in the chat log, and for each theme, provide a short description,
# rank the themes from most to least important, and show how many messages exemplify each theme. You should also provide no more than three
# messages that exemplify each theme. For the themes, your output should be in JSON format and for each theme look like this:

# {
#     theme: string // a single word theme identifier
#     theme_description: // a short description of the theme
#     theme_rank: int // the importance of the theme
#     message_count: int // the number of messages that exemplify the theme
#     example_messages: string // a list of messages that exemplify the theme
# }

# """

# system_msg = """
# You are an academic research assistant. Your goal is to identify the themes in a chat log. The messages in the chat log
# belong to one of the following themes, where each theme has a one-word identifier:

# 1. antivax: Vaccine Skepticism
# 2. conspiracy: Conspiracy Theories
# 3. misinfo: Misinformation about COVID-19 and vaccines
# 4. antiph: Criticism of public health policies and government responses to the COVID-19 pandemic
# 5. community: Expressions of solidarity and support among group members who share similar views.
# 6. altmed: Alternative treatments for COVID-19
# 7. legal: Concerns regarding the legality and ethics of vaccine mandates and public health measures
# 8. media: Critique of mainstream media coverage and its role in shaping public perception of the pandemic
# 9. experience: Sharing of personal stories and experiences related to COVID-19 and vaccines.
# 10. global: Discussions about the global implications of the pandemic and vaccine rollout.

# Classify each message in the chat log under one of these themes. If a message does not fit any of these themes, you can
# classify it as 'other'. For each message, provide JSON output in the following format:

# {
#     date: string // the date the message was sent
#     user_id: string // the user ID of the message sender
#     message: string // the message text
#     theme: string // the theme that the message belongs to
# }
# """

system_msg = """
You are an academic research assistant. Your goal is to identify the themes in a chat log. The messages in the chat log
belong to one of the following themes, where each theme has a one-word identifier:

1. adv.impacts: claims about adverse impacts resulting from vaccination
2. vaccine.comp: claims about the composition of the COVID-19 vaccine, e.g. pubeworms, graphene, spike protein, microchip, 5G
3. conspiracy: links between COVID-19 vaccines and other conspiracy theories
4. misinfo: claims that scientists are lying, e.g. about COVID-19 numbers, existence of virus, PCR tests, threat of disease
5. access.info: claims about mainstream media misleading or brainwashing people and shutting down debate
6. alt.remedies: mentions of alternative remedies such as essential oils, vitamin c, vitamin d, ivermectin, surmanin and other alternative treatments
7. community: messages for building community and notifying of protests

Classify each message in the chat log under one of these themes. Do not remove duplicates: the total number of messages
classified should be equal to the number of input messages. If a message does not fit any of these themes, you can
classify it as 'other'. For each message, provide JSON output in the following format:

{
    date: string // the date the message was sent
    user_id: string // the user ID of the message sender
    message: string // the message text
    theme: string // the theme that the message belongs to
}
"""


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip_chatgpt', action='store_true', help='Skip ChatGPT')
    parser.add_argument('db_path', help='Path to the database file')
    parser.add_argument('year', type=int, help='Year of the chat log to select')
    parser.add_argument('month', type=int, help='Month of the chat log to select')
    parser.add_argument('start_day', type=int, help='Start day of the chat log to select')
    parser.add_argument('end_day', type=int, help='End day of the chat log to select')
    parser.add_argument('chatgpt_output', type=argparse.FileType('w'), nargs='?', default=sys.stdout, help='Path to the output file')
    args = parser.parse_args()

    engine = activate_db(args.db_path)
    message_strings = []
    with Session(engine) as session:
        query = select(Message).where(and_(Message.year == args.year, Message.month == args.month,
                                           Message.day >= args.start_day, Message.day <= args.end_day))
        messages = session.exec(query).all()
        for message_row in messages:
            message = message_row[0]
            if len(message.text.split()) > 3:
                message_strings.append(f"{'-'.join([str(e) for e in [message.year, message.month, message.day]])} {message.from_id} ({message.from_name}) ::: {message.text.rstrip()} ::: msg_id{message.id} \n")

    message_count = len(message_strings)
    print('uploading', message_count, 'messages')

    if args.skip_chatgpt:
        sys.exit()

    client = OpenAI()

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
            task_file.write(json.dumps(obj).encode() + b'\n')
    
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

