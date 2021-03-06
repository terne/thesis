# -*- coding: utf-8 -*-
"""cleaned_lstm_experiments.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1KQ9m70m2XShoUhFLDgRb0Iw2mn8cR6bt
"""

#!git clone https://terne:Sofus2860@github.com/terne/thesis.git
#from google.colab import drive
#drive.mount('/gdrive')


from keras.preprocessing import sequence
from keras.layers import Embedding, Input, Dense, LSTM, TimeDistributed, Dropout, CuDNNLSTM, Bidirectional
from keras.models import Model, load_model
#from thesis.preprocess_text import preprocess
from keras.utils import multi_gpu_model # for data parallelism
from keras.constraints import NonNeg
from keras import regularizers
from keras.utils import plot_model
from keras.utils.np_utils import to_categorical
from keras.optimizers import Adam

import numpy as np
import codecs
import sys
sys.path.append('../')

from sklearn.model_selection import train_test_split
from sklearn import preprocessing
from sklearn.metrics import f1_score, confusion_matrix, accuracy_score
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle

import pandas as pd
import h5py
import nltk
nltk.download('punkt')
#import matplotlib.pyplot as plt
import datetime
from write_dict_file import d_write
import gensim
#from thesis.get_liar_binary_data import *
import random

from my_data_utils import load_liar_data, tile_reshape, load_kaggle_data, load_FNC_data, load_BS_data

random.seed(42)
np.random.seed(42)

from tensorflow import set_random_seed
set_random_seed(42)

from datetime import datetime

print(datetime.now())



datapath = "/home/ktj250/thesis/data/" #"/Users/Terne/Documents/KU/Speciale/thesis/data/"#"/home/ktj250/thesis/data/"
#directory_path = "/gdrive/My Drive/Thesis/"

TIMEDISTRIBUTED = True

use_pretrained_embeddings = True

FAKE=1

trainingdata = sys.argv[1] #"liar" # kaggle, FNC, BS

print("trainingdata=",trainingdata)

if trainingdata == "liar":
    train, dev, test, train_lab, dev_lab, test_lab = load_liar_data(datapath)
    if not TIMEDISTRIBUTED:
        num_cells = 32
        num_epochs = 100
        r_dropout = 0.4
        dropout = 0.4
        learning_rate = 0.00001
    else:
        num_cells = 64
        num_epochs = 5
        r_dropout = 0.6
        dropout = 0.8
        learning_rate = 0.001

elif trainingdata == "kaggle":
    train, test, train_lab, test_lab = load_kaggle_data(datapath)
    if not TIMEDISTRIBUTED:
        num_cells = 64
        num_epochs = 10
        r_dropout = 0.2
        dropout = 0.6
        learning_rate = 0.001
    else:
        num_cells = 128
        num_epochs = 11
        r_dropout = 0.4
        dropout = 0.6
        learning_rate = 0.001

elif trainingdata == "FNC":
    train, test, train_lab, test_lab = load_FNC_data(datapath)
    if not TIMEDISTRIBUTED:
        pass
    else:
        num_cells = 64
        num_epochs = 5
        r_dropout = 0.2
        dropout = 0.6
        learning_rate = 0.001

elif trainingdata == "BS":
    train, test, train_lab, test_lab = load_BS_data(datapath)
    if not TIMEDISTRIBUTED:
        num_cells = 256
        num_epochs = 10
        r_dropout = 0.4
        dropout = 0.2
        learning_rate = 0.0001
    else:
        num_cells = 256
        num_epochs = 10
        r_dropout = 0.4
        dropout = 0.2
        learning_rate = 0.0001




train = [nltk.word_tokenize(i.lower()) for i in train]

test = [nltk.word_tokenize(i.lower()) for i in test]

if trainingdata == "liar":
    dev = [nltk.word_tokenize(i.lower()) for i in dev]
else:
    dev = train[int(abs((len(train_lab)/3)*2)):]
    dev_lab = train_lab[int(abs((len(train_lab)/3)*2)):]
    train = train[:int(abs((len(train_lab)/3)*2))]
    train_lab = train_lab[:int(abs((len(train_lab)/3)*2))]
    print(len(train), len(dev))

