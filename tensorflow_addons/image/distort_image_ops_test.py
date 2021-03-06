# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may noa use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Tests for python distort_image_ops."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np

import tensorflow as tf
from tensorflow_addons.image import distort_image_ops

from tensorflow_addons.utils import test_utils


@test_utils.run_all_in_graph_and_eager_modes
class AdjustHueInYiqTest(tf.test.TestCase):
    def _adjust_hue_in_yiq_np(self, x_np, delta_h):
        """Rotate hue in YIQ space.

        Mathematically we first convert rgb color to yiq space, rotate the hue
        degrees, and then convert back to rgb.

        Args:
          x_np: input x with last dimension = 3.
          delta_h: degree of hue rotation, in radians.

        Returns:
          Adjusted y with the same shape as x_np.
        """
        self.assertEqual(x_np.shape[-1], 3)
        x_v = x_np.reshape([-1, 3])
        y_v = np.ndarray(x_v.shape, dtype=x_v.dtype)
        u = np.cos(delta_h)
        w = np.sin(delta_h)
        # Projection matrix from RGB to YIQ. Numbers from wikipedia
        # https://en.wikipedia.org/wiki/YIQ
        tyiq = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322],
                         [0.211, -0.523, 0.312]])
        y_v = np.dot(x_v, tyiq.T)
        # Hue rotation matrix in YIQ space.
        hue_rotation = np.array([[1.0, 0.0, 0.0], [0.0, u, -w], [0.0, w, u]])
        y_v = np.dot(y_v, hue_rotation.T)
        # Projecting back to RGB space.
        y_v = np.dot(y_v, np.linalg.inv(tyiq).T)
        return y_v.reshape(x_np.shape)

    def _adjust_hue_in_yiq_tf(self, x_np, delta_h):
        x = tf.constant(x_np)
        y = distort_image_ops.adjust_hsv_in_yiq(x, delta_h, 1, 1)
        return y

    def test_adjust_random_hue_in_yiq(self):
        x_shapes = [
            [2, 2, 3],
            [4, 2, 3],
            [2, 4, 3],
            [2, 5, 3],
            [1000, 1, 3],
        ]
        test_styles = [
            "all_random",
            "rg_same",
            "rb_same",
            "gb_same",
            "rgb_same",
        ]
        for x_shape in x_shapes:
            for test_style in test_styles:
                x_np = np.random.rand(*x_shape) * 255.
                delta_h = (np.random.rand() * 2.0 - 1.0) * np.pi
                if test_style == "all_random":
                    pass
                elif test_style == "rg_same":
                    x_np[..., 1] = x_np[..., 0]
                elif test_style == "rb_same":
                    x_np[..., 2] = x_np[..., 0]
                elif test_style == "gb_same":
                    x_np[..., 2] = x_np[..., 1]
                elif test_style == "rgb_same":
                    x_np[..., 1] = x_np[..., 0]
                    x_np[..., 2] = x_np[..., 0]
                else:
                    raise AssertionError(
                        "Invalid test style: %s" % (test_style))
                y_np = self._adjust_hue_in_yiq_np(x_np, delta_h)
                y_tf = self._adjust_hue_in_yiq_tf(x_np, delta_h)
                self.assertAllClose(y_tf, y_np, rtol=2e-4, atol=1e-4)

    def test_invalid_rank(self):
        msg = "Shape must be at least rank 3 but is rank 2"
        x_np = np.random.rand(2, 3) * 255.
        delta_h = np.random.rand() * 2.0 - 1.0
        with self.assertRaisesRegex(ValueError, msg):
            self.evaluate(self._adjust_hue_in_yiq_tf(x_np, delta_h))

    def test_invalid_channels(self):
        msg = "Dimension must be 3 but is 4"
        x_np = np.random.rand(4, 2, 4) * 255.
        delta_h = np.random.rand() * 2.0 - 1.0
        with self.assertRaisesRegex(ValueError, msg):
            self.evaluate(self._adjust_hue_in_yiq_tf(x_np, delta_h))

    def test_adjust_hsv_in_yiq_unknown_shape(self):
        fn = distort_image_ops.adjust_hsv_in_yiq.get_concrete_function(
            tf.TensorSpec(shape=None, dtype=tf.float64))
        for shape in (2, 3, 3), (4, 2, 3, 3):
            image_np = np.random.rand(*shape) * 255.
            image_tf = tf.constant(image_np)
            self.assertAllClose(
                self._adjust_hue_in_yiq_np(image_np, 0),
                self.evaluate(fn(image_tf)),
                rtol=2e-4,
                atol=1e-4)

    def test_random_hsv_in_yiq_unknown_shape(self):
        fn = distort_image_ops.random_hsv_in_yiq.get_concrete_function(
            tf.TensorSpec(shape=None, dtype=tf.float32))
        for shape in (2, 3, 3), (4, 2, 3, 3):
            image_tf = tf.ones(shape)
            self.assertAllEqual(fn(image_tf), fn(image_tf))


