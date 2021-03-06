#!/usr/bin/env python
from reader.image_conversion import convert
from reader.gainfuzzifyNew import gain
from reader.alphaLearning import eta
from reader.alphaLearning import alpha
from reader.fuzzyBP import FuzzyBP
import tensorflow as tf
import numpy as np
import shutil
import zipfile

def logSigmoid(x):
	return tf.divide(tf.constant(1.0), tf.add(tf.constant(1.0), tf.exp(tf.negative(tf.multiply(beta,x)))))

def diffLogSigmoid(x):
	return tf.multiply(beta, tf.multiply(logSigmoid(x), tf.subtract(tf.constant(1.0), logSigmoid(x))))

#Neural Network Parameters

x = tf.placeholder(tf.float32, [None, 100])
y = tf.placeholder(tf.float32, [None, 4])
learningRate = tf.constant(0.5)
beta = tf.Variable(1.0)
middle = 30

#Momentum and Learning Rate Constants
momentum = tf.Variable(0.0)
momentumHidden = tf.Variable(0.0)
momentumOutput = tf.Variable(0.0)
learningRateH = tf.Variable(0.5)
learningRateO = tf.Variable(0.5)

#Neural Network Construction

weight1 = tf.Variable(tf.zeros([100, middle]), tf.float32)
bias1 = tf.Variable(tf.zeros([1, middle], tf.float32))
weight2 = tf.Variable(tf.zeros([middle, 4], tf.float32))
bias2 = tf.Variable(tf.zeros([1, 4], tf.float32))

#Bias and weight storage for momentum

oldDeltaWeight1 = tf.Variable(tf.zeros([100, middle], dtype=tf.float32))
oldDeltaBias1 = tf.Variable(tf.zeros([1, middle], dtype=tf.float32))
oldDeltaWeight2 = tf.Variable(tf.zeros([middle, 4], dtype=tf.float32))
oldDeltaBias2 = tf.Variable(tf.zeros([1, 4], dtype=tf.float32))


net1 = tf.add(tf.matmul(x, weight1), bias1)
out1 = logSigmoid(net1)
net2 = tf.add(tf.matmul(out1, weight2), bias2)
out2 = logSigmoid(net2)

# Backpropagation begins

diff = tf.subtract(out2, y)

S2 = tf.multiply(tf.constant(-2.0),tf.multiply(diff, diffLogSigmoid(net2)))
deltaBias2 = S2
deltaWeight2 = tf.matmul(tf.transpose(out1), S2)
 
S1 = tf.multiply(tf.matmul(S2, tf.transpose(weight2)), diffLogSigmoid(net1))
deltaBias1 = S1
deltaWeight1 = tf.matmul(tf.transpose(x), S1)

s1 = tf.reduce_mean(S1)
s2 = tf.reduce_mean(S2)
# s1Abs = tf.reduce_mean(tf.abs(S1))
# s2Abs = tf.reduce_mean(tf.abs(S2))
# s1 = tf.cond((tf.less(s1,0)), lambda: tf.negative(s1Abs), lambda: s1Abs)
# s2 = tf.cond((tf.less(s2,0)), lambda: tf.negative(s2Abs), lambda: s2Abs)

# General Backpropagation results

generalResult = [
	tf.assign(weight1,
			tf.add(weight1, tf.multiply(learningRate, deltaWeight1)))
  , tf.assign(bias1,
			tf.add(bias1, tf.multiply(learningRate,
							   tf.reduce_mean(deltaBias1, axis=[0]))))
  , tf.assign(weight2,
			tf.add(weight2, tf.multiply(learningRate, deltaWeight2)))
  , tf.assign(bias2,
			tf.add(bias2, tf.multiply(learningRate,
							   tf.reduce_mean(deltaBias2, axis=[0]))))
]

# Backpropagation with momentum

momentumResult = [
	tf.assign(weight1,
			tf.add(weight1, tf.multiply(learningRateH, tf.add(deltaWeight1, tf.multiply(momentumHidden, oldDeltaWeight1))))),
	tf.assign(bias1,
			tf.add(bias1, tf.multiply(learningRateH,
							   tf.add(tf.reduce_mean(deltaBias1, axis=[0]), tf.multiply(momentumHidden, tf.reduce_mean(oldDeltaBias1, axis=[0])))))),
	tf.assign(weight2,
			tf.add(weight2, tf.multiply(learningRateO, tf.add(deltaWeight2, tf.multiply(momentumOutput, oldDeltaWeight2))))),
	tf.assign(bias2,
			tf.add(bias2, tf.multiply(learningRateO,
							   tf.add(tf.reduce_mean(deltaBias2, axis=[0]), tf.multiply(momentumOutput, tf.reduce_mean(oldDeltaBias2, axis=[0])))))),
	tf.assign(oldDeltaWeight1, deltaWeight1),
	tf.assign(oldDeltaBias1, deltaBias1),
	tf.assign(oldDeltaWeight2, deltaWeight2),
	tf.assign(oldDeltaBias2, deltaBias2)
]

