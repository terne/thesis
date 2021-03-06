import numpy as np
import codecs
from sklearn.model_selection import train_test_split
from keras.layers import Input, Dense, Embedding, LSTM, Flatten, TimeDistributed
from keras.models import Model
from keras.preprocessing import sequence
import nltk
from preprocess_text import preprocess
#import matplotlib.pyplot as plt
#from keras.utils import plot_model
#from keras.utils import to_categorical
#from keras.metrics import categorical_accuracy
import h5py


data = codecs.open("data/kaggle_trainset.txt", 'r', 'utf-8').read().split('\n')
data = data[:200]
#data = data[:200]
data = [s.lower() for s in data]
labels = codecs.open("data/kaggle_train_labels.txt", 'r', 'utf-8').read().split('\n')
labels = labels[:200]
#labels = labels[:200]
labels = [int(i) for i in labels]

# disregarding input which is less than 100 characters (as they do not contain many words, if any)
labels_include = []
data_include = []
for indel, i in enumerate(data):
    if len(i) > 100:
        data_include.append(i)
        labels_include.append(labels[indel])

train, dev, train_lab, dev_lab = train_test_split(data, labels, test_size=0.33, random_state=42)
train = preprocess(train)
dev = preprocess(dev)
#train = [nltk.word_tokenize(i.lower()) for i in train]
#dev = [nltk.word_tokenize(i.lower()) for i in dev]

all_train_tokens = []
for i in train:
    for word in i:
        all_train_tokens.append(word)
vocab = set(all_train_tokens)
word2id = {word: i+1 for i, word in enumerate(vocab)}# making the first id is 1, so that I can pad with zeroes.
word2id["UNK"] = len(word2id)+1
id2word = {v: k for k, v in word2id.items()}
#[[id2word.get(word, "UNK") for word in sent] for sent in dev]
# save Dict file containing the mapping from word ID to word (e.g. train.dict)
f = open("dict.txt","w+")
f.write( str(id2word) )
f.close()

#trainTextsSeq: List of input sequence for each document (A matrix with size num_samples * max_doc_length)
trainTextsSeq = np.array([[word2id[w] for w in sent] for sent in train])
testTextsSeq = np.array([[word2id.get(w, word2id["UNK"]) for w in sent] for sent in dev])

# PARAMETERS
# vocab_size: number of tokens in vocabulary
vocab_size = len(word2id)+1
# max_doc_length: length of documents after padding (in Keras, the length of documents are usually padded to be of the same size)
max_doc_length = 320 # using the mean length of documents as max_doc_length for now
# num_cells: number of LSTM cells
num_cells = 50 # for now, probably test best parameter through cross-validation
# num_samples: number of training/testing data samples
num_samples = len(train_lab)
# num_time_steps: number of time steps in LSTM cells, usually equals to the size of input, i.e., max_doc_length
num_time_steps = max_doc_length
embedding_size = 50 # also just for now..
num_epochs = 5
num_batch = 32 # also find optimal through cross-validation


# PREPARING DATA

# padding with max doc lentgh
seq = sequence.pad_sequences(trainTextsSeq, maxlen=max_doc_length, dtype='int32', padding='post', truncating='post', value=0.0)
print("train seq shape",seq.shape)
test_seq = sequence.pad_sequences(testTextsSeq, maxlen=max_doc_length, dtype='int32', padding='post', truncating='post', value=0.0)


trainTextsSeq_flatten = np.array(seq).flatten()
hf = h5py.File("train.hdf5", "w") # need this file for LSTMVis
hf.create_dataset('words', data=trainTextsSeq_flatten)
hf.close()


# Reshape y_train:
def tile_reshape(train_lab, num_time_steps):
    y_train_tiled = np.tile(train_lab, (num_time_steps,1)).T
    y_train_tiled = y_train_tiled.reshape(len(train_lab), num_time_steps , 1)
    print("y_train_shape:",y_train_tiled.shape)
    return y_train_tiled

y_train_tiled = tile_reshape(train_lab, num_time_steps)
y_test_tiled = tile_reshape(dev_lab, num_time_steps)
print("Parameters:: num_cells: "+str(num_cells)+" num_samples: "+str(num_samples)+" embedding_size: "+str(embedding_size)+" epochs: "+str(num_epochs)+" batch_size: "+str(num_batch))
#print(y_train_tiled)


myInput = Input(shape=(max_doc_length,), name='input')
print(myInput.shape)
x = Embedding(input_dim=vocab_size, output_dim=embedding_size, input_length=max_doc_length)(myInput)
print(x.shape)
lstm_out = LSTM(num_cells, return_sequences=True)(x)
print(lstm_out.shape)
#predictions = TimeDistributed(Dense(2, activation='softmax'))(lstm_out)
predictions = TimeDistributed(Dense(1, activation='sigmoid'))(lstm_out) # changing the number of units in Dense from 2 to 1 made it run but it couldnt learn because for softmax the output can't be one.
#predictions = TimeDistributed(Dense(1))(lstm_out) # try this instead?
print("predictions_shape:",predictions.shape)
model = Model(inputs=myInput, outputs=predictions)
model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
#model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
print("fitting model..")
model.fit({'input': seq}, y_train_tiled, epochs=num_epochs, verbose=2, batch_size=num_batch, validation_split=.20)
#parallel_model.fit(seq, y_train_tiled, epochs=num_epochs, verbose=2, steps_per_epoch=(np.int(np.floor(num_samples/num_batch))), validation_split=.20) # or try this, removing the curly brackets.
#parallel_model.fit({'input': seq}, train_lab, epochs=num_epochs, batch_size=num_batch, verbose=1)



model.summary()
score = model.evaluate(test_seq, y_test_tiled, batch_size=num_batch)
print("Test loss:", score[0])
print("Test accuracy:", score[1])

# Save the states via predict
model.layers.pop();
#model.summary()
#inp = model.get_input_at(0)
inp = model.inputs
out = model.layers[-1].output
model_RetreiveStates = Model(inp, out)
states_model = model_RetreiveStates.predict(seq, batch_size=num_batch)

# Flatten first and second dimension for LSTMVis
states_model_flatten = states_model.reshape(num_samples * num_time_steps, num_cells)

hf = h5py.File("states.hdf5", "w")
hf.create_dataset('states1', data=states_model_flatten)
hf.close()

# Plot the model
#plot_model(model, to_file="model.png")

# Display the image
#data = plt.imread("model.png")
#plt.imshow(data)
#plt.show()
