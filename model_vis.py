import numpy as np
import gensim
from Bio import pairwise2
import os
import data_helpers as dhrt
from sklearn.model_selection import train_test_split
from keras.models import model_from_json, Model


word_length = 6
vec_length = 4

# load data
dir = os.getcwd() + '/histone_data/'
x_rt, y_rt = dhrt.load_data_and_labels_pos(dir + 'pos/h3k4me1.pos', pos=1)



def replace_spaces(x):
    return x.replace(' ', '')


x_rt = np.array([replace_spaces(seq) for seq in x_rt])
y_rt = np.array(list(y_rt))
shuffled_rt = np.random.permutation(range(len(x_rt)))
x_shuffle = x_rt[shuffled_rt]
y_shuffle = y_rt[shuffled_rt]
print('X:', x_shuffle)
print('Y:', y_shuffle)
print(pairwise2.align.globalxx(x_shuffle[0], x_shuffle[1], one_alignment_only=True)[0:2])

x_train, x_valid, y_train, y_valid = train_test_split(x_shuffle,
                                                      y_shuffle,
                                                      stratify=y_shuffle,
                                                      test_size=0.2)

# Model reconstruction from JSON file
with open('model_architecture.json', 'r') as f:
    model = model_from_json(f.read())

# Load weights into the new model
model.load_weights('model_weights.h5')


def alignment2vec(alignment, w2v):
    vec = []
    word_list = alignment.split(' ')
    if len(word_list[-1]) != word_length:
        word_list = word_list[:-1]
    for word in word_list:
        try:
            if len(vec) == 0:
                vec = w2v.word_vec(word)
            else:
                vec = np.vstack((vec, w2v.word_vec(word)))
        except Exception as e:
            print('Word', word, 'not in vocab')
    vec = np.reshape(vec, (len(word_list), -1))
    return vec


def get_test_alignment(x, i, j):
    w2v = gensim.models.KeyedVectors.load_word2vec_format('./alignment_vec.txt', binary=False)
    alignment = pairwise2.align.globalxx(x[i], x[j], one_alignment_only=True)[0]
    align_x = np.array(list(alignment)[0:2])
    s1 = align_x[0]
    s2 = align_x[1]
    s1 = ' '.join([s1[i:i + word_length] for i in range(0, len(s1), word_length)]).replace('-','x')
    s2 = ' '.join([s2[i:i + word_length] for i in range(0, len(s2), word_length)]).replace('-', 'x')
    word2vec1 = alignment2vec(s1, w2v)
    word2vec2 = alignment2vec(s2, w2v)
    word2vec1 = np.expand_dims(word2vec1, 0)
    word2vec2 = np.expand_dims(word2vec2, 0)
    return [word2vec1, word2vec2]

w2v = gensim.models.KeyedVectors.load_word2vec_format('./alignment_vec.txt', binary=False)
layer_outputs = [layer.output for layer in model.layers[2:]]
print(layer_outputs)
for layer in layer_outputs:
    print(layer)
activation_model = Model(inputs=model.input, outputs=layer_outputs)
activations = activation_model.predict(get_test_alignment(x_valid, 0, 1))
#print(activations)
activation_1 = activations[0]
print(activation_1)
for kernel in activation_1[0]:
    words = np.reshape(kernel, (-1, vec_length))
    print('Learned alignment motifs:')
    for word in words:
        print(w2v.similar_by_vector(word, topn=1)[0])