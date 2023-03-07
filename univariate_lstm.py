# -*- coding: utf-8 -*-
"""Univariate_LSTM.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1etOuCmwVuEuIrXa883RJRyKP5IPINibQ

# Short Term Weather Forecasting using LSTMs 

## By Rahul Mondal, 18MF3IM31
---
"""

# Commented out IPython magic to ensure Python compatibility.
# %cd /content/
!git clone https://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@github.com/abhinav-bohra/DL-Weather-Prediction.git
# %cd /content/DL-Weather-Prediction

!git pull

"""# **Univariate Time Series Model**
---
"""

#--------------------------------------------------
# Importing Libraries
#--------------------------------------------------
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from keras.models import Sequential
from keras.callbacks import Callback
from datetime import datetime, timedelta
from keras.layers import Dense, LSTM
from tensorflow.keras.optimizers import RMSprop

pd.set_option('mode.chained_assignment', None)
pd.options.display.max_columns = None

"""## **1. Data loading and pre-processing**

### 1.1 Loading the dataset
"""

#--------------------------------------------------
# Loading the dataset
#--------------------------------------------------
raw_df = pd.read_csv( "weather_data.csv", sep = ',', na_values = ['', ' '])
raw_df.columns = raw_df.columns.str.lower().str.replace(' ', '_')

#--------------------------------------------------
# Pre-processing the dataset
#--------------------------------------------------
full_df = raw_df.dropna(axis=0, how='any', thresh=None, subset=None, inplace=False)
df = pd.get_dummies( full_df['raint'], drop_first=True).rename(columns = {'Yes':'raint'})

"""### 1.2 Data Visualization"""

def plot_train_points(df,Tp=7000):
    plt.figure(figsize=(15,4))
    plt.title("Rainfall of first {} data points".format(Tp),fontsize=16)
    plt.plot(df['raint'][:Tp],c='k',lw=1)
    plt.grid(True)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.show()

plot_train_points(df)

"""### 1.4 Train-Test Split"""

#We choose Tp=7000 here which means we will train the RNN with only first 7000 data points and 
#then let it predict the long-term trend (for the next > 35000 data points or so). 
Tp = int(len(df['raint'])*0.8)
train = np.array(df['raint'][:Tp]).reshape(-1,1)
test = np.array(df['raint'][Tp:]).reshape(-1,1)

"""### 1.5 Choose the embedding or step size
RNN model requires a step value that contains n number of elements as an input sequence. Here, we choose `step=8`. In more complex RNN and in particular for text processing, this is also called _embedding size_. The idea here is that **we are assuming that 8 hours of weather data can effectively predict the 9th hour data, and so on.**
"""

step = 14

# add step elements into train and test
test = np.append(test,np.repeat(test[-1,],step))
train = np.append(train,np.repeat(train[-1,],step))

print("Train data length:", train.shape)
print("Test data length:", test.shape)

"""### 1.6 Converting to a multi-dimensional array
Next, we'll convert test and train data into the matrix with step value as it has shown above example.
"""

def convertToMatrix(data, step):
    X, Y =[], []
    for i in range(len(data)-step):
        d=i+step  
        X.append(data[i:d,])
        Y.append(data[d,])
    return np.array(X), np.array(Y)

trainX,trainY = convertToMatrix(train,step)
testX,testY = convertToMatrix(test,step)

trainX = np.reshape(trainX, (trainX.shape[0], 1, trainX.shape[1]))
testX = np.reshape(testX, (testX.shape[0], 1, testX.shape[1]))

print("Training data shape:", trainX.shape,', ',trainY.shape)
print("Test data shape:", testX.shape,', ',testY.shape)

"""## **2. Modeling**

### Keras model with `LSTM` layer

A simple function to define the LSTM model. It uses a single neuron for the output layer because we are predicting a real-valued number here. As activation, it uses the ReLU function. Following arguments are supported.

- neurons in the RNN layer
- embedding length (i.e. the step length we chose)
- nenurons in the densely connected layer
- learning rate
"""

# Metrics
from keras import backend as K

def recall_m(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    recall = true_positives / (possible_positives + K.epsilon())
    return recall

def precision_m(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + K.epsilon())
    return precision

def f1_m(y_true, y_pred):
    precision = precision_m(y_true, y_pred)
    recall = recall_m(y_true, y_pred)
    return 2*((precision*recall)/(precision+recall+K.epsilon()))

import tensorflow as tf

def build_lstm(num_units=128, embedding=14, num_dense=32, lr=0.001):
    """
    Builds and compiles a simple RNN model
    Arguments:
              num_units: Number of units of a the simple RNN layer
              embedding: Embedding length
              num_dense: Number of neurons in the dense layer followed by the RNN layer
              learning_rate: Learning rate (uses RMSprop optimizer)
    Returns:
              A compiled Keras model.
    """
    model = Sequential()
    model.add(LSTM(units=num_units, input_shape=(1,embedding), activation="relu"))
    model.add(Dense(num_dense, activation="relu"))
    model.add(Dense(1, activation="sigmoid"))
    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['mse'])
    # model.compile(optimizer=RMSprop(learning_rate=lr), loss='binary_crossentropy')

    return model

