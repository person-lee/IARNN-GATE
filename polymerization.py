# coding:utf-8
import tensorflow as tf
from bigru import BIGRU_ATT
from utils import feature2cos_sim, max_pooling, cal_loss_and_acc


class LSTM_QA(object):
    def __init__(self, batch_size, quest_len, answer_len, embeddings, embedding_size, rnn_size, num_rnn_layers, max_grad_norm, l2_reg_lambda=0.0, adjust_weight=False,label_weight=[],is_training=True):
        # define input variable
        self.batch_size = batch_size
        self.embeddings = embeddings
        self.embedding_size = embedding_size
        self.adjust_weight = adjust_weight
        self.label_weight = label_weight
        self.rnn_size = rnn_size
        self.num_rnn_layers = num_rnn_layers
        self.quest_len = quest_len 
        self.answer_len = answer_len
        self.max_grad_norm = max_grad_norm
        self.l2_reg_lambda = l2_reg_lambda
        self.is_training = is_training

        self.keep_prob = tf.placeholder(tf.float32, name="keep_drop")
        
        self.lr = tf.Variable(0.0,trainable=False)
        self.new_lr = tf.placeholder(tf.float32, shape=[],name="new_learning_rate")
        self._lr_update = tf.assign(self.lr, self.new_lr)

        self.ori_input_quests = tf.placeholder(tf.int32, shape=[None, self.quest_len])
        self.cand_input_quests = tf.placeholder(tf.int32, shape=[None, self.answer_len])
        self.neg_input_quests = tf.placeholder(tf.int32, shape=[None, self.answer_len])

        self.test_input_q = tf.placeholder(tf.int32, shape=[None, self.quest_len])
        self.test_input_a = tf.placeholder(tf.int32, shape=[None, self.answer_len])


        #embedding layer
        with tf.device("/cpu:0"),tf.name_scope("embedding_layer"):
            W = tf.Variable(tf.to_float(self.embeddings), trainable=True, name="W")
            ori_quests =tf.nn.embedding_lookup(W, self.ori_input_quests)
            cand_quests =tf.nn.embedding_lookup(W, self.cand_input_quests)
            neg_quests =tf.nn.embedding_lookup(W, self.neg_input_quests)

            test_q =tf.nn.embedding_lookup(W, self.test_input_q)
            test_a =tf.nn.embedding_lookup(W, self.test_input_a)

        #dropout
        ori_quests = tf.nn.dropout(ori_quests, self.keep_prob)
        cand_quests = tf.nn.dropout(cand_quests, self.keep_prob)
        neg_quests = tf.nn.dropout(neg_quests, self.keep_prob)
        test_q = tf.nn.dropout(test_q, self.keep_prob)
        test_a = tf.nn.dropout(test_a, self.keep_prob)
        #build LSTM network
        with tf.variable_scope("GRU_scope", reuse=None):
            ori_q = BIGRU_ATT(ori_quests, self.rnn_size, self.batch_size)
            ori_q_feat = tf.nn.tanh(max_pooling(ori_q))
        with tf.variable_scope("GRU_scope", reuse=True):
            cand_a = BIGRU_ATT(cand_quests, self.rnn_size, self.batch_size, is_att=True, summary_state=ori_q_feat)
            neg_a = BIGRU_ATT(neg_quests, self.rnn_size, self.batch_size, is_att=True, summary_state=ori_q_feat)
            cand_q_feat = tf.nn.tanh(max_pooling(cand_a))
            neg_q_feat = tf.nn.tanh(max_pooling(neg_a))

            test_q_out = BIGRU_ATT(test_q, self.rnn_size, self.batch_size)
            test_q_out = tf.nn.tanh(max_pooling(test_q_out))
            test_a_out = BIGRU_ATT(test_a, self.rnn_size, self.batch_size, is_att=True, summary_state=test_q_out)
            test_a_out = tf.nn.tanh(max_pooling(test_a_out))

        self.ori_cand = feature2cos_sim(ori_q_feat, cand_q_feat)
        self.ori_neg = feature2cos_sim(ori_q_feat, neg_q_feat)
        self.loss, self.acc = cal_loss_and_acc(self.ori_cand, self.ori_neg)

        self.test_q_a = feature2cos_sim(test_q_out, test_a_out)


    def assign_new_lr(self,session,lr_value):
        session.run(self._lr_update,feed_dict={self.new_lr:lr_value})
