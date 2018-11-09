import data_helpers as dhrt
from tensorflow.contrib import learn
import numpy as np
from sklearn.preprocessing import StandardScaler


from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.model_selection import train_test_split
from keras.models import Sequential
from keras.layers import Dense, Activation, Flatten, Dropout, Conv1D, Conv2D, AveragePooling1D, MaxPooling1D, LSTM, Bidirectional, BatchNormalization, MaxPooling2D, GlobalAveragePooling1D
from keras.optimizers import SGD, Adam
from keras.utils import np_utils
import matplotlib.pyplot as plt
from Bio import pairwise2


# Network Parameters
learning_rate = 0.01
num_classes = 2
num_features = 372
batch_size = 8
nb_epoch = 32
hidden_size = 100
num_sequences = 10
num_classes = 2
num_filters = [16, 4]


def replace_spaces(x):
    return x.replace(' ', '')


def get_alignments(x, y, seq_i, seq_j, batch_size):
    '''
    Aligns every pair of sequences to prepare input to CNN
    :param x: a set of sequences
    :param y: a set of labels
    :return: a set of pairwise alignments of the sets in x (cartesian product) x
    '''
    a = pairwise2.align.globalxx(x[seq_i], x[seq_j], one_alignment_only=True)[0]
    align_x = np.array(list(a)[0:2])
    if np.array_equal(y[seq_i], y[seq_j]):
        align_y = np.array([1])
    else:
        align_y = np.array([0])
    for i in range(seq_i + 1, seq_i + batch_size):
        for j in range(seq_j + 1, seq_j + batch_size):
            if (i + batch_size) < len(x) and (j + batch_size) < len(x):
                a = pairwise2.align.globalxx(x[i], x[j], one_alignment_only=True)[0]
                align_x = np.vstack((align_x, np.array(list(a)[0:2])))
                if np.array_equal(y[i], y[j]):
                    align_y = np.append(align_y, np.array([1]))
                else:
                    align_y = np.append(align_y, np.array([0]))
    return align_x, align_y

def get_vocab(chars):
    vocab = {}
    i = 0
    for c1 in chars:
        for c2 in chars:
            vocab[c1+c2] = i
            i += 1
    return vocab


def base_pairs_to_onehot(seq1, seq2, max_len):
    vocab = get_vocab('atcg-')
    index_arr = np.array([])
    for i in range(0, max_len):
        if i < len(seq1):
            index_arr = np.append(index_arr, vocab[seq1[i]+seq2[i]])
        else:
            index_arr = np.append(index_arr, 6)
    return index_arr




def convert_base_pairs(x, y):
    lens = [len(seq) for alignment in x for seq in alignment]
    max_document_length = max(lens)
    #print('Max seq length:', max_document_length)
    #print('Input shape:', x.shape)
    vocab_processor = learn.preprocessing.VocabularyProcessor(max_document_length)
    x_proc = []
    y_proc = []
    for i in range(len(x)):
        #print('Alignment shape:', alignment.shape)
        proc = base_pairs_to_onehot(x[i][0], x[i][1], max_document_length)
        proc = np_utils.to_categorical(proc, num_classes=120)
        #scaler = StandardScaler().fit(np.float64(proc))
        #proc = scaler.transform(np.float64(proc))
        #print(proc)
        if len(x_proc) == 0:
            x_proc = proc
            #x_proc = np.expand_dims(x_proc, axis=2)
            y_proc = y[i]
        else:
            #print('shape:', x_proc.shape, proc.shape)
            x_proc = np.vstack((x_proc, proc))
            y_proc = np.append(y_proc, y[i])
    y_proc = np_utils.to_categorical(y_proc, num_classes=num_classes)
    #print('Labels shape', y_proc.shape)
    x_proc = np.reshape(x_proc, (y_proc.shape[0], -1, 120))
    #print(x_proc)
    return x_proc, y_proc


