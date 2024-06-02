import json

words = json.load(open('data/words.json', 'r'))
from gensim import corpora
dictionary = corpora.Dictionary(words)
corpus = [dictionary.doc2bow(text) for text in words]
import pickle
pickle.dump(corpus, open('corpus.pkl', 'wb'))
dictionary.save('dictionary.gensim')

import gensim
NUM_TOPICS = 10
ldamodel = gensim.models.ldamodel.LdaModel(corpus, num_topics = NUM_TOPICS, id2word=dictionary, passes=15)
ldamodel.save('model5.gensim')
topics = ldamodel.print_topics(num_words=6)
for topic in topics:
    print(topic)