all_train_tokens = []
for i in train:
    for word in i:
        all_train_tokens.append(word)

vocab = set(all_train_tokens)
word2id = {word: i+1 for i, word in enumerate(vocab)}# making the first id is 1, so that I can pad with zeroes.
word2id["UNK"] = len(word2id)+1
id2word = {v: k for k, v in word2id.items()}


#trainTextsSeq: List of input sequence for each document (A matrix with size num_samples * max_doc_length)
trainTextsSeq = np.array([[word2id[w] for w in sent] for sent in train])

testTextsSeq = np.array([[word2id.get(w, word2id["UNK"]) for w in sent] for sent in test])

#if trainingdata == "liar":
devTextsSeq = np.array([[word2id.get(w, word2id["UNK"]) for w in sent] for sent in dev])




# PARAMETERS
# vocab_size: number of tokens in vocabulary
vocab_size = len(word2id)+1
# max_doc_length: length of documents after padding (in Keras, the length of documents are usually padded to be of the same size)
max_doc_length = 100 # LIAR 100 (like Wang), Kaggle 3391, FakeNewsCorpus 2669
# num_samples: number of training/testing data samples
num_samples = len(train_lab)
# num_time_steps: number of time steps in LSTM cells, usually equals to the size of input, i.e., max_doc_length
num_time_steps = max_doc_length
embedding_size = 300 # also just for now..
num_batch = 64



# PREPARING DATA

# padding with max doc lentgh
seq = sequence.pad_sequences(trainTextsSeq, maxlen=max_doc_length, dtype='int32', padding='post', truncating='post', value=0.0)
print("train seq shape",seq.shape)
test_seq = sequence.pad_sequences(testTextsSeq, maxlen=max_doc_length, dtype='int32', padding='post', truncating='post', value=0.0)
#if trainingdata == "liar":
dev_seq = sequence.pad_sequences(devTextsSeq, maxlen=max_doc_length, dtype='int32', padding='post', truncating='post', value=0.0)


if TIMEDISTRIBUTED:
    train_lab = tile_reshape(train_lab, num_time_steps)
    test_lab = tile_reshape(test_lab, num_time_steps)
    print(train_lab.shape)
    #if trainingdata == "liar":
    dev_lab = tile_reshape(dev_lab, num_time_steps)
else:
    train_lab = to_categorical(train_lab, 2)
    test_lab = to_categorical(test_lab, 2)
    print(train_lab.shape)
    #if trainingdata == "liar":
    dev_lab = to_categorical(dev_lab, 2)

print("Parameters:: num_cells: "+str(num_cells)+" num_samples: "+str(num_samples)+" embedding_size: "+str(embedding_size)+" epochs: "+str(num_epochs)+" batch_size: "+str(num_batch))


if use_pretrained_embeddings:
    # https://blog.keras.io/using-pre-trained-word-embeddings-in-a-keras-model.html
    # Load Google's pre-trained Word2Vec model.
    # /home/ktj250/thesis/
    model = gensim.models.KeyedVectors.load_word2vec_format('/home/ktj250/thesis/GoogleNews-vectors-negative300.bin', binary=True)

    embedding_matrix = np.zeros((len(word2id) + 1, 300))
    for word, i in word2id.items():
        try:
            embedding_vector = model.wv[word]
        except:
            embedding_vector = model.wv["UNK"]
        if embedding_vector is not None:
            embedding_matrix[i] = embedding_vector

myInput = Input(shape=(max_doc_length,), name='input')
print(myInput.shape)
if use_pretrained_embeddings:
    x = Embedding(input_dim=vocab_size, output_dim=embedding_size, weights=[embedding_matrix],input_length=max_doc_length,trainable=True)(myInput)
else:
    x = Embedding(input_dim=vocab_size, output_dim=embedding_size, input_length=max_doc_length)(myInput)
    print(x.shape)

