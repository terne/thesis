# -*- coding: utf-8 -*-
"""cleaned_logisticregression_experiments.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1gAJgMO1qS1fO5T6pgKlh7lghU05B0IGf
"""


import pandas as pd
import tqdm
import numpy as np
import codecs
import glob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.linear_model import LogisticRegression
import random
import matplotlib.pyplot as plt
import sys
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle
sys.path.append('../')
from my_data_utils import load_liar_data, load_kaggle_data, load_FNC_data, load_BS_data

random.seed(16)
np.random.seed(16)

m= 5000 #number of feats 5000 or 10000
k=5#max ngram
v=1 #min mgram

datapath = "/Users/Terne/Documents/KU/Speciale/thesis/data/"

#FAKE=1




def print_scores(y, y_hat, string):
    print(string)
    print("binary F1", f1_score(y, y_hat))
    #print("micro f1:",f1_score(y, y_hat, average='micro'))
    #print("macro f1:", f1_score(y, y_hat, average='macro'))
    #print("weighted F1", f1_score(y, y_hat, average='weighted'))
    print("accuracy", accuracy_score(y, y_hat))
    print()

def liar():
    # we split the LIAR trainset
    # into two parts, LIAR1 and LIAR2, the latter serving
    # as an in-domain dataset to compare with. We also
    # make a randomly relabelled version of the LIAR2
    # set where the class labels are randomly shuffled,
    # denoted LIAR2 random.

    # C=np.inf to avoid regularization.

    liar_train, liar_dev, liar_test, train_lab, dev_lab, test_lab = load_liar_data(datapath)
    X_1, X_2, y_1, y_2 = train_test_split(liar_train, train_lab, test_size=0.50, random_state=42)

    print(len(y_1))
    print(len(y_2))

    split1_vect = TfidfVectorizer(ngram_range=(v,k), max_features=m)
    X_train1 = split1_vect.fit_transform(X_1)
    X_test1 = split1_vect.transform(liar_test)
    feats_1 = ['_'.join(s.split()) for s in split1_vect.get_feature_names()]
    clf_1 = LogisticRegression(random_state=16, solver='saga',C=np.inf, max_iter=10000).fit(X_train1, y_1)
    coefs_1 = clf_1.coef_
    coefs_1_df = pd.DataFrame.from_records(coefs_1, columns=feats_1)
    coefs_1_df.to_csv('liar_train_split1_coefs.csv', sep='\t', index=False)

    split2_vect = TfidfVectorizer(ngram_range=(v,k), max_features=m)
    X_train2 = split2_vect.fit_transform(X_2)
    X_test2 = split2_vect.transform(liar_test)
    feats_2 = ['_'.join(s.split()) for s in split2_vect.get_feature_names()]
    clf_2 = LogisticRegression(random_state=16, solver='saga',C=np.inf, max_iter=10000).fit(X_train2, y_2)
    coefs_2 = clf_2.coef_
    coefs_2_df = pd.DataFrame.from_records(coefs_2, columns=feats_2)
    coefs_2_df.to_csv('liar_train_split2_coefs.csv', sep='\t', index=False)

    split_1_preds = clf_1.predict(X_test1)
    print_scores(test_lab, split_1_preds,"Split 1 Test scores")

    split_2_preds = clf_2.predict(X_test2)
    print_scores(test_lab, split_2_preds,"Split 2 Test scores")

    X = np.concatenate((liar_dev, liar_test))
    y = np.concatenate((dev_lab, test_lab))

    y_rand = y.copy()
    np.random.shuffle(y_rand)

    liar_test_vectorizer = TfidfVectorizer(ngram_range=(v,k), max_features=m)
    liar_rand_test = liar_test_vectorizer.fit_transform(X)
    rand_feats = ['_'.join(s.split()) for s in liar_test_vectorizer.get_feature_names()]
    clf_rand = None
    clf_rand = LogisticRegression(random_state=16, solver='saga',C=np.inf, max_iter=10000).fit(liar_rand_test,y_rand)
    rand_coefs = clf_rand.coef_
    liar_rand_coefs = pd.DataFrame.from_records(rand_coefs, columns=rand_feats)
    liar_rand_coefs.to_csv('liar_testanddev_random_labels.csv', sep='\t', index=False)

