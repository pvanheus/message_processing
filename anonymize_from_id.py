#!/usr/bin/env python3

"""Add anonymous IDs to the messages table in the database"""


import argparse

from sqlmodel import Session, create_engine, select, and_

from message_models import Message

def anonymize_from_id(db_path: str) -> None:
    engine = create_engine(f"sqlite:///{db_path}")
    from_id_to_anonymous: dict[str, str] = {}
    id_num = 0
    with Session(engine) as session:
        query = select(Message)
        messages = session.exec(query).all()
        for message in messages:
            if message.from_id not in from_id_to_anonymous:
                id_num += 1
                from_id_to_anonymous[message.from_id] = f'user_{id_num}'
            message.anon_from_id = from_id_to_anonymous[message.from_id]
            session.add(message)
        session.commit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('db_path', help='Path to the database file')
    args = parser.parse_args()

    anonymize_from_id(args.db_path)
