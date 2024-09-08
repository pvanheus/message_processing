#!/usr/bin/env python3

import argparse
import sys

from csv import DictReader, DictWriter

from sqlmodel import Session, create_engine, select

from batch_models import Job, StateEnum
from check_for_spam import load_spam_file
from find_user_flows import build_user_id_mapping

def load_messages(db_path: str, user_id_mapping: dict[str, str], spammy_messages: set[str]) -> list[dict[str, str]]:
    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        query = select(Job).where(Job.status == StateEnum.completed).order_by(Job.year, Job.month, Job.start_day)
        jobs = session.exec(query).all()
        messages = []
        for job in jobs:
            results_file = job.results_file
            with open(results_file) as f:
                reader = DictReader(f)
                for row in reader:
                    if row['message'] in spammy_messages:
                        continue
                    if row['user_id'] not in user_id_mapping:
                        # there are a couple of messages with phone numbers instead of IDs - we skip them for analysis
                        continue
                    row['user_id'] = user_id_mapping[row['user_id']]
                    messages.append(row)
    return messages


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('db_path', help='Path to the database file')
    parser.add_argument('messages_db_path', help='Path to the messages database file')
    parser.add_argument('spam_message_file', type=argparse.FileType(), help='File of spammy messages to exclude from analysis')
    parser.add_argument('output_file', type=argparse.FileType('w'), nargs='?', default=sys.stdout, help='File to store messages in')
    args = parser.parse_args()

    user_id_mapping = build_user_id_mapping(args.messages_db_path)
    spammy_messages = load_spam_file(args.spam_message_file)
    messages = load_messages(args.db_path, user_id_mapping, spammy_messages)
    writer = DictWriter(args.output_file, fieldnames=messages[0].keys())
    writer.writeheader()
    writer.writerows(messages)


