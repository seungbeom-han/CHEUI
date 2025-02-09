#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 24 10:16:37 2021

@author: labuser
"""

import argparse

parser = argparse.ArgumentParser(prog='CHEUI_predict_model1 v0.1', description=
                                 """ 
                                 This script takes an ID+signal file generated using CHEUI_preprocess_* and predict methylation status \
                                 per read and per 9-mer.
                                 
                                 """, usage='python CHEUI_predict_model1.py -i <path_to_signlas+IDs_file> '\
                                            '-m <path_to_DL_model> -l <label> -o <file_out> \nversion: %(prog)s')

OPTIONAL = parser._action_groups.pop()
REQUIRED = parser.add_argument_group('required arguments')


REQUIRED.add_argument("-i", "--signals_input",
                      help="path to the ID+signal file",
                      metavar='\b',
                      required=True)

REQUIRED.add_argument("-m", "--DL_model",
                      help="path to trainned model 1 DL model",
                      metavar='\b',
                      required=True)

REQUIRED.add_argument("-l", "--label",
                      help="label of the condition of the sample, e.g. WT_rep1",
                      required=True)

REQUIRED.add_argument("-o", "--file_out",
                      help="Path to the output file",
                      metavar='\b',
                      required=True)

REQUIRED.add_argument("-r", "--resume", 
                      action='store_true',
                      help="Continue predictions from previous file",
                      default=False)

OPTIONAL.add_argument('-v', '--version', 
                        action='version', 
                        version='%(prog)s')                  

parser._action_groups.append(OPTIONAL)

ARGS = parser.parse_args()

# required arg
signals_input = ARGS.signals_input
DL_model = ARGS.DL_model
label = ARGS.label
file_out = ARGS.file_out
resume = ARGS.resume


from tensorflow.keras import Input
from tensorflow.keras.models import Model
import _pickle as cPickle
from DL_models import build_Jasper
import numpy as np
import os
import sys
import subprocess

# load the trainned model
inputs = Input(shape=(100, 2))
output = build_Jasper(inputs,Deep=True)
model = Model(inputs=inputs, outputs=output)


model.load_weights(DL_model)


if resume is not True:
    if os.path.isfile(file_out):
        print('WARNING: read level prediction file already exists, please delete it or change the output name')
        sys.exit()


if resume is True:
    try:
        result = subprocess.run(["wc", "-l", file_out], stdout=subprocess.PIPE, text=True)
        total_lines = int(result.stdout.split(' ')[0])
        print('previous number of predictions ', total_lines)
    except:
        print('Not found previous existing file '+ file_out)
        total_lines = 0
else:
    total_lines = 0


### load the stored data 
counter = 0
IDs_signals = {}

with open(signals_input, 'rb') as signal_in:  
    with open(file_out, 'a') as f_out:
        while True:
            try:
                counter +=1
                if counter <= total_lines:
                    seen_signal = cPickle.load(signal_in)
                    continue
                IDs_signals.update(cPickle.load(signal_in))
                
                # to avoid loading everything predict every 10k singnals
                if counter%20000 == 0:
                    if IDs_signals:
                       
                        predictions = model.predict(np.array(list(IDs_signals.values())))
                        keys = list(IDs_signals.keys())
                        
                        for indv_predit in enumerate(predictions.reshape(len(predictions))):
                            print(keys[indv_predit[0]]+'\t'+ \
                                  str(indv_predit[1])+'\t'+ \
                                  label,
                                  file=f_out)
                   
                        IDs_signals = {}
                    else:
                        continue
            except Exception as ex:
                print(ex)
                
                if IDs_signals:
                    predictions = model.predict(np.array(list(IDs_signals.values())))
                    keys = list(IDs_signals.keys())
                    
                    for indv_predit in enumerate(predictions.reshape(len(predictions))):
                        
                        print(keys[indv_predit[0]]+'\t'+ \
                              str(indv_predit[1])+'\t'+ \
                              label, 
                              file=f_out)
               
                    IDs_signals = {}
    
                print('All signals have been processed', counter)
                break