model_rainfall = build_lstm(embedding=step,lr=0.0005)

model_rainfall.summary()

# Keras `Callback` class to print progress of the training at regular epoch interval
class MyCallback(Callback):
    def on_epoch_end(self, epoch, logs=None):
        if (epoch+1) % 50 == 0 and epoch>0:
            print("Epoch number {} done".format(epoch+1))

# Batch size and number of epochs
batch_size = 128
num_epochs = 1000

"""### Training the model"""

# Commented out IPython magic to ensure Python compatibility.
# %%time
# model_rainfall.fit( trainX, trainY, 
#                     epochs=num_epochs, 
#                     batch_size=batch_size, 
#                     callbacks=[MyCallback(), tf.keras.callbacks.EarlyStopping(monitor='mse', patience=2)],verbose=1)

"""### Plot RMSE loss over epochs"""

plt.figure(figsize=(7,5))
plt.title("RMSE loss over epochs",fontsize=16)
plt.plot(np.sqrt(model_rainfall.history.history['mse']),c='k',lw=2)
plt.grid(True)
plt.xlabel("Epochs",fontsize=14)
plt.ylabel("Root-mean-squared Error",fontsize=14)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)
plt.show()

"""## Result and analysis

### What did the model see while training?
Showing again what exactly the model see during training.
"""

plt.figure(figsize=(20,4))
plt.title("This is what the model saw",fontsize=18)
x_axis = np.arange(1, 1+len(trainX), 1, dtype=int)
plt.scatter(x_axis, trainX[:,0][:,0])
plt.show()

"""### Now predict the future points
Now, we can generate predictions for the future by passing `testX` to the trained model.
"""

threshold = 0.5
trainPredict = model_rainfall.predict(trainX)
trainPredict = [1 if p>=threshold else 0 for p in trainPredict]
testPredict= model_rainfall.predict(testX)
testPredict = [1 if p>=threshold else 0 for p in testPredict]
predicted=np.concatenate((trainPredict,testPredict),axis=0)

plt.figure(figsize=(20,4))
plt.title("This is what the model predicted",fontsize=18)
x_axis = np.arange(1, 1+len(testPredict), 1, dtype=int)
plt.scatter(x_axis, testPredict, c='orange')
plt.show()

"""### Plotting the ground truth and model predictions together
Plotting the ground truth and the model predictions together to see if it follows the general trends in the ground truth data
"""

index = df.index.values

plt.figure(figsize=(15,5))
plt.title("Rainfall: Ground truth and prediction together",fontsize=18)
plt.plot(index,df['raint'],c='blue')
plt.plot(index,predicted,c='orange',alpha=0.75)
plt.legend(['True data','Predicted'],fontsize=15)
plt.axvline(x=Tp, c="r")
plt.grid(True)
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)
plt.ylim(0,1)
plt.show()

"""## **Perfromance Evaluation**"""

from sklearn.metrics import classification_report
trainTruth = df['raint'][:Tp]
testTruth = df['raint'][Tp:]
cm_train = classification_report(trainTruth, trainPredict)
cm_test = classification_report(testTruth, testPredict)
cm_full = classification_report(df['raint'], predicted)

print(cm_train)

print(cm_test)

print(cm_full)

"""## Performance on test set"""

def measure_performance (clasf_matrix):
    measure = pd.DataFrame({
                            'sensitivity': [round(clasf_matrix[0,0]/(clasf_matrix[0,0]+clasf_matrix[0,1]),2)], 
                            'specificity': [round(clasf_matrix[1,1]/(clasf_matrix[1,0]+clasf_matrix[1,1]),2)],
                            'precision': [round(clasf_matrix[0,0]/(clasf_matrix[0,0]+clasf_matrix[1,0]),2)],
                            'recall': [round(clasf_matrix[0,0]/(clasf_matrix[0,0]+clasf_matrix[0,1]),2)],
                            'overall_acc': [round((clasf_matrix[0,0]+clasf_matrix[1,1])/(clasf_matrix[0,0]+clasf_matrix[0,1]+clasf_matrix[1,0]+clasf_matrix[1,1]),2)]
                          })
    return measure

def my_acc(testTruth, testPredict):
  cnt=0
  for g,p in zip(testTruth, testPredict):
    if g==p:
      cnt=cnt+1
  return cnt/len(testTruth)

from sklearn import metrics
from sklearn.metrics import confusion_matrix
cm = metrics.confusion_matrix(testTruth, testPredict)
rnn_metrics_df = pd.DataFrame(measure_performance(cm))

print("-"*100)
print(rnn_metrics_df)
print("-"*100)
print( f'Total Accuracy sklearn: {np.round( 100*metrics.accuracy_score( testTruth, testPredict ), 2 )}%')
print( f'Total Accuracy me     : {np.round( 100*my_acc( testTruth, testPredict ), 2 )}%')

