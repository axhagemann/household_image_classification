import numpy as np
import os
import pickle
from tqdm import tqdm
from keras.layers import Input, Dense, Bidirectional, Conv1D, Flatten, MaxPool1D, TimeDistributed, CuDNNLSTM, GlobalMaxPool2D, GlobalAveragePooling2D
from keras import layers
from keras.callbacks import EarlyStopping,ModelCheckpoint
from keras.models import Sequential, Model
from keras.optimizers import Adam, SGD
from sklearn.model_selection import train_test_split
from keras.metrics import top_k_categorical_accuracy
import random
from utilities import top1_loss

bn_folder = 'assets/bn_mobilenet_224/'
fns = os.listdir(bn_folder)
random.shuffle(fns, random=random.seed(43))
split_at = len(fns)//10
fns_train = fns[split_at:]
fns_valid = fns[:split_at]
batch_size = 32

def data_gen_train():

    while True:
        for fn in fns_train:
            with open(bn_folder + fn,'rb') as f:
                content = pickle.load(f)

            yield content[0], content[1]

def data_gen_valid():
    while True:
        for fn in fns_valid:
            with open(bn_folder + fn,'rb') as f:
                content = pickle.load(f)

            yield content[0], content[1]

runs = {}
params = {}
units = [1024]
dropout = [0.6,0.7]
run_id = 0
for u in units:
    for d in dropout:
        run_id +=1
        inp = Input(shape=(7,7,1024))
        main = TimeDistributed(Bidirectional(CuDNNLSTM(u)))(inp)
        main = Bidirectional(CuDNNLSTM(u))(main)
        main = layers.Dropout(d)(main)
        out = Dense(128, activation = 'sigmoid')(main)

        model = Model(inputs=inp, outputs = out)
        model.compile(optimizer=Adam(lr = 0.0001), loss='categorical_crossentropy',metrics=[top1_loss])
        model.summary()


        check_point = ModelCheckpoint('models/MobileNet/BiLSTM_Gridsearch/top_model_%s_%s.hdf5'%(u,d), monitor="val_loss", mode="min", save_best_only=True, verbose=1)
        early_stop = EarlyStopping(patience=3)
        history = model.fit_generator(data_gen_train(),
                            validation_data = data_gen_valid(),
                            callbacks=[early_stop, check_point],
                            validation_steps= 540,
                            steps_per_epoch=5400,
                            epochs = 100)


        runs[run_id] = {'units':u,
                        'dropout':d,
                        'val_loss':np.min(history.history['val_loss']),
                        'val_top1_loss':np.min(history.history['val_top1_loss'])}