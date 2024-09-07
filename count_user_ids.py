#!/usr/env/bin python3

import argparse
import sys

from sqlmodel import Session, create_engine, select, and_, func

from message_models import Message
from check_for_spam import load_spam_file

def count_user_ids(db_path: str, spam_messages: set[str], year: int, month: int, start_day: int, end_day: int) -> tuple[int, set[int]]:
    """Counts messages in the database for a given year, month, and day range, excluding spam messages
    
    Returns:
        message_count: Number of non-spam messages
        total_message_count: Total number of messages
    """

    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        query = select(Message).where(and_(Message.year == year, Message.month == month,
                                           Message.day >= start_day, Message.day <= end_day))
        user_ids = set()
        for message in session.exec(query).all():
            if message.text not in spam_messages:
                user_ids.add(message.from_id)
        return len(user_ids), user_ids

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('db_path', help='Path to the database file')
    parser.add_argument('spam_message_file', type=argparse.FileType(), help='File of spammy messages to exclude from analysis')
    args = parser.parse_args()

    spam_messages = load_spam_file(args.spam_message_file)

    global_user_ids = set()
    print('Year-Month,User_Count')
    for year in range(2021, 2023):
        for month in range(1, 13):
            if (year == 2021 and month < 5) or (year == 2022 and month > 5):
                continue
            user_count, user_ids = count_user_ids(args.db_path, spam_messages, year, month, 10, 17)
            print(f'{year}-{month:02d},{user_count}')
            global_user_ids.update(user_ids)
    print('Unique User Count:', len(global_user_ids), file=sys.stderr)
