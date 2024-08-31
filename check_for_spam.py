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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('db_path', help='Path to the database file')
    parser.add_argument('spam_message_file', type=argparse.FileType(), help='File of spammy messages to exclude from analysis')
    parser.add_argument('year', type=int, help='Year of the chat log to select')
    parser.add_argument('month', type=int, help='Month of the chat log to select')
    parser.add_argument('start_day', type=int, help='Start day of the chat log to select')
    parser.add_argument('end_day', type=int, help='End day of the chat log to select')
    args = parser.parse_args()

    spam_messages = load_spam_file(args.spam_message_file)

    message_count, total_message_count = count_messages(args.db_path, spam_messages, args.year, args.month, args.start_day, args.end_day)
    print(f'Year: {args.year}, Month: {args.month}, Start Day: {args.start_day}, End Day: {args.end_day}')
    print(f'Total messages: {total_message_count}')
    print(f'Non-spam messages: {message_count}')
    print(f"Non-spam %: {message_count / total_message_count * 100:.2f}%")
