import json

from sqlmodel import Session
from sqlalchemy import select

from message_models import activate_db, Link

def get_bitchute_links(db_path: str) -> list[str]:
    engine = activate_db(db_path)
    links = []
    with Session(engine) as session:
        query = select(Link).where(Link.resolved_link.like("%bitchute.com%"))
        for link in session.scalars(query).all():
            links.append(link.resolved_link)
    return links


if __name__ == '__main__':
    links = get_bitchute_links('messages.db')
    json.dump(links, open('data/bitchute_links.json', 'w'))