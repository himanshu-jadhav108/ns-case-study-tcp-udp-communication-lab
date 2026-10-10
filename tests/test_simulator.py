import unittest

from simulator import simulate_network, summarize


class SimulatorTests(unittest.TestCase):
    def test_seeded_results_are_deterministic(self):
        args = dict(packet_count=40, packet_bytes=256, base_delay_ms=25, loss_probability=0.2, bandwidth_kbps=512, seed=19)
        self.assertEqual(simulate_network(**args), simulate_network(**args))

    def test_zero_loss_and_invalid_inputs(self):
        rows = simulate_network(packet_count=10, packet_bytes=128, base_delay_ms=0, loss_probability=0, bandwidth_kbps=1000)
        self.assertEqual(summarize(rows, 1000)["loss_count"], 0)
        with self.assertRaises(ValueError):
            simulate_network(packet_count=0, packet_bytes=128, base_delay_ms=0, loss_probability=0, bandwidth_kbps=1000)
        with self.assertRaises(ValueError):
            simulate_network(packet_count=1, packet_bytes=128, base_delay_ms=0, loss_probability=1.1, bandwidth_kbps=1000)


if __name__ == "__main__": unittest.main()
