#!/usr/bin/env python3

import argparse
import json

from sqlmodel import Session, create_engine, select, and_, func

from message_models import Message

def find_spammy_messages(db_path: str, min_copies: int = 100) -> list[Message]:
    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        query = (select(Message.text, func.count(Message.text)).
                 where(Message.text != '').
                 group_by(Message.text).having(func.count(Message.text) > min_copies).
                 order_by(func.count(Message.text).desc()))
        spammy_messages = session.exec(query).all()
        return spammy_messages

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--min_copies', type=int, default=100, help='Minimum number of copies for a message to be considered spammy')
    parser.add_argument('db_path', help='Path to the database file')
    parser.add_argument('output_file', type=argparse.FileType('w'), help='File to store spammy message in')
    args = parser.parse_args()

    spammy_messages = find_spammy_messages(args.db_path, args.min_copies)
    for message in spammy_messages:
        record = {'message': message.text, 'count': message.count}
        args.output_file.write(json.dumps(record) + "\n")
