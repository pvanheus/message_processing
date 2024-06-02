import argparse
import json

import requests

from sqlmodel import Session
from sqlalchemy.engine.base import Engine
from sqlalchemy import select, update
from tqdm import tqdm

from message_models import activate_db, Link

def resolve_links(engine: Engine) -> set[str]:
    unresolveable_links = set()
    with Session(engine) as session:
        unresolved_links = session.exec(select(Link.link).where(Link.resolved_link == None).distinct()).all()
        with requests.Session() as requests_session:
            requests_session.max_redirects = 5
            for link_row in tqdm(unresolved_links):
                link = link_row[0]
                if not link.startswith('http'):
                    link = 'http://' + link
                try:
                    response = requests_session.head(link, timeout=20, allow_redirects=True)
                    if response.status_code == 200:
                        session.exec(update(Link).where(Link.link == link).values(resolved_link=response.url))
                except requests.exceptions.RequestException:
                    unresolveable_links.add(link)
        session.commit()
    return unresolveable_links


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('db_path', help='Path to the database file')
    args = parser.parse_args()

    engine = activate_db(args.db_path)
    unresolveable_links = resolve_links(engine)
    json.dump(list(unresolveable_links), open('unresolveable_links.json', 'w', encoding='utf-8'))