if TIMEDISTRIBUTED:
    lstm_out = LSTM(num_cells, dropout=dropout, recurrent_dropout=r_dropout, return_sequences=True, kernel_constraint=NonNeg())(x)
    predictions = TimeDistributed(Dense(1, activation='sigmoid', kernel_constraint=NonNeg()))(lstm_out)
else:
    lstm_out = Bidirectional(LSTM(num_cells, dropout=dropout, recurrent_dropout=r_dropout))(x)
    predictions = Dense(2, activation='softmax')(lstm_out)

model = Model(inputs=myInput, outputs=predictions)


# try-except to switch between gpu and cpu version when not working in google colab
#try:
#    parallel_model = multi_gpu_model(model, gpus=2)
#    parallel_model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
#    print("fitting model..")
#    parallel_model.fit({'input': seq}, y_train_tiled, epochs=num_epochs, verbose=2, batch_size=num_batch, validation_split=.20)
#    print("Testing...")
#    score = parallel_model.evaluate(test_seq, y_test_tiled, batch_size=num_batch, verbose=0)
#    print("Test loss:", score[0])
#    print("Test accuracy:", score[1])
    # get predicted classes
#    train_preds = model.predict(seq)
#    test_preds = model.predict(test_seq)
#except:

opt = Adam(lr=learning_rate)

if TIMEDISTRIBUTED:
    model.compile(optimizer=opt, loss='binary_crossentropy', metrics=['accuracy'])
else:
    model.compile(optimizer=opt, loss='categorical_crossentropy', metrics=['accuracy'])
print("fitting model..")
#if trainingdata == "liar":
model.fit({'input': seq}, train_lab, epochs=num_epochs, verbose=2, batch_size=num_batch, validation_data=(dev_seq,dev_lab))
#else:
    #model.fit({'input': seq}, train_lab, epochs=num_epochs, verbose=2, batch_size=num_batch)
print("Testing...")
test_score = model.evaluate(test_seq, test_lab, batch_size=num_batch, verbose=0)
#if trainingdata == "liar":
dev_score = model.evaluate(dev_seq, dev_lab, batch_size=num_batch, verbose=0)

print("Test loss:", test_score[0])
print("Test accuracy:", test_score[1])
#if trainingdata == "liar":
print("Valid loss:", dev_score[0])
print("Valid accuracy:", dev_score[1])

if not TIMEDISTRIBUTED:
    preds = model.predict(test_seq)
    f1 = f1_score(np.argmax(test_lab,axis=1), np.argmax(preds, axis=1))
    tn, fp, fn, tp = confusion_matrix(np.argmax(test_lab,axis=1), np.argmax(preds, axis=1)).ravel()
    print("tn, fp, fn, tp")
    print(tn, fp, fn, tp)


model.summary()



if TIMEDISTRIBUTED:
    model_path = trainingdata+'lstmvis_model'
else:
    model_path = trainingdata+'biLSTM_model'

model.save(model_path+'.h5')

d_write(trainingdata+"words.dict", word2id)
d_write(trainingdata+"words.dict", {"PADDING": 0})




#plot_model(model, to_file=trainingdata+model_path+".png") # error here

