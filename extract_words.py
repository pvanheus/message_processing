import json
import random

from datetime import date
from time import mktime

import nltk
import spacy

from nltk.corpus import wordnet as wn
from nltk.stem.wordnet import WordNetLemmatizer
from spacy.lang.en import English
from sqlalchemy import select
from sqlmodel import Session
from tqdm import tqdm

from message_models import activate_db, Message

spacy.load('en_core_web_sm')
nltk.download('punkt')
nltk.download('words')
nltk.download('wordnet')
nltk.download('stopwords')


def find_messages(db_path: str, start_date: str, end_date: str) -> list[Message]:
    engine = activate_db(db_path)
    messages = []
    start_unixtime = mktime(date.fromisoformat(start_date).timetuple())
    end_unixtime = mktime(date.fromisoformat(end_date).timetuple())
    with Session(engine) as session:
        message_rows = session.exec(select(Message).where(Message.date_unixtime >= start_unixtime,
                                                          Message.date_unixtime <= end_unixtime)).all()
        for message_row in message_rows:
            messages.append(message_row[0])
    return messages


def tokenize_text(text: str) -> list[str]:
    parser = English()
    tokens = parser(text)
    lda_tokens = []
    for token in tokens:
        if not token.orth_.isalnum():
            continue
        elif token.like_url:
            lda_tokens.append('URL')
        elif token.orth_.startswith('@'):
            lda_tokens.append('SCREEN_NAME')
        else:
            lda_tokens.append(token.lower_)
    return lda_tokens


def prepare_text(messages: list[Message]) -> list[str]:
    lemmatizer = WordNetLemmatizer()
    en_stop = set(nltk.corpus.stopwords.words('english'))
    output_words = []
    for message in tqdm(messages):
        tokens = [token for token in tokenize_text(message.text) if token not in en_stop]
        lemmatized_words = [lemmatizer.lemmatize(token) for token in tokens]
        output_words.append(lemmatized_words)
    return output_words

def prepare_text2(messages: list[Message],
                  min_message_length: int = 4,
                  min_english_fraction: float = 0.4) -> list[str]:
    en_words = set(nltk.corpus.words.words())
    en_stop = set(nltk.corpus.stopwords.words('english'))
    lemmatizer = WordNetLemmatizer()
    output_words = []
    num_messages = skipped_messages = 0
    for message in tqdm(messages):
        num_messages += 1
        tokens = [word.lower() for word in nltk.tokenize.word_tokenize(message.text, language='english')]
        words = [lemmatizer.lemmatize(token) for token in tokens if token.isalnum]
        if len(words) < min_message_length:
            skipped_messages += 1
            continue
        english_words = [word for word in words if (word in en_words)]
        english_fraction = len(english_words) / len(words)
        if english_fraction < min_english_fraction or len(english_words) < min_message_length:
            skipped_messages += 1
            continue
        non_stop_words = [word for word in english_words if word not in en_stop]
        # print(english_fraction, non_stop_words)
        output_words.append(non_stop_words)
    print(f"Skipped {skipped_messages} out of {num_messages} messages. total words {len(output_words)}")
    return output_words


if __name__ == '__main__':
    messages = find_messages('messages.db', '2021-06-01', '2021-08-30')
    words = prepare_text2(messages)
    json.dump(words, open("data/words.json", 'w', encoding='utf-8'))
    # for word in words:
    #     if random.random() > 0.99:
    #         print(word)

