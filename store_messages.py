#!/usr/bin/env python3

# parse Telegram message dump and store in SQLite database
# telegram messages are stored in a JSON file
# keys:
#   'id' - message id
#   'date' - message date
#   'date_unixtime' - message date in unixtime
#   'type' - type of action, can be message or service
#   'from' - username of the sender
#   'from_id' - userid of the sender
#   'reply_to_message_id'
#   'forwarded_from - name of channel message is forwarded from
#   'text' - either a text string or a list of elements. if a list of elements
#   'text_entities' - list of entities in the text
#   'photo' - link to path of photo
#   'file' - can be video, audio file or animation - can also be "(File exceeds maximum size. Change data exporting settings to download.)"
#   'thumbnail' - link to path of thumbnail for video
#   'media_type' - type of media, can be photo, video, audio, or file
#   'mime_type' - mime type of file
#   'duration_seconds' - duration of video or audio file in seconds
#   'width' - width of video or photo
#   'height' - height of video or photo
#
# Text entities can have these keys:
#  'type' can be: bold bot_command cashtag code custom_emoji email hashtag italic link mention mention_name phone plain pre spoiler strikethrough text_link underline
#  'text'
#
# data model
# messages:

import json
import re

from tqdm import tqdm
from sqlmodel import SQLModel, Session, create_engine

from message_models import Message, Link

def store_messages(db_path: str, messages: list[dict]):
    # "mention_name" has a "text" and "user_id"
    # "text_link" has a "text" and "href"
    text_parts = (
        "bold",
        "code",
        "email",
        "hashtag",
        "italic",
        "mention",
        "phone",
        "plain",
        "pre",
        "spoiler",
        "strikethrough",
        "underline",
    )
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    message_count = 0
    # date format = 2021-05-10T18:42:26
    date_re = re.compile(r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})')
    with Session(engine) as session:
        for message in tqdm(messages, unit="msg"):
            message_count += 1
            if message["type"] != "message":
                continue
            # deal with the "from" field - from is a reserved word in Python
            from_name = message["from"]
            del message["from"]
            message_orm = Message(**message)
            message_orm.from_name = from_name
            # we need to overwrite all the inter fields
            for field_name in ("id", "date_unixtime", "reply_to_message_id", "duration_seconds", "width", "height"):
                if field_name in message:
                    setattr(message_orm, field_name, int(message[field_name]))
            text = []
            links = []
            for part in message["text_entities"]:
                part_type = part["type"]

                if part_type == "link":
                    links.append(part["text"])
                elif part_type in text_parts:
                    text.append(part["text"])
                elif part_type == "text_link":
                    text.append(part["text"])
                    links.append(part["href"])
                elif part_type == "mention_name":
                    text.append(part["text"])
                    # there is also a "user_id" but not sure what to do with it right now
            if links:
                for link in links:
                    link_orm = Link(link=link, message_id=message_orm.id)
                    session.add(link_orm)
            message_orm.text = " ".join(text)
            if (
                "file" in message and message["file"]
                == "(File exceeds maximum size. Change data exporting settings to download.)"
            ):
                message_orm.oversize_file = True
                message_orm.file = None
            if message_orm.from_name is None:
                message_orm.from_name = 'Unknown User'
            date_match = date_re.match(message_orm.date)
            if date_match:
                message_orm.year = int(date_match.group('year'))
                message_orm.month = int(date_match.group('month'))
                message_orm.day = int(date_match.group('day'))
            else:
                raise ValueError(f"date {message_orm.date} does not match expected format")
            session.add(message_orm)
        session.commit()


if __name__ == "__main__":
    message_path = "data/result.json"
    print("loading messages")
    with open(message_path) as f:
        data = json.load(f)
    print("storing messages")
    store_messages("messages.db", data['messages'])
    print("messages stored in messages.db")