if TIMEDISTRIBUTED:
    #model = load_model(directory_path+model_path)
    # Getting all the files

    # text files
    trainTextsSeq_flatten = np.array(seq).flatten()
    hf = h5py.File(trainingdata+"train.hdf5", "w") # need this file for LSTMVis
    hf.create_dataset('words', data=trainTextsSeq_flatten)
    hf.close()

    testTextsSeq_flatten = np.array(test_seq).flatten()
    hf_t = h5py.File(trainingdata+"test.hdf5", "w") # need this file for LSTMVis
    hf_t.create_dataset('words', data=testTextsSeq_flatten)
    hf_t.close()



    # predictions

    # get predicted classes
    train_preds = model.predict(seq)
    test_preds = model.predict(test_seq)

    # if multiclass:
    #y_classes_train = train_preds.argmax(axis=-1)
    #y_classes_test = test_preds.argmax(axis=-1)
    # if binary:
    #y_classes = (y_prob > 0.5).astype(np.int)
    y_classes_train = (train_preds > 0.5).astype(np.int)
    y_classes_test = (test_preds > 0.5).astype(np.int)

    # save predicted classes!
    predicted_train_classes_flatten = np.array(y_classes_train).flatten()
    hf_p = h5py.File(trainingdata+"predictions.hdf5", "w")
    hf_p.create_dataset('preds_train', data=predicted_train_classes_flatten)
    #hf_p.close()
    predicted_test_classes_flatten = np.array(y_classes_test).flatten()
    hf_p.create_dataset('preds_test', data=predicted_test_classes_flatten)
    #hf_pt = h5py.File("test_predictions.hdf5", "w")
    #hf_pt.create_dataset('preds', data=predicted_test_classes_flatten)
    test_true_classes = np.array(test_lab).flatten()
    hf_p.create_dataset('true_classes_testset', data=test_true_classes)
    train_true_classes = np.array(test_lab).flatten()
    hf_p.create_dataset('true_classes_trainset', data=train_true_classes)
    hf_p.close()

    # dictionary
    #d_write("words.dict", word2id)
    #d_write("words.dict", {"PADDING": 0}) # add padding token to lstmvis dict

    # states
    model.layers.pop();
    inp = model.inputs
    out = model.layers[-1].output
    model_RetreiveStates = Model(inp, out)

    states_model = model_RetreiveStates.predict(seq, batch_size=num_batch)
    states_model_flatten = states_model.reshape(num_samples * num_time_steps, num_cells)# Flatten first and second dimension for LSTMVis
    hf = h5py.File(trainingdata+"states.hdf5", "w")
    hf.create_dataset('states_train', data=states_model_flatten)
    #hf.close()

    # solved
    states_model_test = model_RetreiveStates.predict(test_seq, batch_size=num_batch)
    states_model_test_flatten = states_model_test.reshape(len(test_seq) * num_time_steps, num_cells)# Flatten first and second dimension for LSTMVis
    hf.create_dataset('states_test', data=states_model_test_flatten)
    hf.close()

"""Testing"""

def test_on_kaggle():
    print("Testing on kaggle")
    train, test, train_lab, test_lab = load_kaggle_data(datapath)
    model_loaded = load_model(model_path+'.h5')
    commons_testing(model_loaded, test, test_lab, trainingdata+"_kaggle")


def test_on_FNC():
    print("Testing on FNC")
    train, test, train_lab, test_lab = load_FNC_data(datapath)
    model_loaded2 = load_model(model_path+'.h5')
    commons_testing(model_loaded2, test, test_lab, trainingdata+"_FNC")

def test_on_BS():
    print("Testing on BS")
    train, test, train_lab, test_lab = load_BS_data(datapath)
    model_loaded3 = load_model(model_path+'.h5')
    commons_testing(model_loaded3, test, test_lab, trainingdata+"_BS")

def test_on_liar():
    print("Testing on Liar")
    train, dev, test, train_lab, dev_lab, test_lab = load_liar_data(datapath)
    model_loaded4 = load_model(model_path+'.h5')
    commons_testing(model_loaded4, test, test_lab, trainingdata+"_Liar test set")
    #commons_testing(model_loaded4, dev, dev_lab, trainingdata+"_Liar dev set")


def test_on_learnerdata():
    prof_test = codecs.open(datapath+"proficiency/fce_text_entire_docs.txt", "r", "utf-8").read().split("\n")
    prof_test = prof_test[:len(prof_test)-1]
    test = [nltk.word_tokenize(i.lower()) for i in prof_test]
    test_lab = codecs.open(datapath+"proficiency/proficiency_entire_docs.txt", "r", "utf-8").read().split("\r\n")
    test_lab = test_lab[:len(test_lab)-1]
    #pr = []
    #ID = []
    #for i in test_lab:
    #    s = i.split("\t")
        #print(s[0])
    #    pr.append(int(np.float(s[0])))
    #    ID.append(s[1])
    #np.savetxt("IDs_entire_docs", ID)
    #np.savetxt("prof_score_entire_docs", pr)
    testTextsSeq = np.array([[word2id.get(w, word2id["UNK"]) for w in sent] for sent in test])
    test_seq = sequence.pad_sequences(testTextsSeq, maxlen=max_doc_length, dtype='int32', padding='post', truncating='post', value=0.0)
    model_loaded3 = load_model(model_path+'.h5')
    if TIMEDISTRIBUTED:
        test_preds = model_loaded3.predict(test_seq)
        retrieve_lstmvis_files(model_loaded3, test_seq, test_lab, test_preds, trainingdata+"_FCE")
    else:
        test_preds = model.predict(test_seq)
        print(len(test_preds))
        np.savetxt("student_preds_softmax_entire_docs.txt",test_preds)

