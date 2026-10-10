import math
import unittest

from local_lab.metrics import throughput_bytes_per_second, udp_sequence_metrics


class MetricsTests(unittest.TestCase):
    def test_udp_sequence_metrics(self):
        result = udp_sequence_metrics([0, 1, 2, 3], [0, 2, 8])
        self.assertEqual(result["lost"], 2)
        self.assertEqual(result["received"], 2)
        self.assertEqual(result["unexpected"], 1)
        self.assertEqual(result["loss_percent"], 50.0)

    def test_throughput(self):
        self.assertEqual(throughput_bytes_per_second(1000, 2), 500)
        self.assertTrue(math.isinf(throughput_bytes_per_second(1, 0)))
        with self.assertRaises(ValueError): throughput_bytes_per_second(-1, 1)


if __name__ == "__main__": unittest.main()