@test_utils.run_all_in_graph_and_eager_modes
class AdjustValueInYiqTest(tf.test.TestCase):
    def _adjust_value_in_yiq_np(self, x_np, scale):
        return x_np * scale

    def _adjust_value_in_yiq_tf(self, x_np, scale):
        x = tf.constant(x_np)
        y = distort_image_ops.adjust_hsv_in_yiq(x, 0, 1, scale)
        return y

    def test_adjust_random_value_in_yiq(self):
        x_shapes = [
            [2, 2, 3],
            [4, 2, 3],
            [2, 4, 3],
            [2, 5, 3],
            [1000, 1, 3],
        ]
        test_styles = [
            "all_random",
            "rg_same",
            "rb_same",
            "gb_same",
            "rgb_same",
        ]
        for x_shape in x_shapes:
            for test_style in test_styles:
                x_np = np.random.rand(*x_shape) * 255.
                scale = np.random.rand() * 2.0 - 1.0
                if test_style == "all_random":
                    pass
                elif test_style == "rg_same":
                    x_np[..., 1] = x_np[..., 0]
                elif test_style == "rb_same":
                    x_np[..., 2] = x_np[..., 0]
                elif test_style == "gb_same":
                    x_np[..., 2] = x_np[..., 1]
                elif test_style == "rgb_same":
                    x_np[..., 1] = x_np[..., 0]
                    x_np[..., 2] = x_np[..., 0]
                else:
                    raise AssertionError(
                        "Invalid test style: %s" % (test_style))
                y_np = self._adjust_value_in_yiq_np(x_np, scale)
                y_tf = self._adjust_value_in_yiq_tf(x_np, scale)
                self.assertAllClose(y_tf, y_np, rtol=2e-4, atol=1e-4)

    def test_invalid_rank(self):
        msg = "Shape must be at least rank 3 but is rank 2"
        x_np = np.random.rand(2, 3) * 255.
        scale = np.random.rand() * 2.0 - 1.0
        with self.assertRaisesRegex(ValueError, msg):
            self.evaluate(self._adjust_value_in_yiq_tf(x_np, scale))

    def test_invalid_channels(self):
        msg = "Dimension must be 3 but is 4"
        x_np = np.random.rand(4, 2, 4) * 255.
        scale = np.random.rand() * 2.0 - 1.0
        with self.assertRaisesRegex(ValueError, msg):
            self.evaluate(self._adjust_value_in_yiq_tf(x_np, scale))


@test_utils.run_all_in_graph_and_eager_modes
class AdjustSaturationInYiqTest(tf.test.TestCase):
    def _adjust_saturation_in_yiq_tf(self, x_np, scale):
        x = tf.constant(x_np)
        y = distort_image_ops.adjust_hsv_in_yiq(x, 0, scale, 1)
        return y

    def _adjust_saturation_in_yiq_np(self, x_np, scale):
        """Adjust saturation using linear interpolation."""
        rgb_weights = np.array([0.299, 0.587, 0.114])
        gray = np.sum(x_np * rgb_weights, axis=-1, keepdims=True)
        y_v = x_np * scale + gray * (1 - scale)
        return y_v

    def test_adjust_random_saturation_in_yiq(self):
        x_shapes = [
            [2, 2, 3],
            [4, 2, 3],
            [2, 4, 3],
            [2, 5, 3],
            [1000, 1, 3],
        ]
        test_styles = [
            "all_random",
            "rg_same",
            "rb_same",
            "gb_same",
            "rgb_same",
        ]
        for x_shape in x_shapes:
            for test_style in test_styles:
                x_np = np.random.rand(*x_shape) * 255.
                scale = np.random.rand() * 2.0 - 1.0
                if test_style == "all_random":
                    pass
                elif test_style == "rg_same":
                    x_np[..., 1] = x_np[..., 0]
                elif test_style == "rb_same":
                    x_np[..., 2] = x_np[..., 0]
                elif test_style == "gb_same":
                    x_np[..., 2] = x_np[..., 1]
                elif test_style == "rgb_same":
                    x_np[..., 1] = x_np[..., 0]
                    x_np[..., 2] = x_np[..., 0]
                else:
                    raise AssertionError(
                        "Invalid test style: %s" % (test_style))
                y_baseline = self._adjust_saturation_in_yiq_np(x_np, scale)
                y_tf = self._adjust_saturation_in_yiq_tf(x_np, scale)
                self.assertAllClose(y_tf, y_baseline, rtol=2e-4, atol=1e-4)

    def test_invalid_rank(self):
        msg = "Shape must be at least rank 3 but is rank 2"
        x_np = np.random.rand(2, 3) * 255.
        scale = np.random.rand() * 2.0 - 1.0
        with self.assertRaisesRegex(ValueError, msg):
            self.evaluate(self._adjust_saturation_in_yiq_tf(x_np, scale))

    def test_invalid_channels(self):
        msg = "Dimension must be 3 but is 4"
        x_np = np.random.rand(4, 2, 4) * 255.
        scale = np.random.rand() * 2.0 - 1.0
        with self.assertRaisesRegex(ValueError, msg):
            self.evaluate(self._adjust_saturation_in_yiq_tf(x_np, scale))