def kaggle():
    tr, te, trlab, telab = load_kaggle_data(datapath)

    kaggle_vectorizer = TfidfVectorizer(ngram_range=(v,k), max_features=m)
    X_train_kaggle = kaggle_vectorizer.fit_transform(tr)
    X_test_kaggle = kaggle_vectorizer.transform(te)
    kaggle_feats = ['_'.join(s.split()) for s in kaggle_vectorizer.get_feature_names()]

    clf_kaggle = LogisticRegression(random_state=16, solver='saga',C=np.inf, max_iter=10000).fit(X_train_kaggle,trlab)
    kaggle_coefs = clf_kaggle.coef_
    allcoefs_kaggle = pd.DataFrame.from_records(kaggle_coefs, columns=kaggle_feats) #add ngrams as colnames
    allcoefs_kaggle.to_csv('kaggle_coefs.csv', sep='\t', index=False)

    preds_kaggle_test = clf_kaggle.predict(X_test_kaggle)
    preds_kaggle_tain = clf_kaggle.predict(X_train_kaggle)

    print_scores(telab, preds_kaggle_test, "Kaggle Test Scores")
    print_scores(trlab, preds_kaggle_tain, "Kaggle Train Scores")

def FNC():
    FNC_Xtrain, FNC_Xtest, FNC_ytrain, FNC_ytest = load_FNC_data(datapath)

    FNC_vectorizer = TfidfVectorizer(ngram_range=(v,k), max_features=m)
    FNC_Xtrain_vect = FNC_vectorizer.fit_transform(FNC_Xtrain)
    FNC_Xtest_vect = FNC_vectorizer.transform(FNC_Xtest)
    FNC_feats = ['_'.join(s.split()) for s in FNC_vectorizer.get_feature_names()]

    clf_FNC=None
    clf_FNC = LogisticRegression(random_state=16, solver='saga',C=np.inf, max_iter=10000).fit(FNC_Xtrain_vect, FNC_ytrain)
    FNC_coefs = clf_FNC.coef_
    allcoefs_FNC = pd.DataFrame.from_records(FNC_coefs, columns=FNC_feats)
    allcoefs_FNC.to_csv("FakeNewsCorpus_coefs.csv", sep="\t", index=False)

    preds_FNC_test = clf_FNC.predict(FNC_Xtest_vect)
    preds_FNC_train = clf_FNC.predict(FNC_Xtrain_vect)

    print_scores(FNC_ytest, preds_FNC_test, "FakeNewsCorpus Test Scores")
    print_scores(FNC_ytrain, preds_FNC_train, "FakeNewsCorpus Train Scores")

def BS():
    X_train, X_test, y_train, y_test = load_BS_data(datapath)
    vect = TfidfVectorizer(ngram_range=(v,k), max_features=m)
    X_train_vect = vect.fit_transform(X_train)
    X_test_vect = vect.transform(X_test)
    feats = ['_'.join(s.split()) for s in vect.get_feature_names()]

    clf = None
    clf = LogisticRegression(random_state=16, solver='saga',C=np.inf, max_iter=10000).fit(X_train_vect, y_train)
    coefs = clf.coef_
    allcoefs = pd.DataFrame.from_records(coefs, columns=feats)
    allcoefs.to_csv("BS_coefs.csv", sep="\t", index=False)

    test_preds = clf.predict(X_test_vect)
    train_preds = clf.predict(X_train_vect)
    print_scores(y_test, test_preds, "BS Test Scores")
    print_scores(y_train, train_preds, "BS Train scores")

#liar()

#kaggle()

#FNC()
"""
FakeNewsCorpus Test Scores
binary F1 0.9870882104501026
accuracy 0.987030303030303

FakeNewsCorpus Train Scores
binary F1 0.9999100638546631
accuracy 0.999910447761194

 """

BS()

"""
BS Test Scores
binary F1 0.922234664675874
accuracy 0.9138762574066419

BS Train scores
binary F1 0.9998170620159765
accuracy 0.9997963754836082
"""
