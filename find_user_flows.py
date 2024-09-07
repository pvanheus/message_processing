#!/usr/bin/env python3

import argparse

from csv import DictReader

from sqlmodel import Session, create_engine, select, func

from batch_models import Job, StateEnum
from message_models import Message

def message_key(date_str: str) -> str:
    (year, month, day) = [int(element) for element in date_str.split('-')]
    return year * 10000 + month * 100 + day

def build_user_id_mapping(message_db_path: str) -> dict[str, str]:
    engine = create_engine(f"sqlite:///{message_db_path}")
    with Session(engine) as session:
        query = select(Message.from_id, Message.anon_from_id).distinct()
        id_pairs = session.exec(query).all()
    return dict(id_pairs)


def read_job_outputs(db_path: str, user_id_lookup: dict[str, str]) -> list[dict[str, str]]:
    engine = create_engine(f"sqlite:///{db_path}")
    new_id_num = 0
    messages: list[dict[str, str]] = []
    with Session(engine) as session:
        query = select(Job).where(Job.status == StateEnum.completed)
        jobs = session.exec(query).all()
        for job in jobs:
            results_file = job.results_file
            with open(results_file) as f:
                reader = DictReader(f)
                for row in reader:
                    if row['user_id'] not in user_id_lookup:
                        new_id_num += 1
                        user_id_lookup[row['user_id']] = f'new_user_{new_id_num}'
                    row['user_id'] = user_id_lookup[row['user_id']]
                    messages.append(row)
    return messages


def filter_messages(messages: list[dict[str, str]], start_date: str, end_date: str) -> list[dict[str, str]]:
    start_key = message_key(start_date)
    end_key = message_key(end_date)
    return [message for message in messages if start_key <= message_key(message['date']) <= end_key]


def find_top_users(messages: list[dict[str, str]], top_n: int) -> list[dict[str, str]]:
    user_counts: dict[str, int] = {}
    for message in messages:
        user_id = message['user_id']
        count = user_counts.get(user_id, 0)
        user_counts[user_id] = count + 1
    top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [{'user_id': user, 'count': count} for user, count in top_users]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('db_path', help='Path to the database file')
    parser.add_argument('messages_db_path', help='Path to the messages database file')
    parser.add_argument('top_users_output_file', type=argparse.FileType('w'), help='File to store top users in')
    parser.add_argument('messages_per_month_output_file', type=argparse.FileType('w'), help='File to store messages per month in')
    args = parser.parse_args()

    user_id_lookup = build_user_id_mapping(args.messages_db_path)
    messages = sorted(read_job_outputs(args.db_path, user_id_lookup), key=lambda x: message_key(x['date']))
    
    args.top_users_output_file.write('year-month,user_id,count\n')
    args.messages_per_month_output_file.write('year-month,message_count,top_user_percentage\n')
    top_user_occurance_count: dict[str, int] = {}
    for year in range(2021, 2023):
        for month in range(1, 13):
            if (year == 2021 and month < 5) or (year == 2022 and month > 5):
                continue
            start_date = f'{year}-{month:02d}-10'
            end_date = f'{year}-{month:02d}-17'
            month_messages = filter_messages(messages, start_date, end_date)
            month_message_count = len(month_messages)
            top_users = find_top_users(month_messages, 5)
            for user_id in top_users:
                top_user_occurance_count[user_id['user_id']] = top_user_occurance_count.get(user_id['user_id'], 0) + 1
            top_user_percent = sum(user['count'] for user in top_users) / month_message_count * 100
            print(f'{year}-{month:02d} {top_user_percent:.2f} {[(user["user_id"], user["count"]) for user in top_users]}')
            for user in top_users:
                args.top_users_output_file.write(f'{year}-{month:02d},{user["user_id"]},{user["count"]}\n')
            args.messages_per_month_output_file.write(f'{year}-{month:02d},{month_message_count},{top_user_percent:.2f}\n')

    top_recurring_users = sorted(top_user_occurance_count.items(), key=lambda x: x[1], reverse=True)
    print(top_recurring_users)

    for user_id, count in top_recurring_users[:5]:
        themes: dict[str, str] = {}
        for message in messages:
            if message['user_id'] == user_id:
                themes[message['theme']] = themes.get(message['theme'], 0) + 1
        print(user_id, count, sorted(themes.items(), key=lambda x: x[1], reverse=True)[:5])