# TODO: get rid of sessions
class AdjustHueInYiqBenchmark(tf.test.Benchmark):
    def _benchmark_adjust_hue_in_yiq(self, device, cpu_count):
        image_shape = [299, 299, 3]
        burn_iters = 100
        benchmark_iters = 1000
        config = tf.compat.v1.ConfigProto()
        tag = device + "_%s" % (cpu_count if cpu_count is not None else "all")
        if cpu_count is not None:
            config.inter_op_parallelism_threads = 1
            config.intra_op_parallelism_threads = cpu_count
        with self.cached_session("", graph=tf.Graph(), config=config) as sess:
            with tf.device(device):
                inputs = tf.Variable(
                    tf.random.uniform(image_shape, dtype=tf.dtypes.float32) *
                    255,
                    trainable=False,
                    dtype=tf.dtypes.float32)
                delta = tf.constant(0.1, dtype=tf.dtypes.float32)
                outputs = distort_image_ops.adjust_hsv_in_yiq(
                    inputs, delta, 1, 1)
                run_op = tf.group(outputs)
                sess.run(tf.compat.v1.global_variables_initializer())
                benchmark_values = self.run_op_benchmark(
                    sess,
                    run_op,
                    burn_iters=burn_iters,
                    min_iters=benchmark_iters,
                    name="benchmarkAdjustSaturationInYiq_299_299_3_%s" % (tag))
        print("benchmarkAdjustSaturationInYiq_299_299_3_%s step_time: %.2f us"
              % (tag, benchmark_values['wall_time'] * 1e6))

    def benchmark_adjust_hue_in_yiqCpu1(self):
        self._benchmark_adjust_hue_in_yiq("/cpu:0", 1)

    def benchmark_adjust_hue_in_yiqCpuAll(self):
        self._benchmark_adjust_hue_in_yiq("/cpu:0", None)

    def benchmark_adjust_hue_in_yiq_gpu_all(self):
        self._benchmark_adjust_hue_in_yiq(tf.test.gpu_device_name(), None)


# TODO: get rid of sessions
class AdjustSaturationInYiqBenchmark(tf.test.Benchmark):
    def _benchmark_adjust_saturation_in_yiq(self, device, cpu_count):
        image_shape = [299, 299, 3]
        burn_iters = 100
        benchmark_iters = 1000
        config = tf.compat.v1.ConfigProto()
        tag = device + "_%s" % (cpu_count if cpu_count is not None else "all")
        if cpu_count is not None:
            config.inter_op_parallelism_threads = 1
            config.intra_op_parallelism_threads = cpu_count
        with self.cached_session("", graph=tf.Graph(), config=config) as sess:
            with tf.device(device):
                inputs = tf.Variable(
                    tf.random.uniform(image_shape, dtype=tf.dtypes.float32) *
                    255,
                    trainable=False,
                    dtype=tf.dtypes.float32)
                scale = tf.constant(0.1, dtype=tf.dtypes.float32)
                outputs = distort_image_ops.adjust_hsv_in_yiq(
                    inputs, 0, scale, 1)
                run_op = tf.group(outputs)
                sess.run(tf.compat.v1.global_variables_initializer())
                benchmark_values = self.run_op_benchmark(
                    sess,
                    run_op,
                    burn_iters=burn_iters,
                    min_iters=benchmark_iters,
                    name="benchmarkAdjustSaturationInYiq_299_299_3_%s" % (tag))
        print("benchmarkAdjustSaturationInYiq_299_299_3_%s step_time: %.2f us"
              % (tag, benchmark_values['wall_time'] * 1e6))

    def benchmark_adjust_saturation_in_yiq_cpu1(self):
        self._benchmark_adjust_saturation_in_yiq("/cpu:0", 1)

    def benchmark_adjust_saturation_in_yiq_cpu_all(self):
        self._benchmark_adjust_saturation_in_yiq("/cpu:0", None)

    def benchmark_adjust_saturation_in_yiq_gpu_all(self):
        self._benchmark_adjust_saturation_in_yiq(tf.test.gpu_device_name(),
                                                 None)


if __name__ == "__main__":
    tf.test.main()
