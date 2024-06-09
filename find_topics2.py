import re
import datetime

from collections import Counter

import spacy

import matplotlib.pyplot as plt
from nltk import ngrams
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA 
from sklearn.cluster import KMeans
from sqlmodel import Session, select, and_

from message_models import Message, activate_db

def query_to_pandas(db_path: str, start_date: str, end_date: str):
    engine = activate_db(db_path)
    start_unixtime = datetime.datetime.strptime(start_date, "%Y-%m-%d").timestamp()
    end_unixtime = datetime.datetime.strptime(end_date, "%Y-%m-%d").timestamp()
    with Session(engine) as session:
        stmt = select(Message).where(
            and_(Message.text is not None,
                 Message.date_unixtime >= start_unixtime, Message.date_unixtime <= end_unixtime))
        df = pd.read_sql_query(stmt, session.connection())
    return df

def clean_text(text):
    text = text.lower()
    text = text.replace("'re", " are")
    text = text.replace("n't", " not")
    text = text.replace("'s", " is")
    text = text.replace("'ve", " have")
    text = re.sub(r'5\s?g', 'fivegee', str(text))
    text = re.sub(r'\d+', '',str(text)) #remove digits and convert to lower case
    text = re.sub('[^A-Za-z0-9\s]', ' ', text) #remove special chracters
    text = text.strip() #Remove leading and trailing white spaces
    return text

if __name__ == "__main__":
    db_path = "messages.db"
    start_date = "2021-05-01"
    end_date = "2021-05-31"
    df = query_to_pandas(db_path, start_date, end_date)

    nlp = spacy.load('en_core_web_lg')

    #Remove Duplicates. Any duplication of text is dropped and one last record maintained
    df = df.drop_duplicates(subset = ['text'], keep = 'last').reset_index(drop = True) 

    cleaned_text = []
    for index,text in enumerate(df['text']):
        #For some reason, text still had leading and trailing spaces even after cleaning. This is to explicitly remove it
        cleanedsentence= ' '.join(text.split()) 
        cleaned_text.append(clean_text(cleanedsentence).replace("\n", "")) #Remove the next line annotation, \n
        # print(index, clean_text(cleanedsentence).replace("\n", ""))
    
    df['cleaned_text'] = cleaned_text

    tfidf_vectorizer = TfidfVectorizer(max_df=0.85, max_features=200, stop_words='english') 
    tfidf_matrix = tfidf_vectorizer.fit_transform(df['text']) 
    print("matrix shape:", tfidf_matrix.shape)


    pca = PCA(n_components=2)
    reduced_tfidf = pca.fit_transform(tfidf_matrix.toarray()) 
    
    #Using the Elbow method to detrmine optimal number of clusters
    wcss = []  # within-cluster sum of squares
    cluster_range = range(1, 10)  # test up to 10 clusters 
    for k in cluster_range:
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(reduced_tfidf)
        wcss.append(kmeans.inertia_)
    
    #Plot to detrmine elbow
    plt.figure(figsize=(10, 6))
    plt.plot(cluster_range, wcss, marker='o', linestyle='--')
    plt.xlabel('Number of Clusters')
    plt.ylabel('Within-Cluster Sum of Squares')
    plt.title('Elbow Method for Optimal Number of Clusters')
    plt.grid(True)
    plt.savefig('elbow.png')
    # plt.show()    

    # Perform KMeans clustering with 4 clusters
    kmeans = KMeans(n_clusters=4, random_state=42)
    clusters = kmeans.fit_predict(reduced_tfidf)
    
    plt.figure(figsize=(10, 6))
    plt.scatter(reduced_tfidf[:, 0], reduced_tfidf[:, 1], c=clusters, cmap='rainbow')
    #plt.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:, 1])
                #s=200, c='black', marker='o', label='Centroids')
    plt.xlabel('X-axis')
    plt.ylabel('Y-axis')
    plt.title('Volume of Telgram messages about Anti-Vaccination')
    plt.legend()
    plt.grid(True)
    plt.savefig('kmeans.png')
    # plt.show()

    df['cluster'] = clusters #Add a column of corresponding cluster

    #Determine the top 10 n-word phrases from each cluster. For each of the clusters, form one string that will be used to determined the top n-word phrases
    merged = pd.DataFrame()
    for cluster in df['cluster'].unique():
        one_string=''
        currentdf=df[df['cluster'] == cluster]['cleaned_text']
        for text in currentdf:
            text=nlp(text)
            for token in text:            
                if token.is_stop == False:
                    one_string=one_string + ' ' + token.lemma_ #For one string from each cluster
        phrases=[]
        for token in ngrams(one_string.split(), 3): #Get 3 word phrases- this can be changed         
            phrases.append(' '.join(token))
        top_phrases=Counter(phrases).most_common(10) #Obtain the top 10
        cluster_top_words=pd.DataFrame(top_phrases, columns=('top_phrases','volume'))
        cluster_top_words['cluster'] = pd.Series([cluster for x in range(len(cluster_top_words.index))]) 
        merged= pd.concat([merged, cluster_top_words])
                
        print(cluster,len(currentdf))

    merged.to_csv('3word.csv', index=False)

    df.to_csv('overall.csv', index=False)