# Accuracy and convergence measures

acct_mat = tf.equal(tf.argmax(out2, 1), tf.argmax(y, 1))
acct_res = tf.reduce_sum(tf.cast(acct_mat, tf.float32))

conv_mat = tf.multiply(100.0, tf.subtract(1.0, tf.abs(tf.reduce_mean(diff, axis=[0]))))
conv_res = tf.reduce_min(conv_mat)

def checkAccuracy(sess, numTestingSamples):
	return sess.run(acct_res, feed_dict =
						   {x: mnist.test.images[:numTestingSamples],
							y : mnist.test.labels[:numTestingSamples]})

def checkConvergence(sess, image, result):
	return sess.run(conv_res, feed_dict = 
							{x: image,
							y : result})


def read(sess, imagepath):
	image = [convert(imagepath)]
	return sess.run(out2, feed_dict = {x: image})

def outputCharacter(sess, imagepath):
	output = read(sess, imagepath)
	index = np.argmax(output)
	if (index < 10):
		return index
	else :
		return chr(index+55)


def reset(sess):
	sess.run([
		tf.assign(weight1, tf.truncated_normal([100, middle])),
		tf.assign(bias1, tf.truncated_normal([1, middle])),
		tf.assign(weight2, tf.truncated_normal([middle, 10])),
		tf.assign(bias2, tf.truncated_normal([1, 10]))
		])
	print("Network Reset!")


def restoreModel(session,filename):
	saver = tf.train.Saver()
	unzip = zipfile.ZipFile("./"+filename+".zip")
	unzip.extractall("./temp")
	unzip.close()
	saver.restore(sess,"./temp/"+filename)
	shutil.rmtree("./temp")
	return session


def session():
	sess = tf.Session()
	sess.run(tf.global_variables_initializer())
	return sess


def storeModel(session,filename):
	saver = tf.train.Saver()
	saver.save(session,"./temp/"+filename)
	shutil.make_archive(filename, 'zip', "./temp")
	shutil.rmtree("./temp")


def train(sess, data, result, enableGainFuzzification= True):
	arr=[]
	data = [data]
	result = [result]
	convergence = 0.0
	j = 0
	while(convergence < 99.9):
		j+=1
		l = sess.run([generalResult, s1, s2], feed_dict = {x: data, y:result})
		if enableGainFuzzification:
			sess.run(tf.assign(beta, tf.constant(gain(l[1], l[2]), dtype=tf.float32)))
		convergence = checkConvergence(sess, data, result)
		print(str(j) + ":" + str(convergence))
		arr.append(convergence)
		if j>10000:
			break
	print("Trained Model with the data in " + str(j) + " iterations!")
	return arr

# def train2(sess, imagepath, actualresult, enableGainFuzzification= True, enableEtaFuzzification=True, enableMomentumFuzzification=True, momentum=0.6):
# 	arr=[]
# 	image = [convert(imagepath)]
# 	result = np.zeros(10)
# 	result[actualresult] = 1.0
# 	result = [result]
# 	convergence = 0.0
# 	j = 0
# 	l1 = [0.0,0.0,0.0]
# 	while(np.amin(np.array(convergence)) < 99.8):
# 		j+=1
# 		lprev = [l1[1],l1[2]]
# 		l1 = sess.run([momentumResult, s1, s2], feed_dict = {x: image,
# 										y:result})
# 		if enableGainFuzzification:
# 			sess.run(tf.assign(beta, tf.constant(gain(l1[1], l1[2],100), dtype=tf.float32)))
# 		if enableEtaFuzzification:
# 			lh = sess.run(tf.assign(learningRateH, tf.constant(eta(l1[1], l1[1]-lprev[0]), dtype=tf.float32)))
# 			lo = sess.run(tf.assign(learningRateO, tf.constant(eta(l1[2], l1[2]-lprev[1]), dtype=tf.float32)))
# 		if enableMomentumFuzzification:
# 			mh = sess.run(tf.assign(momentumHidden, tf.constant(alpha(l1[1], l1[1]-lprev[0]), dtype=tf.float32)))
# 			mo = sess.run(tf.assign(momentumOutput, tf.constant(alpha(l1[2], l1[2]-lprev[1]), dtype=tf.float32)))
# 		convergence = checkConvergence(sess, image, result)
# 		print(convergence)
# 		arr.append(convergence)
# 	print("Trained Model with the new image!")
# 	return arr