#!/usr/bin/env python3

import argparse
import json

from typing import TextIO

from sqlmodel import Session, create_engine, select, and_, func
from message_models import Message

def load_spam_file(spam_message_file: TextIO) -> set[str]:
    spam_messages = set()
    for line in spam_message_file:
        spam_messages.add(json.loads(line)['message'])
    return spam_messages


def count_messages(db_path: str, spam_messages: set[str], year: int, month: int, start_day: int, end_day: int) -> int:
    """Counts messages in the database for a given year, month, and day range, excluding spam messages
    
    Returns:
        message_count: Number of non-spam messages
        total_message_count: Total number of messages
    """

    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        query = select(Message.text).where(and_(Message.year == year, Message.month == month,
                                           Message.day >= start_day, Message.day <= end_day))
        message_count = 0
        total_message_count = len(session.exec(query).all())
        for text in session.exec(query).all():
            if text not in spam_messages:
                message_count += 1
        return (message_count, total_message_count)


def print_output(year: int, month: int, message_count: int, total_message_count: int, output_format: str) -> None:
    if output_format == 'txt':
        print(f'Total messages: {total_message_count}')
        print(f'Non-spam messages: {message_count}')
        print(f"Non-spam %: {message_count / total_message_count * 100:.2f}%")
    elif output_format == 'csv':
        print(f'{year},{month},{total_message_count},{message_count},{message_count / total_message_count * 100:.2f}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_format', choices=['txt', 'csv'], default='txt', help='Output format')
    parser.add_argument('--all_months', action='store_true', help='Process all months')
    parser.add_argument('db_path', help='Path to the database file')
    parser.add_argument('spam_message_file', type=argparse.FileType(), help='File of spammy messages to exclude from analysis')
    parser.add_argument('year', type=int, help='Year of the chat log to select')
    parser.add_argument('month', type=int, help='Month of the chat log to select')
    parser.add_argument('start_day', type=int, help='Start day of the chat log to select')
    parser.add_argument('end_day', type=int, help='End day of the chat log to select')
    args = parser.parse_args()

    spam_messages = load_spam_file(args.spam_message_file)

    if args.output_format == 'csv':
        print('Year,Month,Total messages,Non-spam messages,Non-spam %')
    if args.all_months:
        for year in range(2021, 2025):
            for month in range(1, 13):
                if (year == 2021 and month < 5) or (year == 2024 and month > 5):
                    # our range is from May 2021 to May 2024
                    continue                
                message_count, total_message_count = count_messages(args.db_path, spam_messages, year, month, 10, 17)
                print_output(year, month, message_count, total_message_count, args.output_format)
    else:
        message_count, total_message_count = count_messages(args.db_path, spam_messages, args.year, args.month, args.start_day, args.end_day)
        print_output(args.year, args.month, message_count, total_message_count, args.output_format)


