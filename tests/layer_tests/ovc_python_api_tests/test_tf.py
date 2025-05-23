# Copyright (C) 2018-2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
import numpy as np
import openvino as ov
import os
import sys
import pytest
import tempfile
import tensorflow as tf
import unittest
from common import constants
from common.layer_test_class import CommonLayerTest
from common.mo_convert_test_class import CommonMOConvertTest
from common.utils.tf_utils import save_to_pb
from openvino import PartialShape, Model, Dimension
from openvino.test_utils import compare_functions
from pathlib import Path


def create_tf_graph_def(tmp_dir):
    tf.compat.v1.reset_default_graph()

    with tf.compat.v1.Session() as sess:
        inp1 = tf.compat.v1.placeholder(tf.float32, [1, 2, 3], 'Input')
        inp2 = tf.compat.v1.placeholder(tf.float32, [1, 2, 3], 'Input')
        relu = tf.nn.relu(inp1 + inp2, name='Relu')

        output = tf.nn.sigmoid(relu, name='Sigmoid')

        tf.compat.v1.global_variables_initializer()
        tf_net = sess.graph_def

    shape = PartialShape([1, 2, 3])
    param1 = ov.opset8.parameter(shape, dtype=np.float32)
    param2 = ov.opset8.parameter(shape, dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")

    return tf_net, model_ref, None


def create_keras_model(temp_dir):
    tf.keras.backend.clear_session()
    tf.compat.v1.reset_default_graph()

    input_names = ["Input1", "Input2"]
    input_shape = [1, 2, 3]

    x1 = tf.keras.Input(shape=input_shape, name=input_names[0])
    x2 = tf.keras.Input(shape=input_shape, name=input_names[1])
    relu = tf.keras.layers.Activation('relu')(x1 + x2)
    sigmoid = tf.keras.layers.Activation('sigmoid')(relu)
    keras_net = tf.keras.Model(inputs=[x1, x2], outputs=[sigmoid])

    shape = PartialShape([-1, 1, 2, 3])
    param1 = ov.opset8.parameter(shape, dtype=np.float32)
    param2 = ov.opset8.parameter(shape, dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")
    tf.keras.backend.clear_session()

    return keras_net, model_ref, None


def create_tf1_wrap_function(tmp_dir):
    def f(x, y):
        return tf.nn.sigmoid(tf.nn.relu(x + y))

    func = tf.compat.v1.wrap_function(f, [tf.TensorSpec((1, 2, 3), tf.float32),
                                          tf.TensorSpec((1, 2, 3), tf.float32)])

    shape = PartialShape([1, 2, 3])
    param1 = ov.opset8.parameter(shape, dtype=np.float32)
    param2 = ov.opset8.parameter(shape, dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")

    return func, model_ref, None


def create_tf_session(tmp_dir):
    from tensorflow.python.eager.context import graph_mode

    with graph_mode():
        tf.compat.v1.reset_default_graph()
        sess = tf.compat.v1.Session()
        inp1 = tf.compat.v1.placeholder(tf.float32, [1, 2, 3], 'Input1')
        inp2 = tf.compat.v1.placeholder(tf.float32, [1, 2, 3], 'Input2')
        relu = tf.nn.relu(inp1 + inp2, name='Relu')

        output = tf.nn.sigmoid(relu, name='Sigmoid')

        tf.compat.v1.global_variables_initializer()

    shape = PartialShape([1, 2, 3])
    param1 = ov.opset8.parameter(shape, dtype=np.float32)
    param2 = ov.opset8.parameter(shape, dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")

    return sess, model_ref, None


def create_tf_module(tmp_dir):
    class Net(tf.Module):
        def __init__(self, name=None):
            super(Net, self).__init__(name=name)

        def __call__(self, x, y):
            return tf.nn.sigmoid(tf.nn.relu(x + y))

    shape = PartialShape([1, 2, 3])
    param1 = ov.opset8.parameter(shape, dtype=np.float32)
    param2 = ov.opset8.parameter(shape, dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")

    net = Net()
    return net, model_ref, {'example_input': (np.random.rand(1, 2, 3).astype(np.float32),
                                              np.random.rand(1, 2, 3).astype(np.float32))}


def create_tf_module_dynamic(tmp_dir):
    class Net(tf.Module):
        def __init__(self, name=None):
            super(Net, self).__init__(name=name)

        def __call__(self, x, y):
            return tf.nn.sigmoid(tf.nn.relu(x + y))

    input_shapes = [PartialShape([-1, Dimension(3, -1), Dimension(4)]),
                    PartialShape([-1, Dimension(3), Dimension(4, -1)])]

    param1 = ov.opset8.parameter(input_shapes[0], dtype=np.float32)
    param2 = ov.opset8.parameter(input_shapes[1], dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")

    net = Net()
    return net, model_ref, {'input': input_shapes,
                            'example_input': (np.random.rand(1, 2, 3).astype(np.float32),
                                              np.random.rand(1, 2, 3).astype(np.float32))}


def create_keras_layer(tmp_dir):
    class LayerModel(tf.keras.layers.Layer):

        def __init__(self):
            super(LayerModel, self).__init__()

        def call(self, x, y):
            return tf.sigmoid(tf.nn.relu(x + y))

    shape = PartialShape([1, 2, 3])
    param1 = ov.opset8.parameter(shape, dtype=np.float32)
    param2 = ov.opset8.parameter(shape, dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")

    net = LayerModel()
    return net, model_ref, {'example_input': (np.random.rand(1, 2, 3).astype(np.float32),
                                              np.random.rand(1, 2, 3).astype(np.float32))}


def create_keras_layer_dynamic(tmp_dir):
    class LayerModel(tf.keras.layers.Layer):

        def __init__(self):
            super(LayerModel, self).__init__()

        def call(self, x, y):
            return tf.sigmoid(tf.nn.relu(x + y))

    input_shapes = [PartialShape([-1, Dimension(3, -1), Dimension(4)]),
                    PartialShape([-1, Dimension(3), Dimension(4, -1)])]

    param1 = ov.opset8.parameter(input_shapes[0], dtype=np.float32)
    param2 = ov.opset8.parameter(input_shapes[1], dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")

    net = LayerModel()
    return net, model_ref, {'input': input_shapes,
                            'example_input': (np.random.rand(1, 2, 3).astype(np.float32),
                                              np.random.rand(1, 2, 3).astype(np.float32))
                            }


def create_tf_checkpoint(tmp_dir):
    input_names = ["Input1", "Input2"]
    input_shape = [1, 2, 3]

    x1 = tf.keras.Input(shape=input_shape, name=input_names[0])
    x2 = tf.keras.Input(shape=input_shape, name=input_names[1])
    relu = tf.keras.layers.Activation('relu')(x1 + x2)
    sigmoid = tf.keras.layers.Activation('sigmoid')(relu)
    model = tf.keras.Model(inputs=[x1, x2], outputs=[sigmoid])
    checkpoint = tf.train.Checkpoint(model)

    shape = PartialShape([-1, 1, 2, 3])
    param1 = ov.opset8.parameter(shape, dtype=np.float32)
    param2 = ov.opset8.parameter(shape, dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")

    return checkpoint, model_ref, None


def create_tf_function(temp_dir):
    @tf.function(
        input_signature=[tf.TensorSpec(shape=[1, 2, 3], dtype=tf.float32),
                         tf.TensorSpec(shape=[1, 2, 3], dtype=tf.float32)])
    def f(x1, x2):
        y = tf.nn.sigmoid(tf.nn.relu(x1 + x2))
        return y

    shape = PartialShape([1, 2, 3])
    param1 = ov.opset8.parameter(shape, dtype=np.float32)
    param2 = ov.opset8.parameter(shape, dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")

    return f, model_ref, None


def create_tf_graph(temp_dir):
    tf.compat.v1.reset_default_graph()

    with tf.compat.v1.Session() as sess:
        inp1 = tf.compat.v1.placeholder(tf.float32, [1, 2, 3], 'Input')
        inp2 = tf.compat.v1.placeholder(tf.float32, [1, 2, 3], 'Input')
        relu = tf.nn.relu(inp1 + inp2, name='Relu')

        output = tf.nn.sigmoid(relu, name='Sigmoid')

        tf.compat.v1.global_variables_initializer()
        tf_net = sess.graph

    shape = PartialShape([1, 2, 3])
    param1 = ov.opset8.parameter(shape, dtype=np.float32)
    param2 = ov.opset8.parameter(shape, dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")

    return tf_net, model_ref, None


def create_tf_saved_model_dir(temp_dir):
    input_names = ["Input1", "Input2"]
    input_shape = [1, 2, 3]

    x1 = tf.keras.Input(shape=input_shape, name=input_names[0])
    x2 = tf.keras.Input(shape=input_shape, name=input_names[1])
    relu = tf.keras.layers.Activation('relu')(x1 + x2)
    sigmoid = tf.keras.layers.Activation('sigmoid')(relu)
    keras_net = tf.keras.Model(inputs=[x1, x2], outputs=[sigmoid])

    tf.saved_model.save(keras_net, temp_dir + "/model")

    shape = PartialShape([-1, 1, 2, 3])
    param1 = ov.opset8.parameter(shape, name="Input1:0", dtype=np.float32)
    param2 = ov.opset8.parameter(shape, name="Input2:0", dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu = ov.opset8.relu(add)
    sigm = ov.opset8.sigmoid(relu)

    parameter_list = [param1, param2]
    model_ref = Model([sigm], parameter_list, "test")

    return temp_dir + "/model", model_ref


def create_tf_stateful_partioned_call_net(temp_dir):
    tf.compat.v1.reset_default_graph()

    data_shape = [1, 1, 10, 10]
    filters_shape = [3, 3, 1, 1]

    strides = [1, 1]
    pads_begin = [0, 0]
    pads_end = [0, 0]
    dilations = [1, 1]

    @tf.function
    def second_func(input, filter):
        conv = tf.raw_ops.Conv2D(input=input, filter=filter, strides=[1, 1, 1, 1], padding='SAME', data_format='NCHW')
        return conv

    @tf.function(
        input_signature=[tf.TensorSpec(shape=data_shape, dtype=tf.float32),
                         tf.TensorSpec(shape=filters_shape, dtype=tf.float32)])
    def first_func(input, filter):
        conv = second_func(input, filter)
        return conv

    tf_model = first_func

    param1 = ov.opset8.parameter(data_shape, dtype=np.float32)
    param2 = ov.opset8.parameter(filters_shape, dtype=np.float32)
    transpose2 = ov.opset8.transpose(param2, np.array([3, 2, 0, 1], dtype=np.int64))
    conv = ov.opset11.convolution(param1, transpose2, strides, pads_begin, pads_end, dilations, auto_pad="same_upper")

    parameter_list = [param1, param2]
    model_ref = Model([conv], parameter_list, "test")

    return tf_model, model_ref, {}


def create_keras_layer_input_list():
    class LayerModel(tf.keras.layers.Layer):

        def __init__(self):
            super(LayerModel, self).__init__()

        def call(self, x, y):
            res_list = [tf.sigmoid(tf.nn.relu(x + y)), tf.nn.relu(x), tf.sigmoid(y)]
            return res_list

    input_shapes = [PartialShape([1, 2, 3]),
                    PartialShape([1, 2, 3])]

    param1 = ov.opset8.parameter(input_shapes[0], dtype=np.float32)
    param2 = ov.opset8.parameter(input_shapes[1], dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu1 = ov.opset8.relu(add)
    sigm1 = ov.opset8.sigmoid(relu1)
    relu2 = ov.opset8.relu(param1)
    sigm2 = ov.opset8.sigmoid(param2)

    parameter_list = [param1, param2]
    model_ref = Model([sigm1, relu2, sigm2], parameter_list, "test")
    return LayerModel(), model_ref


def create_keras_layer_input_list_one_inp():
    class LayerModel(tf.keras.layers.Layer):

        def __init__(self):
            super(LayerModel, self).__init__()

        def call(self, x):
            res_list = [tf.sigmoid(tf.nn.relu(x)), tf.nn.relu(x)]
            return res_list

    input_shapes = [PartialShape([1, 2, 3])]

    param1 = ov.opset8.parameter(input_shapes[0], dtype=np.float32)
    relu1 = ov.opset8.relu(param1)
    sigm1 = ov.opset8.sigmoid(relu1)
    parameter_list = [param1]
    model_ref = Model([sigm1, relu1], parameter_list, "test")

    return LayerModel(), model_ref


def create_keras_layer_input_dict():
    class LayerModel(tf.keras.layers.Layer):

        def __init__(self):
            super(LayerModel, self).__init__()

        def call(self, args):
            res = {}
            res['result'] = tf.sigmoid(tf.nn.relu(args['a'] + args['b']))
            return res

    input_shapes = [PartialShape([1, 2, 3]),
                    PartialShape([1, 2, 3])]

    param1 = ov.opset8.parameter(input_shapes[0], dtype=np.float32)
    param2 = ov.opset8.parameter(input_shapes[1], dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    relu1 = ov.opset8.relu(add)
    sigm1 = ov.opset8.sigmoid(relu1)

    parameter_list = [param1, param2]
    model_ref = Model([sigm1], parameter_list, "test")
    return LayerModel(), model_ref


def create_keras_layer_input_dict_one_inp():
    class LayerModel(tf.keras.layers.Layer):

        def __init__(self):
            super(LayerModel, self).__init__()

        def call(self, args):
            res = {}
            res['result'] = tf.sigmoid(tf.nn.relu(args['args']))
            return res

    input_shapes = [PartialShape([1, 2, 3]),
                    PartialShape([1, 2, 3])]

    param1 = ov.opset8.parameter(input_shapes[0], dtype=np.float32)
    param2 = ov.opset8.parameter(input_shapes[1], dtype=np.float32)
    relu1 = ov.opset8.relu(param1)
    sigm1 = ov.opset8.sigmoid(relu1)
    parameter_list = [param1, param2]
    model_ref = Model([sigm1], parameter_list, "test")
    return LayerModel(), model_ref


def single_param_function_reference(shape, const_value):
    param1 = ov.opset8.parameter(shape, dtype=np.float32)
    const = ov.opset8.constant(const_value, dtype=np.float32)
    sigm = ov.opset8.sigmoid(param1)
    mul = ov.opset8.multiply(sigm, const)
    parameter_list = [param1]
    return Model([mul], parameter_list, "test")


def two_params_function_reference(shapes, const_value):
    param1 = ov.opset8.parameter(shapes[0], dtype=np.float32)
    param2 = ov.opset8.parameter(shapes[1], dtype=np.float32)
    const = ov.opset8.constant(const_value, dtype=np.float32)
    sigm = ov.opset8.sigmoid(param1)
    add = ov.opset8.add(sigm, param2)
    mul = ov.opset8.multiply(add, const)
    parameter_list = [param1, param2]
    return Model([mul], parameter_list, "test")


def two_params_function_reference_fp16_compressed(shapes, const_value):
    param1 = ov.opset8.parameter(shapes[0], dtype=np.float32)
    param2 = ov.opset8.parameter(shapes[1], dtype=np.float32)
    const_value = ov.opset8.constant(const_value, dtype=np.float16)
    const_decompress = ov.opset8.convert(const_value, np.float32)
    sigm = ov.opset8.sigmoid(param1)
    add = ov.opset8.add(sigm, param2)
    mul = ov.opset8.multiply(add, const_decompress)
    parameter_list = [param1, param2]
    return Model([mul], parameter_list, "test")


def create_keras_layer_with_example_input_1(tmp_dir):
    model, model_ref = create_keras_layer_input_list()
    example_input = (np.random.rand(1, 2, 3).astype(np.float32), np.random.rand(1, 2, 3).astype(np.float32))
    return model, model_ref, {'example_input': example_input}


def create_keras_layer_with_example_input_2(tmp_dir):
    model, model_ref = create_keras_layer_input_dict()
    example_input = {'a': np.random.rand(1, 2, 3).astype(np.float32), 'b': np.random.rand(1, 2, 3).astype(np.float32)}
    return model, model_ref, {'example_input': example_input}


def create_keras_layer_with_input_shapes_case1(tmp_dir):
    model, model_ref = create_keras_layer_input_list()
    return model, model_ref, {'example_input': (np.random.rand(1, 2, 3).astype(np.float32),
                                                np.random.rand(1, 2, 3).astype(np.float32))}


def create_keras_layer_with_input_shapes_case2(tmp_dir):
    model, model_ref = create_keras_layer_input_list()
    return model, model_ref, {'example_input': (np.random.rand(1, 2, 3).astype(np.float32),
                                                np.random.rand(1, 2, 3).astype(np.float32))}


def create_keras_layer_with_input_shapes_case3(tmp_dir):
    model, model_ref = create_keras_layer_input_dict_one_inp()
    return model, model_ref, {'example_input': {'args': np.random.rand(1, 2, 3).astype(np.float32)}}


def create_keras_layer_with_input_shapes_case4(tmp_dir):
    model, model_ref = create_keras_layer_input_list_one_inp()
    return model, model_ref, {'input': [1, 2, 3]}


def create_keras_layer_with_tf_function_call(tmp_dir):
    class LayerModel(tf.Module):
        def __init__(self):
            super(LayerModel, self).__init__()
            self.var1 = tf.Variable(5.0)

        @tf.function(input_signature=[tf.TensorSpec([1, 2], tf.float32), tf.TensorSpec([1, 2], tf.float32)])
        def __call__(self, input1, input2):
            sigm = tf.nn.sigmoid(input1) + input2
            return sigm * self.var1

    model = LayerModel()
    model_ref = two_params_function_reference([[1, 2], [1, 2]], [[5.0]])
    return model, model_ref, {'compress_to_fp16': False}


def create_keras_layer_with_tf_function_call_default_compressed_to_fp16(tmp_dir):
    class LayerModel(tf.Module):
        def __init__(self):
            super(LayerModel, self).__init__()
            self.var1 = tf.Variable(5.0)

        @tf.function(input_signature=[tf.TensorSpec([1, 2], tf.float32), tf.TensorSpec([1, 2], tf.float32)])
        def __call__(self, input1, input2):
            sigm = tf.nn.sigmoid(input1) + input2
            return sigm * self.var1

    model = LayerModel()
    model_ref = two_params_function_reference_fp16_compressed([[1, 2], [1, 2]], [[5.0]])
    return model, model_ref, {}


def create_keras_layer_with_compressed_constants(tmp_dir):
    import tensorflow as tf

    class LayerModel(tf.Module):
        def __init__(self):
            super(LayerModel, self).__init__()
            self.const = tf.constant([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], shape=[10], dtype=tf.float16)

        @tf.function(input_signature=[tf.TensorSpec([10], tf.float32)])
        def __call__(self, input_1):
            return input_1 + tf.cast(self.const, dtype=tf.float32)

    param_1 = ov.opset13.parameter([10], dtype=np.float32)
    const_1 = ov.opset13.constant(np.arange(10), dtype=np.float16)
    convert_1 = ov.opset13.convert(const_1, np.float32)
    add_1 = ov.opset13.add(param_1, convert_1)

    ov_model_ref = Model([add_1], [param_1], "test")
    fw_model = LayerModel()
    return fw_model, ov_model_ref, {}


def create_keras_layer_with_tf_function_call_no_signature(tmp_dir):
    class LayerModel(tf.Module):
        def __init__(self):
            super(LayerModel, self).__init__()
            self.var1 = tf.Variable(5.0)

        @tf.function()
        def __call__(self, input1, input2):
            sigm = tf.nn.sigmoid(input1) + input2
            return sigm * self.var1

    model = LayerModel()
    example_input = [np.random.rand(2, 3).astype(np.float32), np.random.rand(2, 3).astype(np.float32)]

    model_ref = two_params_function_reference([[2, 3], [2, 3]], [[5.0]])
    return model, model_ref, {'example_input': example_input, 'compress_to_fp16': False}


def create_keras_layer_with_tf_function_call_no_signature_single_input(tmp_dir):
    class LayerModel(tf.Module):
        def __init__(self):
            super(LayerModel, self).__init__()
            self.var1 = tf.Variable(5.0)

        @tf.function()
        def __call__(self, input1):
            sigm = tf.nn.sigmoid(input1)
            return sigm * self.var1

    model = LayerModel()
    example_input = np.random.rand(2, 3).astype(np.float32)

    model_ref = single_param_function_reference([2, 3], [[5.0]])
    return model, model_ref, {'example_input': example_input, 'compress_to_fp16': False}


def create_keras_layer_with_string_tensor(tmp_dir):
    class LayerModel(tf.Module):
        def __init__(self):
            super(LayerModel, self).__init__()
            self.var = tf.Variable("Text_1", dtype=tf.string)
            self.const = tf.constant("Text_2", dtype=tf.string)

        @tf.function(input_signature=[tf.TensorSpec([1], tf.float32), tf.TensorSpec([1], tf.float32)])
        def __call__(self, input1, input2):
            return input1 + input2, self.var, self.const

    model = LayerModel()

    param1 = ov.opset8.parameter([1], dtype=np.float32)
    param2 = ov.opset8.parameter([1], dtype=np.float32)
    add = ov.opset8.add(param1, param2)
    parameter_list = [param1, param2]
    model_ref = Model([add], parameter_list, "test")

    return model, model_ref, {}


def create_tf_model_three_inputs(shape=[1, 2, 3, 4], type=tf.float32):
    tf.compat.v1.reset_default_graph()

    with tf.compat.v1.Session() as sess:
        inp1 = tf.compat.v1.placeholder(type, shape, 'Input1')
        inp2 = tf.compat.v1.placeholder(type, shape, 'Input2')
        inp3 = tf.compat.v1.placeholder(type, shape, 'Input3')

        relu1 = tf.nn.relu(inp1, name='Relu1')
        relu2 = tf.nn.relu(inp2, name='Relu2')
        relu3 = tf.nn.relu(inp3, name='Relu3')

        add = relu1 + relu2 + relu3

        tf.compat.v1.global_variables_initializer()
        tf_net = sess.graph
    return tf_net


def create_ref_model_three_inputs(shape=[1, 2, 3, 4], dtype=np.float32):
    inp1 = ov.opset8.parameter(PartialShape(
        shape), name="Input1", dtype=dtype)
    inp2 = ov.opset8.parameter(PartialShape(
        shape), name="Input2", dtype=dtype)
    inp3 = ov.opset8.parameter(PartialShape(
        shape), name="Input3", dtype=dtype)

    relu1 = ov.opset8.relu(inp1)
    relu2 = ov.opset8.relu(inp2)
    relu3 = ov.opset8.relu(inp3)

    add1 = ov.opset8.add(relu1, relu2)
    add2 = ov.opset8.add(add1, relu3)

    parameter_list = [inp1, inp2, inp3]
    model = Model([add2], parameter_list, "test")
    return model


def create_tf_model_single_input(shape=[1, 2, 3, 4], type=tf.float32):
    tf.compat.v1.reset_default_graph()

    with tf.compat.v1.Session() as sess:
        inp = tf.compat.v1.placeholder(type, shape, 'Input')
        relu = tf.nn.relu(inp, name='Relu')
        output = tf.nn.sigmoid(relu, name='Sigmoid')

        tf.compat.v1.global_variables_initializer()
        tf_net = sess.graph

    return tf_net


def create_ref_model_single_input(shape=[1, 2, 3, 4], dtype=np.float32):
    inp = ov.opset8.parameter(PartialShape(
        shape), name="Input", dtype=dtype)
    relu = ov.opset8.relu(inp)
    sigm = ov.opset8.sigmoid(relu)
    parameter_list = [inp]
    model = Model([sigm], parameter_list, "test")
    return model


class TestMoConvertTF(CommonMOConvertTest):
    test_data = [
        # TF2
        'create_keras_model',
        'create_keras_layer',
        'create_tf_function',
        'create_tf_module',
        'create_tf_checkpoint',
        'create_keras_layer_dynamic',
        'create_tf_module_dynamic',
        'create_tf_stateful_partioned_call_net',
        'create_keras_layer_with_example_input_1',
        'create_keras_layer_with_example_input_2',
        'create_keras_layer_with_input_shapes_case1',
        'create_keras_layer_with_input_shapes_case2',
        'create_keras_layer_with_input_shapes_case3',
        'create_keras_layer_with_input_shapes_case4',
        'create_keras_layer_with_tf_function_call',
        'create_keras_layer_with_tf_function_call_default_compressed_to_fp16',
        'create_keras_layer_with_compressed_constants',
        'create_keras_layer_with_tf_function_call_no_signature',
        'create_keras_layer_with_tf_function_call_no_signature_single_input',
        'create_keras_layer_with_string_tensor',

        # TF1
        'create_tf_graph',
        'create_tf_graph_def',
        'create_tf1_wrap_function',
        'create_tf_session',
    ]

    @pytest.mark.parametrize("create_model", test_data)
    @pytest.mark.nightly
    @pytest.mark.precommit_tf_fe
    @pytest.mark.precommit
    def test_mo_import_from_memory_tf_fe(self, create_model, ie_device, precision, ir_version,
                                         temp_dir):
        fw_model, graph_ref, mo_params = eval(create_model)(temp_dir)

        test_params = {'input_model': fw_model}
        if mo_params is not None:
            test_params.update(mo_params)
        self._test_by_ref_graph(temp_dir, test_params, graph_ref, compare_tensor_names=False)

    @pytest.mark.nightly
    @pytest.mark.precommit
    @pytest.mark.skipif(
        condition=(sys.version_info[0], sys.version_info[1]) == (3, 12),
        reason='Ticket: 152216'
    )
    def test_unnamed_saved_model_dir(self, ie_device, precision, ir_version, temp_dir):
        saved_model_dir, graph_ref = create_tf_saved_model_dir(temp_dir)

        test_params = {'input_model': saved_model_dir}
        self._test_by_ref_graph(temp_dir, test_params, graph_ref, compare_tensor_names=False)

        test_params = {'input_model': saved_model_dir}
        self._test_by_ref_graph(temp_dir, test_params, graph_ref, compare_tensor_names=False)

    def test_zero_copy(self, ie_device, precision, ir_version, temp_dir):
        from openvino.tools.ovc import convert_model
        from openvino import compile_model
        class LayerModel(tf.Module):
            def __init__(self):
                super(LayerModel, self).__init__()
                self.var1 = tf.Variable([7., 5., 6.], name='var1')
                self.var2 = tf.Variable([5., 7., 3.], name='var2')

            @tf.function
            def sub_function(self, input):
                return input * self.var1 + self.var2

            @tf.function()
            def __call__(self, input):
                return self.sub_function(input)

        # Create TF model with variables
        keras_model = LayerModel()
        test_input = np.array(7.).astype(np.float32)

        # Convert model to OV
        ov_model = convert_model(keras_model, input=[1], share_weights=True)
        cmp_model = compile_model(ov_model)

        # Check model inference
        ov_infer1 = cmp_model(test_input, ie_device)
        fw_infer1 = keras_model(test_input).numpy()

        assert np.array_equal(ov_infer1['Identity:0'], fw_infer1)
        assert np.array_equal(ov_infer1['Identity:0'], [54., 42., 45.])

        # Change value of variables in original model
        for val in keras_model.variables:
            arr = val.value().__array__()
            arr[0] = 0
            arr[1] = 1
            arr[2] = 2

        # Check model inference
        cmp_model = compile_model(ov_model)
        ov_infer2 = cmp_model(test_input)
        fw_infer2 = keras_model(test_input).numpy()

        assert np.array_equal(ov_infer2['Identity:0'], fw_infer2)
        assert np.array_equal(ov_infer2['Identity:0'], [0., 8., 16.])

    def test_turn_off_sharing(self, ie_device, precision, ir_version, temp_dir):
        from openvino.tools.ovc import convert_model
        from openvino import compile_model
        class LayerModel(tf.Module):
            def __init__(self):
                super(LayerModel, self).__init__()
                self.var1 = tf.Variable([7., 5., 6.], name='var1')
                self.var2 = tf.Variable([5., 7., 3.], name='var2')

            @tf.function
            def sub_function(self, input):
                return input * self.var1 + self.var2

            @tf.function()
            def __call__(self, input):
                return self.sub_function(input)

        # Create TF model with variables
        keras_model = LayerModel()
        test_input = np.array(7.).astype(np.float32)

        # Convert model to OV
        ov_model = convert_model(keras_model, input=[1], share_weights=False)
        cmp_model = compile_model(ov_model)

        # Check model inference
        ov_infer1 = cmp_model(test_input, ie_device)
        fw_infer1 = keras_model(test_input).numpy()

        assert np.array_equal(ov_infer1['Identity:0'], fw_infer1)
        assert np.array_equal(ov_infer1['Identity:0'], [54., 42., 45.])

        # Change value of variables in original model
        for val in keras_model.variables:
            arr = val.value().__array__()
            arr[0] = 0
            arr[1] = 1
            arr[2] = 2

        # Check model inference
        ov_infer2 = cmp_model(test_input)
        fw_infer2 = keras_model(test_input).numpy()

        # Check model inference calculated with old constant values
        assert not np.array_equal(ov_infer2['Identity:0'], fw_infer2)
        assert np.array_equal(ov_infer2['Identity:0'], [54., 42., 45.])

    def test_memory_loss(self, ie_device, precision, ir_version, temp_dir):
        # This test checks that the memory allocated for constants
        # is not lost after returning the model from convert_model() method.
        tf.compat.v1.reset_default_graph()

        from openvino.tools.ovc import convert_model
        from openvino import compile_model
        import gc

        with tf.compat.v1.Session() as sess:
            inp1 = tf.compat.v1.placeholder(tf.float32, [3], 'Input')
            const = tf.constant([0.5, 2.3, 7.8], dtype=tf.float32)
            res = inp1 + const

            tf.compat.v1.global_variables_initializer()
            tf_graph = sess.graph  # tf.Graph

        if precision == 'FP32':
            eps = 1e-4
        else:
            eps = 5e-2

        test_input = np.array([2.1, 7.3, 4.6]).astype(np.float32)

        # Convert model to OV
        ov_model = convert_model(tf_graph)
        cmp_model = compile_model(ov_model)

        # Check model inference
        ov_infer1 = cmp_model(test_input, ie_device)

        feed_dict = {"Input:0": test_input}
        with tf.compat.v1.Session(graph=tf_graph) as sess:
            fw_infer1 = sess.run('add:0', feed_dict=feed_dict)

        assert CommonLayerTest().compare_ie_results_with_framework(ov_infer1, {"add:0": fw_infer1}, eps)
        assert CommonLayerTest().compare_ie_results_with_framework(ov_infer1, {"add:0": [2.6, 9.6, 12.4]}, eps)

        # run Garbage collector to ensure, that values from tf.constant are copied to ov.Const and
        # we do not lose allocated memory.
        gc.collect()

        # Check model inference
        cmp_model = compile_model(ov_model)
        ov_infer2 = cmp_model(test_input, ie_device)

        feed_dict = {"Input:0": test_input}
        with tf.compat.v1.Session(graph=tf_graph) as sess:
            fw_infer2 = sess.run('add:0', feed_dict=feed_dict)

        assert CommonLayerTest().compare_ie_results_with_framework(ov_infer2, {"add:0": fw_infer2}, eps)
        assert CommonLayerTest().compare_ie_results_with_framework(ov_infer1, {"add:0": [2.6, 9.6, 12.4]}, eps)

    def test_scalar(self, ie_device, precision, ir_version, temp_dir):
        tf.compat.v1.reset_default_graph()

        from openvino.tools.ovc import convert_model
        from openvino import compile_model

        class LayerModel(tf.Module):
            def __init__(self):
                super(LayerModel, self).__init__()
                self.var1 = tf.Variable(-0.5, name='var1')
                self.var2 = tf.Variable(1.7, name='var2')

            @tf.function
            def sub_function(self, input):
                return input + self.var1 + self.var2

            @tf.function(input_signature=[tf.TensorSpec([], tf.float32)])
            def __call__(self, input):
                return self.sub_function(input)

        if precision == 'FP32':
            eps = 1e-4
        else:
            eps = 5e-2

        test_input = np.array(2.0).astype(np.float32)

        # Convert model to OV
        fw_model = LayerModel()
        ov_model = convert_model(fw_model)
        cmp_model = compile_model(ov_model)

        # Check model inference
        ov_infer = cmp_model(test_input, ie_device)
        fw_infer = fw_model(test_input).numpy()

        assert CommonLayerTest().compare_ie_results_with_framework(ov_infer, {"Identity:0": fw_infer}, eps)
        assert CommonLayerTest().compare_ie_results_with_framework(ov_infer, {"Identity:0": 3.2}, eps)

    def test_unnamed_variable(self, ie_device, precision, ir_version, temp_dir):
        tf.compat.v1.reset_default_graph()

        from openvino.tools.ovc import convert_model
        from openvino import compile_model

        class LayerModel(tf.Module):
            def __init__(self):
                super(LayerModel, self).__init__()
                self.var1 = tf.Variable([1.6, 3.8])
                self.var2 = tf.Variable(-0.5)

            @tf.function
            def sub_function(self, input):
                return (input + self.var1) * self.var2

            @tf.function(input_signature=[tf.TensorSpec([2], tf.float32)])
            def __call__(self, input):
                return self.sub_function(input)

        if precision == 'FP32':
            eps = 1e-4
        else:
            eps = 5e-2

        test_input = np.array([2.0, 5.0]).astype(np.float32)

        # Convert model to OV
        fw_model = LayerModel()
        ov_model = convert_model(fw_model)
        cmp_model = compile_model(ov_model)

        # Check model inference
        ov_infer = cmp_model(test_input, ie_device)
        fw_infer = fw_model(test_input).numpy()

        assert CommonLayerTest().compare_ie_results_with_framework(ov_infer, {"Identity:0": fw_infer}, eps)
        assert CommonLayerTest().compare_ie_results_with_framework(ov_infer, {"Identity:0": [-1.8, -4.4]}, eps)


class TFGraphDefNames(unittest.TestCase):
    def test_graph_def_names(self):
        from openvino.tools.ovc import convert_model

        tf_model, model_ref, _ = create_tf_graph_def(None)
        ov_model = convert_model(tf_model)

        input_list = []
        with tf.Graph().as_default() as graph:
            tf.import_graph_def(tf_model, name='')
            for op in graph.get_operations():
                if op.type == "Placeholder":
                    input_list.append(op.name + ":0")

        for input in input_list:
            found = False
            for ov_input in ov_model.inputs:
                if input in ov_input.get_names():
                    found = True
            assert found, "Could not found input {} in resulting model.".format(input)


class TFConvertTest(unittest.TestCase):
    @pytest.mark.nightly
    @pytest.mark.precommit
    def test_tf_function_no_signature(self):
        from openvino.tools.ovc import convert_model

        @tf.function()
        def function(x1, x2):
            y = tf.nn.sigmoid(tf.nn.relu(x1 + x2))
            return y

        with self.assertRaisesRegex(Exception, ".*Please provide 'example_input'.*"):
            convert_model(function)


class TestTFLoadByModel(unittest.TestCase):
    def test_load_by_model_tf_graph_iterator(self):
        def simple_tf_model():
            tf.compat.v1.reset_default_graph()

            with tf.compat.v1.Session() as sess:
                inp = tf.compat.v1.placeholder(tf.float32, [1, 2, 3], "Input")
                _ = tf.nn.sigmoid(inp, name="Sigmoid")

                tf.compat.v1.global_variables_initializer()
                tf_net = sess.graph
            return tf_net

        from openvino.frontend.tensorflow.graph_iterator import GraphIteratorTFGraph
        from openvino.frontend import FrontEndManager
        model = GraphIteratorTFGraph(simple_tf_model(), True)
        fem = FrontEndManager()
        fe = fem.load_by_model(model)
        assert fe is not None
        assert fe.get_name() == "tf"


class TestTFConvertRaises(unittest.TestCase):
    def test_incorrect_inputs_1(self):
        from openvino.tools.ovc import convert_model
        tf_model, _, _ = create_keras_model('')

        with self.assertRaisesRegex(Exception, ".*No node with name.*"):
            convert_model(tf_model, input='Input1[1, 2, 3]')

    def test_incorrect_inputs_2(self):
        from openvino.tools.ovc import convert_model
        tf_model, _, _ = create_keras_model('')

        # check that it accepts specified names as is without parsing into 2 different inputs
        with self.assertRaisesRegex(Exception, 'No node with name Input1\[1, 2, 3\],Input2\[1, 2, 3\]'):
            convert_model(tf_model, input='Input1[1, 2, 3],Input2[1, 2, 3]')


class TestTFConversionParams(CommonMOConvertTest):
    test_data = [
        {'params_test': {
            'input': [tf.shape(tf.zeros((2, 3, 4))), tf.zeros((2, 3, 4)).shape, tf.TensorShape((2, 3, 4))]},
         'fw_model': {
            'create_model': 'create_tf_model_three_inputs',
             'params': [[1, 2, 3, 4]]},
         'ref_model': {
             'create_model': 'create_ref_model_three_inputs',
             'params': [[2, 3, 4]]}},
        {'params_test': {'input': [tf.float32, tf.float32, tf.float32]},
         'fw_model': {
            'create_model': 'create_tf_model_three_inputs',
            'params': [[2, 3], tf.int32]},
         'ref_model': {
            'create_model': 'create_ref_model_three_inputs',
            'params': [[2, 3], np.float32]}},
        {'params_test': {'input': tf.shape(tf.zeros((5, 8, 2)))},
         'fw_model': {
            'create_model': 'create_tf_model_single_input',
            'params': []},
          'ref_model': {
            'create_model': 'create_ref_model_single_input',
            'params': [[5, 8, 2]]}},
        {'params_test': {'input': tf.zeros((9, 2)).shape},
         'fw_model': {
            'create_model': 'create_tf_model_single_input',
            'params': []},
         'ref_model': {
            'create_model': 'create_ref_model_single_input',
            'params': [[9, 2]]}},
        {'params_test': {'input': tf.TensorShape((4, 8, 3))},
         'fw_model': {
            'create_model': 'create_tf_model_single_input',
            'params': []},
         'ref_model': {
            'create_model': 'create_ref_model_single_input',
            'params': [[4, 8, 3]]}},
        {'params_test': {'input': tf.int32},
         'fw_model': {
            'create_model': 'create_tf_model_single_input',
            'params': []},
         'ref_model': {
            'create_model': 'create_ref_model_single_input',
            'params': [[1, 2, 3, 4], np.int32]}},
    ]

    @pytest.mark.parametrize("params", test_data)
    @pytest.mark.nightly
    def test_mo_convert_tf_model(self, params, ie_device, precision, ir_version,
                                 temp_dir):
        fw_model_dict = params['fw_model']
        ref_model_dict = params['ref_model']
        test_params = params['params_test']

        ref_model = eval(ref_model_dict['create_model'])(*ref_model_dict['params'])
        fw_model = eval(fw_model_dict['create_model'])(*fw_model_dict['params'])
        test_params.update({'input_model': fw_model})
        self._test_by_ref_graph(temp_dir, test_params, ref_model, compare_tensor_names=False)


class TestOutputTensorName(unittest.TestCase):
    @staticmethod
    def create_keras_model_with_named_output():
        tf.keras.backend.clear_session()
        tf.compat.v1.reset_default_graph()

        input_names = ["Input1", "Input2"]
        input_shape = [1, 2, 3]

        x1 = tf.keras.Input(shape=input_shape, name=input_names[0])
        x2 = tf.keras.Input(shape=input_shape, name=input_names[1])
        relu = tf.keras.layers.Activation('relu')(x1 + x2)
        sigmoid = tf.keras.layers.Activation('sigmoid')(relu)
        keras_net = tf.keras.Model(inputs=[x1, x2], outputs=[{"output": sigmoid}])
        keras_net.output_names[0] = "output"

        return keras_net

    @pytest.mark.nightly
    @pytest.mark.precommit
    def test_tf1_from_file_single_tensor_name(self):
        tf.keras.backend.clear_session()
        tf.compat.v1.reset_default_graph()

        Path(constants.out_path).mkdir(parents=True, exist_ok=True)
        tmp_dir = tempfile.TemporaryDirectory(dir=constants.out_path).name

        from openvino import convert_model

        model, _, _ = create_tf_graph_def(None)
        path = save_to_pb(model, tmp_dir)

        ov_model = convert_model(path)
        out_tensors = ov_model.outputs[0].get_names()

        assert len(out_tensors) == 1
        assert list(out_tensors)[0] == "Sigmoid:0"

        out_tensor_name = list(out_tensors)[0]

        ov_model = convert_model(path, output=out_tensor_name)
        out_tensors = ov_model.outputs[0].get_names()

        assert len(out_tensors) == 1
        assert list(out_tensors)[0] == "Sigmoid:0"

    @pytest.mark.nightly
    @pytest.mark.precommit
    def test_tf1_from_memory_single_tensor_name(self):
        tf.keras.backend.clear_session()
        tf.compat.v1.reset_default_graph()
        from openvino.tools.ovc import convert_model

        model, _, _ = create_tf_graph_def(None)

        ov_model = convert_model(model)
        out_tensors = ov_model.outputs[0].get_names()

        assert len(out_tensors) == 1
        assert list(out_tensors)[0] == "Sigmoid:0"

        out_tensor_name = list(out_tensors)[0]

        ov_model = convert_model(model, output=out_tensor_name)
        out_tensors = ov_model.outputs[0].get_names()

        assert len(out_tensors) == 1
        assert list(out_tensors)[0] == "Sigmoid:0"

    @pytest.mark.nightly
    @pytest.mark.precommit
    @pytest.mark.skipif(
        condition=(sys.version_info[0], sys.version_info[1]) == (3, 12),
        reason='Ticket: 152216'
    )
    def test_tf2_from_file_single_tensor_name(self):
        tf.keras.backend.clear_session()
        tf.compat.v1.reset_default_graph()
        Path(constants.out_path).mkdir(parents=True, exist_ok=True)
        tmp_dir = tempfile.TemporaryDirectory(dir=constants.out_path).name
        model_path = tmp_dir + os.sep + "model"

        from openvino import convert_model

        model = TestOutputTensorName.create_keras_model_with_named_output()
        tf.saved_model.save(model, model_path)

        ov_model = convert_model(model_path)
        for output in ov_model.outputs:
            out_tensors = output.get_names()

            assert len(out_tensors) == 1
            out_tensor = list(out_tensors)[0]
            assert out_tensor == "output"

    @pytest.mark.nightly
    @pytest.mark.precommit
    def test_tf2_from_memory_single_tensor_name(self):
        tf.keras.backend.clear_session()
        tf.compat.v1.reset_default_graph()
        from openvino.tools.ovc import convert_model

        model = TestOutputTensorName.create_keras_model_with_named_output()

        ov_model = convert_model(model)
        for output in ov_model.outputs:
            out_tensors = output.get_names()

            assert len(out_tensors) == 1
            out_tensor = list(out_tensors)[0]
            assert out_tensor == "output"

    @pytest.mark.nightly
    @pytest.mark.precommit
    def test_tf1_output_with_identity(self):
        tf.keras.backend.clear_session()
        tf.compat.v1.reset_default_graph()
        from openvino.tools.ovc import convert_model

        with tf.compat.v1.Session() as sess:
            x = tf.compat.v1.placeholder(tf.float32, [2], 'x')
            y = tf.compat.v1.placeholder(tf.float32, [2], 'y')
            add = tf.add(x, y, name="add")
            result1 = tf.identity(add, name="result1")
            result2 = tf.identity(add, name="result2")

            tf.compat.v1.global_variables_initializer()
            model = sess.graph_def

        ov_model = convert_model(model)

        assert ov_model.outputs[0].get_names() == {"result1:0", "result2:0", "add:0"}
        assert ov_model.outputs[1].get_names() == {"result1:0", "result2:0", "add:0"}


class TestInputTensorName(unittest.TestCase):
    @pytest.mark.nightly
    @pytest.mark.precommit
    def test_tf1_from_file_single_input_name(self):
        tf.keras.backend.clear_session()
        tf.compat.v1.reset_default_graph()
        Path(constants.out_path).mkdir(parents=True, exist_ok=True)
        tmp_dir = tempfile.TemporaryDirectory(dir=constants.out_path).name
        from openvino import convert_model

        model, _, _ = create_tf_graph_def(None)
        path = save_to_pb(model, tmp_dir)

        ov_model = convert_model(path)

        ref_inputs = ["Input:0", "Input_1:0"]
        for idx, output in enumerate(ov_model.inputs):
            tensors = output.get_names()

            assert len(tensors) == 1
            out_tensor = list(tensors)[0]
            assert out_tensor == ref_inputs[idx]

        ov_model = convert_model(path, input=["Input:0", "Input_1:0"])
        for idx, output in enumerate(ov_model.inputs):
            tensors = output.get_names()

            assert len(tensors) == 1
            out_tensor = list(tensors)[0]
            assert out_tensor == ref_inputs[idx]

    @pytest.mark.nightly
    @pytest.mark.precommit
    def test_tf1_from_memory_single_input_name(self):
        tf.keras.backend.clear_session()
        tf.compat.v1.reset_default_graph()
        from openvino import convert_model

        model, _, _ = create_tf_graph_def(None)

        ov_model = convert_model(model)

        ref_inputs = ["Input:0", "Input_1:0"]
        for idx, output in enumerate(ov_model.inputs):
            tensors = output.get_names()

            assert len(tensors) == 1
            out_tensor = list(tensors)[0]
            assert out_tensor == ref_inputs[idx]

        ov_model = convert_model(model, input=["Input:0", "Input_1:0"])
        for idx, output in enumerate(ov_model.inputs):
            tensors = output.get_names()

            assert len(tensors) == 1
            out_tensor = list(tensors)[0]
            assert out_tensor == ref_inputs[idx]

    @pytest.mark.nightly
    @pytest.mark.precommit
    def test_tf1_input_with_identity(self):
        tf.keras.backend.clear_session()
        tf.compat.v1.reset_default_graph()
        from openvino.tools.ovc import convert_model

        with tf.compat.v1.Session() as sess:
            x = tf.compat.v1.placeholder(tf.float32, [2], 'x')
            y = tf.compat.v1.placeholder(tf.float32, [2], 'y')
            input1 = tf.identity(x, name="x_identity")
            input2 = tf.identity(y, name="y_identity")
            add = tf.add(input1, input2, name="add")

            tf.compat.v1.global_variables_initializer()
            model = sess.graph_def

        ov_model = convert_model(model)

        assert ov_model.inputs[0].get_names() == {"x:0"}
        assert ov_model.inputs[1].get_names() == {"y:0"}


class TestUnicodePathsTF(unittest.TestCase):
    @pytest.mark.nightly
    @pytest.mark.precommit
    def test_unicode_paths(self):
        test_directory = os.path.dirname(os.path.realpath(__file__))
        with tempfile.TemporaryDirectory(dir=test_directory, prefix=r"晚安_путь_к_файлу") as temp_dir:
            model, model_ref, _ = create_tf_graph_def(None)

            try:
                model_path = save_to_pb(model, temp_dir)
            except:
                return

            assert os.path.exists(model_path), "Could not create a directory with unicode path."

            from openvino import convert_model, save_model, Core
            res_model = convert_model(model_path)
            flag, msg = compare_functions(res_model, model_ref, False)
            assert flag, msg

            save_model(res_model, model_path + ".xml")
            res_model_after_saving = Core().read_model(model_path + ".xml")
            flag, msg = compare_functions(res_model_after_saving, model_ref, False)
            assert flag, msg

            from openvino.frontend import FrontEndManager
            fm = FrontEndManager()
            fe = fm.load_by_framework("tf")

            assert fe.supported(model_path)

            del res_model_after_saving
