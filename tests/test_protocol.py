import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from local_lab.protocol import ProtocolError, recv_frame, sanitize_filename, send_frame, sha256_bytes
from local_lab.server import handle_tcp_connection


class MemorySocket:
    def __init__(self, incoming=b""):
        self.incoming = incoming
        self.outgoing = bytearray()

    def recv(self, size):
        chunk, self.incoming = self.incoming[:size], self.incoming[size:]
        return chunk

    def sendall(self, data):
        self.outgoing.extend(data)

    def settimeout(self, _seconds):
        pass


class ProtocolTests(unittest.TestCase):
    def test_frame_round_trip(self):
        sender = MemorySocket()
        send_frame(sender, {"kind": "message"}, b"hello")
        header, payload = recv_frame(MemorySocket(sender.outgoing))
        self.assertEqual(header["kind"], "message")
        self.assertEqual(payload, b"hello")

    def test_frame_size_limit(self):
        sender = MemorySocket()
        send_frame(sender, {"kind": "message"}, b"large")
        with self.assertRaises(ProtocolError): recv_frame(MemorySocket(sender.outgoing), 4)

    def test_filename_sanitization_and_traversal_rejection(self):
        self.assertEqual(sanitize_filename("hello world.txt"), "hello_world.txt")
        for value in ("../secret", "a\\b.txt", "..", ""):
            with self.subTest(value=value), self.assertRaises(ProtocolError): sanitize_filename(value)

    def test_hash_verification(self):
        self.assertEqual(sha256_bytes(b"abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_file_saved_under_receive_directory_and_acknowledged(self):
        payload = b"safe lab data"
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temp:
            request = MemorySocket()
            send_frame(request, {"kind": "file", "filename": "notes.txt", "file_size": len(payload), "sha256": sha256_bytes(payload)}, payload)
            connection = MemorySocket(request.outgoing)
            handle_tcp_connection(connection, Path(temp), 1024)
            response, _ = recv_frame(MemorySocket(connection.outgoing))
            self.assertTrue(response["ok"])
            self.assertEqual((Path(temp) / "notes.txt").read_bytes(), payload)


if __name__ == "__main__": unittest.main()
