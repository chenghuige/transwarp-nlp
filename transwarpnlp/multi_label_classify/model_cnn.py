# -*- coding: utf-8 -*-

import numpy as np
import warnings
import tensorflow as tf
from transwarpnlp.multi_label_classify.cnn_config import CnnConfig

warnings.filterwarnings("ignore")

config = CnnConfig()

"""
使用tensorflow构建CNN模型进行多标签文本分类
"""

# 一些数据预处理的方法======================================
def get_idx_from_sent(sent, word_idx_map, max_l):
    """
    Transforms sentence into a list of indices. Pad with zeroes.
    """
    x = []
    words = sent.split()
    for i, word in enumerate(words):
        if word in word_idx_map and i < max_l:
            x.append(word_idx_map[word])
    while len(x) < max_l:  # 长度不够的，补充0
        x.append(0)
    # 一个训练的一个输入 形式为[0,0,0,0,x11,x12,,,,0,0,0] 向量长度为max_l+2*filter_h-2
    return x


def generate_batch(revs, word_idx_map, minibatch_index, class_num):
    batch_size = config.batch_size
    sentence_length = config.sentence_length
    minibatch_data = revs[minibatch_index * batch_size:(minibatch_index + 1) * batch_size]
    batchs = np.ndarray(shape=(batch_size, sentence_length), dtype=np.int32)
    labels = np.ndarray(shape=(batch_size, class_num), dtype=np.int32)

    for i in range(batch_size):
        sentece = minibatch_data[i]["text"]
        label_ids = minibatch_data[i]["y"].split(",")

        label = []
        for j in range(class_num):
            if int(j) in label_ids:
                label.append(1)
            else:
                label.append(0)

        labels[i] = label
        batch = get_idx_from_sent(sentece, word_idx_map, sentence_length)
        batchs[i] = batch
    return batchs, labels

def get_test_batch(revs, word_idx_map, class_num, cv=1):
    sentence_length = config.sentence_length
    test = []
    for rev in revs:
        if rev["split"] == cv:
            test.append(rev)
    minibatch_data = test
    test_szie = len(minibatch_data)
    batchs = np.ndarray(shape=(test_szie, sentence_length), dtype=np.int64)
    labels = np.ndarray(shape=[test_szie, class_num], dtype=np.int64)
    for i in range(test_szie):
        sentence = minibatch_data[i]["text"]
        label_ids = minibatch_data[i]["y"].split(",")

        label = []
        for j in range(class_num):
            if str(j) in label_ids:
                label.append(1)
            else:
                label.append(0)

        labels[i] = label

        batch = get_idx_from_sent(sentence, word_idx_map, sentence_length)
        batchs[i] = batch

    return batchs, labels

# 卷积图层 第一个卷积
def conv2d(x, W):
    return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='VALID')

# 定义pooling图层
def max_pool(x, filter_h):
    return tf.nn.max_pool(x, ksize=[1, config.img_h - filter_h + 1, 1, 1], strides=[1, 1, 1, 1], padding='VALID')

def build_model(x_in, y_in, keep_prob):
    # Embedding layer===============================
    # 要学习的词向量矩阵
    embeddings = tf.Variable(tf.random_uniform([config.word_idx_map_szie, config.vector_size], -1.0, 1.0))
    # 输入reshape
    x_image_tmp = tf.nn.embedding_lookup(embeddings, x_in)
    # 输入size: sentence_length*vector_size
    # x_image = tf.reshape(x_image_tmp, [-1,sentence_length,vector_size,1])======>>>>>
    # 将[None, sequence_length, embedding_size]转为[None, sequence_length, embedding_size, 1]
    x_image = tf.expand_dims(x_image_tmp, -1)  # 单通道

    # 定义卷积层，进行卷积操作===================================
    h_conv = []
    for filter_h in config.filter_hs:
        # 卷积的patch大小：vector_size*filter_h, 通道数量：1, 卷积数量：hidden_layer_input_size
        filter_shape = [filter_h, config.vector_size, 1, config.num_filters]
        W_conv1 = tf.Variable(tf.truncated_normal(filter_shape, stddev=0.1), name="W")
        b_conv1 = tf.Variable(tf.constant(0.1, shape=[config.num_filters]), name="b")
        h_conv1 = tf.nn.relu(conv2d(x_image, W_conv1) + b_conv1)  # 输出szie: (sentence_length-filter_h+1,1)
        h_conv.append(h_conv1)


    # pool层========================================
    h_pool_output = []
    for h_conv1, filter_h in zip(h_conv, config.filter_hs):
        h_pool1 = max_pool(h_conv1, filter_h)  # 输出szie:1
        h_pool_output.append(h_pool1)

    # 全连接层=========================================
    l2_reg_lambda = 0.001
    # 输入reshape
    num_filters_total = config.num_filters * len(config.filter_hs)
    h_pool = tf.concat(h_pool_output, 3)
    h_pool_flat = tf.reshape(h_pool, [-1, num_filters_total])
    h_drop = tf.nn.dropout(h_pool_flat, keep_prob)


    W = tf.Variable(tf.truncated_normal([num_filters_total, config.class_num], stddev=0.1))
    b = tf.Variable(tf.constant(0.1, shape=[config.class_num]), name="b")
    l2_loss = tf.nn.l2_loss(W) + tf.nn.l2_loss(b)

    scores = tf.nn.xw_plus_b(h_drop, W, b, name="scores")  # wx+b
    losses = tf.nn.sigmoid_cross_entropy_with_logits(logits=scores, labels=y_in)
    loss = tf.reduce_mean(losses) + l2_reg_lambda * l2_loss

    correct_prediction = tf.equal(tf.round(tf.nn.sigmoid(scores)), tf.round(y_in))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

    # correct_prediction = tf.equal(tf.argmax(scores, 1), y_in)
    # accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

    return loss, accuracy, embeddings