def test_on_TP():

    pass

def commons_testing(model_loaded, test, test_lab, identifier_string):
    test = [nltk.word_tokenize(i.lower()) for i in test]
    testTextsSeq = np.array([[word2id.get(w, word2id["UNK"]) for w in sent] for sent in test])
    test_seq = sequence.pad_sequences(testTextsSeq, maxlen=max_doc_length, dtype='int32', padding='post', truncating='post', value=0.0)
    if TIMEDISTRIBUTED:
        test_lab = tile_reshape(test_lab, num_time_steps)
    else:
        test_lab = to_categorical(test_lab, 2)
        preds = model.predict(test_seq)
        prediction = pd.DataFrame(list(zip(np.argmax(test_lab,axis=1), np.argmax(preds, axis=1), [" ".join(i[:100]) for i in test])), columns=['label','prediction','text']).to_csv(identifier_string+'_prediction.csv')

        accuracy = accuracy_score(np.argmax(test_lab,axis=1), np.argmax(preds, axis=1))
        print("accuracy:", accuracy)
        f1 = f1_score(np.argmax(test_lab,axis=1), np.argmax(preds, axis=1))
        print("F1=", f1)
        tn, fp, fn, tp = confusion_matrix(np.argmax(test_lab,axis=1), np.argmax(preds, axis=1)).ravel()
        print("tn, fp, fn, tp")
        print(tn, fp, fn, tp)
    test_score = model_loaded.evaluate(test_seq, test_lab, batch_size=num_batch, verbose=0)
    print("Test loss:", test_score[0])
    print("Test accuracy:", test_score[1])
    if TIMEDISTRIBUTED:
        test_preds = model_loaded.predict(test_seq)
        retrieve_lstmvis_files(model_loaded, test_seq, test_lab, test_preds, identifier_string)


def retrieve_lstmvis_files(model_loaded, test_seq, test_lab, test_preds,identifier_string):
    testTextsSeq_flatten = np.array(test_seq).flatten()
    hf_t = h5py.File(identifier_string+"_"+"test.hdf5", "w")
    hf_t.create_dataset('words', data=testTextsSeq_flatten)
    hf_t.close()
    #test_preds = model.predict(test_seq)
    y_classes_test = (test_preds > 0.5).astype(np.int)
    hf_p = h5py.File(identifier_string+"_"+"predictions.hdf5", "w")
    predicted_test_classes_flatten = np.array(y_classes_test).flatten()
    hf_p.create_dataset('preds_test', data=predicted_test_classes_flatten)
    #hf_pt = h5py.File("test_predictions.hdf5", "w")
    #hf_pt.create_dataset('preds', data=predicted_test_classes_flatten)
    test_true_classes = np.array(test_lab).flatten()
    hf_p.create_dataset('true_classes_testset', data=test_true_classes)
    hf_p.close()
    # states
    model_loaded.layers.pop();
    inp = model_loaded.inputs
    out = model_loaded.layers[-1].output
    model_RetreiveStates = Model(inp, out)
    states_model_test = model_RetreiveStates.predict(test_seq, batch_size=num_batch)
    states_model_test_flatten = states_model_test.reshape(len(test_seq) * num_time_steps, num_cells)# Flatten first and second dimension for LSTMVis
    hf = h5py.File(identifier_string+"_"+"states.hdf5", "w")
    hf.create_dataset('states_test', data=states_model_test_flatten)
    hf.close()


test_on_kaggle()

test_on_FNC()

test_on_BS()

test_on_liar()

test_on_learnerdata()
