import logging
from gensim.models.word2vec import Word2Vec
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
from nltk import word_tokenize
import dataframe_image as dfi
from time import time
import seaborn as sns
import pandas as pd  
import numpy as np

import nltk
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('stopwords')

plt.style.use('ggplot')

logging.basicConfig(filename='../logs/word2vec.log',  level=logging.INFO)
labels = {2 : "ALL", 1 : "happiness", 0 : "depression"}

def train_word_word2vec(source_sentences, des_path, vector_size=64, window=3, min_count=20):
    
    sents = [word_tokenize(s) for s in source_sentences]
    model = Word2Vec(sentences=sents, vector_size=vector_size, window=window, min_count=min_count, epochs=25)   
    model.save("{}.model".format(des_path))

    t = time()
    model.build_vocab(sents, progress_per=1000)
    logging.info('Time to build vocab: {} mins'.format(round((time() - t) / 60, 2)))
    
    t = time()
    model.train(sents, total_examples=model.corpus_count, epochs=30, report_delay=1)
    logging.info('Time to train the model: {} mins'.format(round((time() - t) / 60, 2)))

    word_vectors = model.wv
    word_vectors.save("{}.wordvectors".format(des_path))   

def save_word2vec_model():
    
    path = '../data/cleaned/data_cleand.json'
    df = pd.read_json(path)

    for label_code, label_name in labels.items(): 
        
        source_sentences = df.copy()
        
        if label_code != 2 : 
            source_sentences = df[df.label == label_code]
        
        source_sentences = source_sentences['selftext_clean'].to_list()
        
        des_path="../models/word2vec/{}.word2vec".format(label_name)
        train_word_word2vec(source_sentences, des_path)
        
        logging.info("save {}.model".format(des_path))

def bias_experimnt(source = "ALL"):
    logging.info('bias experiment')

    model = Word2Vec.load('../models/word2vec/{}.word2vec.model'.format(source))
    
    result = model.wv.most_similar(positive=['woman', 'doctor'], negative=['man'])
    df = pd.DataFrame(result, columns=['word', 'score'])
    dfi.export(df, '../reports/word2vec/bias-man.png')

    result = model.wv.most_similar(positive=['man', 'doctor'], negative=['woman'])
    
    df = pd.DataFrame(result, columns=['word', 'score'])
    dfi.export(df, '../reports/word2vec/bias-woman.png')

    logging.info('bias report can found reports/word2vec/*.png')

def calculate_cosine_similarity(word, model_hap, model_dep):
    logging.info('calculate cosine similarity for '+ word)
    vec_hap = model_hap.wv[word]
    vec_dep = model_dep.wv[word]
    
    cossine_similarity = np.sum(vec_hap*vec_dep)/(np.linalg.norm(vec_hap)*np.linalg.norm(vec_dep))
    
    logging.info('calculate cosine similarity for '+ word + ' = ' + str(cossine_similarity))

    return cossine_similarity

def tsnescatterplot(label, model, word, list_names):
    """ Plot in seaborn the results from the t-SNE dimensionality reduction algorithm of the vectors of a query word,
    its list of most similar words, and a list of words.
    """

    arrays = np.empty((0, 64), dtype='f')
    word_labels = [word]
    color_list  = ['red']

    # adds the vector of the query word
    arrays = np.append(arrays, model.wv.__getitem__([word]), axis=0)
    
    # adds the vector for each of the words from list_names to the array
    for wrd in list_names:
        try:
            wrd_vector = model.wv.__getitem__([wrd])
            word_labels.append(wrd)
            color_list.append('green')
            arrays = np.append(arrays, wrd_vector, axis=0)
        except:
            print([wrd])
        
    # Reduces the dimensionality from 64 to 20 dimensions with PCA
    reduc = PCA(n_components=len(list_names)).fit_transform(arrays)
    
    # Finds t-SNE coordinates for 2 dimensions
    np.set_printoptions(suppress=True)
    
    Y = TSNE(n_components=2, random_state=0, perplexity=15).fit_transform(reduc)
    
    # Sets everything up to plot
    df = pd.DataFrame({'x': [x for x in Y[:, 0]],
                       'y': [y for y in Y[:, 1]],
                       'words': word_labels,
                       'color': color_list})
    
    fig, _ = plt.subplots()
    fig.set_size_inches(9, 9)
    
    # Basic plot
    p1 = sns.regplot(data=df,
                     x="x",
                     y="y",
                     fit_reg=False,
                     marker="o",
                     scatter_kws={'s': 40,
                                  'facecolors': df['color']
                                 }
                    )
    
    # Adds annotations one by one with a loop
    for line in range(0, df.shape[0]):
         p1.text(df["x"][line],
                 df['y'][line],
                 '  ' + df["words"][line].title(),
                 horizontalalignment='left',
                 verticalalignment='bottom', size='medium',
                 color=df['color'][line],
                 weight='normal'
                ).set_size(15)

    
    plt.xlim(Y[:, 0].min()-50, Y[:, 0].max()+50)
    plt.ylim(Y[:, 1].min()-50, Y[:, 1].max()+50)
            
    plt.title('t-SNE visualization for {}'.format(word.title()))
    plt.savefig('../reports/word2vec/{}_{}_most_similar_word.png'.format(label, word))
    plt.cla()
    logging.info('t-SNE visualization for class {} can found reports/word2vec/{}_{}_most_similar_word.png'.format(label, label, word))

def main():

    #step 1. learning
    save_word2vec_model()

    #step 2. find bias
    bias_experimnt()

    #step 3. compare vector
    model_hap = Word2Vec.load('../models/word2vec/happiness.word2vec.model')
    model_dep = Word2Vec.load('../models/word2vec/depression.word2vec.model')
    vector_cossine_similarity_result = {}
    words = ['working', 'time', 'able', 'good', 'depression', 'life', 'believe', 'anxiety', 'human', 'beautiful']
    for word in words:
        vector_cossine_similarity_result[word] = calculate_cosine_similarity(word, model_hap, model_dep)
    
    df = pd.DataFrame(list(vector_cossine_similarity_result.items()), columns=['word', 'cosine similarity value'])
    dfi.export(df, '../reports/word2vec/cosine_similarity.png')
    
    #step 4. find most similar word    
    tsnescatterplot('happiness', model_hap, 'life', [t[0] for t in model_hap.wv.most_similar(positive=["life"], topn=10)])
    tsnescatterplot('depression',model_dep, 'life', [t[0] for t in model_dep.wv.most_similar(positive=["life"], topn=10)])


if __name__ == '__main__':
    main()
