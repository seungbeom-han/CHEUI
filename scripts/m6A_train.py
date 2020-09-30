#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 20:29:58 2020

@author: pablo
"""

import os
import pickle

import numpy as np
#from tensorflow.keras import Input
#from tensorflow.keras import Model
#from tensorflow.keras.layers import Dense
#from tensorflow.keras.preprocessing.sequence import pad_sequences
from keras import backend as K
from sklearn import preprocessing
from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split
from keras.models import Model
from keras.callbacks import ModelCheckpoint

from itertools import product
import umap
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from matplotlib.lines import Line2D

#from tcn import TCN

import tensorflow as tf
#assert tf.test.is_gpu_available()
#assert tf.test.is_built_with_cuda()

from tensorflow.compat.v1 import ConfigProto
from tensorflow.compat.v1 import InteractiveSession
from keras.layers import Input
from tensorflow.keras.layers import Input
from scipy.spatial import distance
from scipy import signal
from math import floor

from sklearn.preprocessing import minmax_scale

import ray
ray.init()


config = ConfigProto()
config.gpu_options.allow_growth = True
session = InteractiveSession(config=config)


@ray.remote
def load_data_smooth(directory, model_kmer_dict, lenght_event):
    '''
    '''
    files = os.listdir(directory)
    dic_signal = {} # dictionary of signal event values
    dic_dwell = {} # dictionary of dwelling time values
    dic_distance = {} # dictionary of distance from the non-modified to the signal
    counter = 0
    for file in files:
        counter +=1
        file_raw = pickle.load(open(directory+file,"rb"))
        for signal_values in file_raw:
            signal_smoothed = []
            dwell_smoothed = []
            sequence_smothed = []
            for event in signal_values:
                if len(event) > 1000: # maximun event lenght
                    dwell_smoothed += [1000/1000]*lenght_event
                else:
                    dwell_smoothed += [len(event)/1000]*lenght_event # record the original dwelling time
                event_smoothed = smooth_event(event, lenght_event) # smooth the event
                signal_smoothed += event_smoothed  # add the event to the signal
            
            expected_smoothed = make_expected(model_kmer_dict, 
                                              file.split('_')[-2],
                                              lenght_event)
            
            #sequence = file.split('_')[-2]
            
            #sequence_smothed = make_sequences(sequence, lenght_event)
            
            try: # fix the equal kmers bug in script Epinano_site_parse_noA_all.py
                distance_vector = distance_calculator(expected_smoothed,
                                                      signal_smoothed)
            except:
                break
            
            #with open(directory[:-1]+'event.npy', "ab") as f:
            #    pickle.dump(signal_smoothed, f)

            with open(directory[:-1]+'distances_euclidean.npy', "ab") as f:
                pickle.dump(distance_vector, f)

            #with open(directory[:-1]+'dwell.npy', "ab") as f:
            #    pickle.dump(dwell_smoothed, f)
            
            #with open(directory[:-1]+'sequences.npy', "ab") as f:
           #     pickle.dump(sequence_smothed, f)
            
            #if file in dic_signal:
            #    dic_signal[file] += [signal_smoothed]
            #    dic_dwell[file] += [dwell_smoothed]
            #    dic_distance[file] += [distance_vector]
            #else:
            #    dic_distance[file] = [distance_vector]
            #    dic_signal[file] = [signal_smoothed]
            #    dic_dwell[file] = [dwell_smoothed]
            
        if counter == 200:
            return True
            #return [dic_signal, dic_dwell, dic_distance]


def make_expected(model_kmer_dict, kmer, event_lenght):
    '''
    '''
    expected_signal = []
    for i in range(5):
        expected_signal += [model_kmer_dict[kmer[i:i+5]]]*event_lenght
    return expected_signal

def distance_calculator(signal_expected, event_smoothed):
    '''
    '''
    #vector_distance = list(np.round(abs(np.array(signal_expected) - \
    #                                    np.array(event_smoothed)), 3))
    
    vector_distance_eu =    list(np.round(abs(np.array(signal_expected) - \
                                        np.array(event_smoothed)), 3))
    
    return vector_distance


def smooth_event(raw_signal, lenght_events):
    '''
    smmoth the signal 
    '''
    raw_signal_events = []
    
    if len(raw_signal) < lenght_events:
        event = top_median(raw_signal, lenght_events)
        raw_signal_events = [round(i, 3) for i in event]
        
    else:
        division = floor(len(raw_signal)/lenght_events)
        new_event = []
        for i in range(0, len(raw_signal), division):
            new_event.append(np.median(raw_signal[i:i+division]))
            if len(new_event) == lenght_events:
                break
        if len(new_event) < lenght_events:
            new_event = top_median(new_event, lenght_events)
        raw_signal_events = [round(i, 3) for i in new_event]
    return raw_signal_events


def top_median(array, lenght):
    '''
    This function top an array until some specific lenght
    '''
    extra_measure = [np.median(array)]*(lenght-len(array))
    array += extra_measure
    return array


def load_data(directory):
    '''
    '''
    files = os.listdir(directory)
    dic_signal = {}
    for file in files:
        dic_signal[file] = pickle.load(open(directory+file,"rb" ))
    
    return dic_signal


def plot_signals_10(KO_signal_filtered_np, WT_signal_filtered_np, kmer, save=None):
    '''
    This function wil plot the median and sd of a bunch of signals
    '''
    # first build the whole signals with medians
    sns.set_style('darkgrid')

    KO_signal = KO_signal_filtered_np.transpose().ravel()
    KO_signal_index = np.arange(1, 101)
    KO_signal_index = np.repeat(KO_signal_index, KO_signal_filtered_np.shape[0])
    
    KO_df = pd.DataFrame({'events' : KO_signal_index, 
                          'signal' : KO_signal})
    
    
    WT_signal = WT_signal_filtered_np.transpose().ravel()
    WT_signal_index = np.arange(1, 101)
    WT_signal_index = np.repeat(WT_signal_index, WT_signal_filtered_np.shape[0])
    
    WT_df = pd.DataFrame({'events' : WT_signal_index, 
                          'signal' : WT_signal})
    plt.figure(figsize=(15, 8))
    ax = sns.lineplot(x="events", y="signal", ci='sd', estimator=np.median, data=WT_df, color='red')
    ax2 = sns.lineplot(x="events", y="signal", ci='sd', estimator=np.median, data=KO_df, color='blue')
    ax2.lines[0].set_linestyle("--")
    plt.xticks([])
    plt.yticks([])
    plt.ylabel('Signal intensity', fontsize=30)
    X = [10, 30, 50, 70, 90]
    labels = list(kmer.split('_')[5])
    # You can specify a rotation for the tick labels in degrees or with keywords.
    plt.xticks(X, labels, fontsize=30)
    
    custom_lines = [Line2D([0], [0], color='blue', lw=4, markersize=40),
                    Line2D([0], [0], color='red', lw=4, markersize=40, linestyle='--')]
    
    plt.legend(custom_lines,
               ['NO MOD','MOD'],
               fancybox=True,
               framealpha=1, 
               shadow=True, 
               borderpad=1,
               fontsize=20
               )
    plt.show()
    if save:
        plt.title('Signal RNA IVT')
        plt.savefig(save+'.pdf',
                    format='pdf',
                    dpi=1200)
    plt.close('all')
    
    return True


def make_sequences(nucleotides, lenght):
    '''
    '''
    sequence_to_number = []
    for i in range(len(nucleotides)-4):
        sequence_to_number += [tokenizer[nucleotides[i:i+5]]]*lenght
    return(sequence_to_number)
    # return list(map(int, ''.join([OneHotDNA[i] for i in nucleotides])))


def plot_UMAP(no_mod_list, mod_list, plot=None):
    '''
    '''
    reducer = umap.UMAP()
    embedding = reducer.fit_transform(np.concatenate([mod_list, no_mod_list]))
    
    plt.figure(figsize=(15, 8))
    sns.scatterplot(embedding[:len(mod_list),0],
                    embedding[:len(mod_list),1],
                    color='b')
        
    sns.scatterplot(embedding[len(mod_list):,0],
                    embedding[len(mod_list):,1],
                    color='r')
    if plot:
        plt.savefig(plot+'UMAPembedding'+'.pdf',
                    format='pdf',
                    dpi=1200)
    plt.show()
    plt.close('all')
    return True
    
    

@ray.remote
def load_local_stored(file_path):
    '''
    '''
    data = []   
    with open(file_path, 'rb') as fr:
        try:
            while True:
                data.append(pickle.load(fr))
        except:
            pass
    return data


def recall(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    recall = true_positives / (possible_positives + K.epsilon())
    return recall

def precision(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + K.epsilon())
    return precision

def f1(y_true, y_pred):
    precision_ = precision(y_true, y_pred)
    recall_ = recall(y_true, y_pred)
    return 2*((precision_*recall_)/(precision_+recall_+K.epsilon()))


if __name__ == '__main__':
    
    mod_rep_1 = '/media/labuser/Data/nanopore/m6A_classifier/data/Epinano/doubleAA/mod_rep1_eventalign_numpy_sites_AA/'
    no_mod_rep_1 = '/media/labuser/Data/nanopore/m6A_classifier/data/Epinano/doubleAA/no_mod_rep1_eventalign_numpy_sites_AA/'
    
    model_kmer = pd.read_csv('/media/labuser/Data/nanopore/m6A_classifier/data/model_kmer.csv',
                             sep=',')
    
    # create a dictionary with each kmer and its current value
    model_kmer_dict = dict(zip(model_kmer['model_kmer'], model_kmer['model_mean']))
    
    # Create a column with the numbers that we will use as tokens from 0 to 1
    model_kmer['number'] = [round((i+1)/1025, 5) for i in range(len(model_kmer))]
    
    tokenizer = dict(zip(model_kmer['model_kmer'], model_kmer['number']))
    
    # start the load the raw signal files and preprocess the signals
    # also creating the vectors for distances, sequences and dwelling time
    #ret_id1 = load_data_smooth.remote(mod_rep_1, model_kmer_dict, 20)
    #ret_id2 = load_data_smooth.remote(no_mod_rep_1, model_kmer_dict, 20)
    
    #ret1 = ray.get(ret_id1)
    #ret2 = ray.get(ret_id2)
    
    # load the local stored data
    directory = '/media/labuser/Data/nanopore/m6A_classifier/data/Epinano/doubleAA/'
    mod_rep_1_signal_dwell_id = load_local_stored.remote(directory+'mod_rep1_eventalign_numpy_sites_AAdwell.npy')
    mod_rep_1_signal_events_id = load_local_stored.remote(directory+'mod_rep1_eventalign_numpy_sites_AAevent.npy')
    mod_rep_1_signal_distances_id = load_local_stored.remote(directory+'mod_rep1_eventalign_numpy_sites_AAdistances.npy')
    #mod_rep_1_signal_sequences_id = load_local_stored.remote(directory+'mod_rep1_eventalign_numpy_sites_AAsequences.npy')

    no_mod_rep_1_signal_dwell_id = load_local_stored.remote(directory+'no_mod_rep1_eventalign_numpy_sites_AAdwell.npy')
    no_mod_rep_1_signal_events_id = load_local_stored.remote(directory+'no_mod_rep1_eventalign_numpy_sites_AAevent.npy')
    no_mod_rep_1_signal_distances_id = load_local_stored.remote(directory+'no_mod_rep1_eventalign_numpy_sites_AAdistances.npy')
    #no_mod_rep_1_signal_sequences_id = load_local_stored.remote(directory+'no_mod_rep1_eventalign_numpy_sites_AAsequences.npy')

    mod_rep_1_signal_dwell = ray.get(mod_rep_1_signal_dwell_id)
    mod_rep_1_signal_events = ray.get(mod_rep_1_signal_events_id)
    mod_rep_1_signal_distances = ray.get(mod_rep_1_signal_distances_id)
    #mod_rep_1_signal_sequences = ray.get(mod_rep_1_signal_sequences_id)

    no_mod_rep_1_signal_dwell  = ray.get(no_mod_rep_1_signal_dwell_id)
    no_mod_rep_1_signal_events = ray.get(no_mod_rep_1_signal_events_id)
    no_mod_rep_1_signal_distances = ray.get(no_mod_rep_1_signal_distances_id)
    #no_mod_rep_1_signal_sequences = ray.get(no_mod_rep_1_signal_sequences_id)
    
    # put dwell time between 0 and 1
    #no_mod_rep_1_signal_dwell_sc = [[item/1000 for item in subl] for subl in no_mod_rep_1_signal_dwell]
    #mod_rep_1_signal_dwell_sc = [[item/1000 for item in subl] for subl in mod_rep_1_signal_dwell]
    
    # concatenate input vectors
    no_mod_input = np.concatenate([no_mod_rep_1_signal_events,
                                   no_mod_rep_1_signal_dwell,
                                   no_mod_rep_1_signal_distances],
                                   #np.array(no_mod_rep_1_signal_sequences)],
                                   axis=1)
    
    mod_input = np.concatenate([mod_rep_1_signal_events,
                                mod_rep_1_signal_dwell,
                                mod_rep_1_signal_distances],
                                #np.array(mod_rep_1_signal_sequences)],
                                axis=1)
    
    no_mod_input = no_mod_input.reshape(len(no_mod_input), 3, 100)
    mod_input = mod_input.reshape(len(mod_input), 3, 100)
    
    # transpose the last two dimensions to have each channel with separate information
    no_mod_input =  np.transpose(no_mod_input, (0, 2, 1))
    mod_input = np.transpose(mod_input, (0, 2, 1))
    
    
    total_data = np.concatenate([no_mod_input, mod_input],
                                axis=0)
    
    # Create y
    target = np.concatenate([np.zeros(len(no_mod_input)),
                             np.ones(len(mod_input))],
                            axis=0)
    
    # shuffle data
    total_data , target = shuffle(total_data, target, random_state=42)
    
    X_train, X_test, y_train, y_test = train_test_split( \
                        total_data, target, test_size=0.20, random_state=42)
    
    from DL_models import build_TCN_causalCall, TCN
    from tensorflow.keras import Input, Model # only for TCN
    from tcn import tcn_full_summary
    from tensorflow.keras.layers import Dense

   # inputs = Input(batch_shape=(None, 100, 3))
    
    #predictions = build_TCN_causalCall(inputs, 1)
    i = Input(batch_shape=(None, 100, 3))

    x1 = TCN(return_sequences=False,
             nb_filters=48,
             nb_stacks=3,
             kernel_size=3,
             dilations=[1,2,4,8,16], 
             padding='same',
             activation='relu',
             use_batch_norm=True,
             dropout_rate=0.15)(i)

    o = Dense(1, activation='sigmoid')(x1)
    
    
    model = Model(inputs=[i], outputs=[o])
   
    model.compile(optimizer='nadam',
                  loss='binary_crossentropy',
                  metrics=['accuracy',
                           recall,
                           precision,
                           f1])
    
    tcn_full_summary(model, expand_residual_blocks=True)

    checkpoint = ModelCheckpoint('/media/labuser/Data/nanopore/m6A_classifier/scripts/models/m6A_classifier_DB.h5',
                                 monitor='val_acc', verbose=1,
                                 save_best_only=True, mode='max')
    
    model.fit(X_train, y_train,
              batch_size=125,
              epochs=1,
              validation_data=(X_test, y_test),
              #callbacks=[checkpoint]
              )