def generate_batch(x, y):
    for i in range(0, len(x), batch_size):
        for j in range(0, len(y), batch_size):
            align_x, align_y = (get_alignments(x, y, i, j, batch_size))
            #align_y = np.reshape(align_y, (len(align_y)//2, 2))
            align_x, align_y = convert_base_pairs(align_x, align_y)
            #align_x = np.expand_dims(align_x, axis=2)
            #align_x = np.reshape(align_x, (align_x.shape[0], align_x.shape[2], 2))
            #align_x = np.swapaxes(align_x, 0, 2)
            #print('Num Alignments', align_x.shape)
            #print('Labels:', align_y.shape)
            #print('Sample Alignment:', align_x[0], align_y[0])
            yield align_x, align_y


# load data
x_rt, y_rt = dhrt.load_data_and_labels('h3.pos', 'h3.neg')

x_rt = np.array([replace_spaces(seq) for seq in x_rt])
print('X:', x_rt)
y_rt = np.array(list(y_rt))
print(pairwise2.align.globalxx('aaattcgctgc','aaatctcgcgat', one_alignment_only=True))
shuffled_rt = np.random.permutation(range(len(x_rt)))
x_shuffle = x_rt[shuffled_rt]
y_shuffle = y_rt[shuffled_rt]

# split train data into train and validation
#sss = StratifiedShuffleSplit(test_size=0.2, random_state=23)
#for train_index, valid_index in sss.split(x_shuffle, y_shuffle):
#    x_train, x_valid = x_shuffle[train_index], y_shuffle[valid_index]
#    y_train, y_valid = x_shuffle[train_index], y_shuffle[valid_index]

x_train, x_valid, y_train, y_valid = train_test_split(x_shuffle,
                                                      y_shuffle,
                                                      stratify=y_shuffle,
                                                      test_size=0.2)

print('x shape:', x_train.shape)

model = Sequential()
# Shape is (batch_size, sentence_length)
#model.add(Conv2D(num_filters[0], kernel_size=(2,2), input_shape=(None, 2, 5)))
model.add(Conv1D(nb_filter=num_filters[0], filter_length=2, input_shape=(None, 120)))
model.add(Activation('relu'))
#model.add(MaxPooling1D(pool_size=num_features//batch_size, padding='valid'))
#model.add(Activation('relu'))
#model.add(Dropout(0.3))
model.add(Conv1D(nb_filter=num_filters[1], filter_length=1))
model.add(Activation('relu'))
model.add(Dropout(0.3))
#model.add(Bidirectional(LSTM(hidden_size)))
#model.add(BatchNormalization())
#model.add(AveragePooling1D(pool_size=int(num_features), padding='same'))
#model.add(MaxPooling2D(pool_size=(1, 1)))
#model.add(Dense(2048, activation='relu'))
model.add(Dense(1024, activation='relu'))
model.add(Dense(512, activation='relu'))
model.add(Dropout(0.3))
model.add(GlobalAveragePooling1D())
model.add(Dense(num_classes))
model.add(Activation('softmax'))
print(model.summary())

adam = Adam(lr=learning_rate)
sgd = SGD(lr=learning_rate, nesterov=True, decay=1e-6, momentum=0.9)
model.compile(loss='categorical_crossentropy', optimizer=sgd, metrics=['acc'])
print('Training shapes:', x_train.shape, y_train.shape)
print('Valid shapes:', x_valid.shape, y_valid.shape)
history = model.fit_generator(generate_batch(x_train, y_train),
                              steps_per_epoch=75,
                              epochs=nb_epoch,
                              validation_data=generate_batch(x_valid, y_valid),
                              validation_steps=75,
                              verbose=1)
print(history.history.keys())
# summarize history for accuracy
plt.plot(history.history['acc'])
plt.plot(history.history['val_acc'])
plt.title('model accuracy')
plt.ylabel('accuracy')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
plt.show()
# summarize history for loss
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
plt.show()
