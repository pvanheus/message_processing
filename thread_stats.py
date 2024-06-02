import json

from sqlalchemy import select
from sqlmodel import Session

from message_models import activate_db, Message

def gather_threads(db_path: str) -> None:
    engine = activate_db(db_path)
    threads = {}
    with Session(engine) as session:
        messages = session.exec(select(Message.id, Message.reply_to_message_id).where(Message.reply_to_message_id != None))
        for message_row in messages:
            (message_id, reply_to_message_id) = message_row
            if reply_to_message_id not in threads:
                threads[message_id] = reply_to_message_id
            else:
                threads[message_id] = threads[reply_to_message_id]
    for message_id , thread_id in threads.items():
        assert thread_id not in threads, f"found thread with multiple parents {message_id, thread_id}"     

    final_threads = {}
    for message_id, thread_id in threads.items():
        if thread_id not in final_threads:
            final_threads[thread_id] = []
        final_threads[thread_id].append(message_id)

    thread_sizes = {}
    for thread in final_threads.values():
        thread_sizes[len(thread) + 1] = thread_sizes.get(len(thread) + 1, 0) + 1  # minimum size of a thread is 2
    final_thread_sizes = {}
    for size in sorted(thread_sizes.keys()):
        final_thread_sizes[size] = thread_sizes[size]

    json.dump(final_threads, open('data/threads.json', 'w', encoding='utf-8'))
    json.dump(final_thread_sizes, open('data/thread_sizes.json', 'w', encoding='utf-8'))

if __name__ == '__main__':
    gather_threads('messages.db')