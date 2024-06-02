### Message processing code

The SQLite3 model is done using SQLModel, migrations are done using Alemic.

Dependencies:
* SQLModel and SQLAlchemy - used for all the database interactions
* tqdm - used for progress bars
* altair - used for drawing graphs
* requests - used to resolve links
* NLTK and spacy - used for tokenising messages
* gensim - used for LDA / topic clustering

The `message_models.py` contains the Message and Link models and is used by all other code.

`store_messages.py` reads in the JSON dump from Telegram and populates the DB.

`thread_stats.py` computes some statistics on the threads (i.e. chains of replies) in the messages

`resolve_links.py` looks up links and resolves them (using requests) to get a "canonical form" of each link

`visualise.ipynb` has some experiments in visualisation of the data

`extract_words.py` uses NLTK and spacy to turn messages into lists of tokens

`find_topics.py` tries to find topics in the list that `extract_words.py` creates.
