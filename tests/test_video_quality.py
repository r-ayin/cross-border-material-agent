"""Offline video quality-contract tests. No models, network or external codecs.

Fixtures have consistent BMFF headers/sample tables and media ranges. Their
synthetic samples test container inspection, NOT decoding or perceptual quality.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_video_quality.py
"""
import builtins
import copy
import json
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from src import dsapi, media_probe, runtime_policy, video_gen as vg


def box(kind, payload, extended=False):
    if extended:
        return struct.pack(">I4sQ", 1, kind, len(payload) + 16) + payload
    return struct.pack(">I4s", len(payload) + 8, kind) + payload


def timing(kind, duration, version, scale=1000):
    size = (100 if version == 0 else 112) if kind == b"mvhd" else (24 if version == 0 else 36)
    data = bytearray(size)
    data[0] = version
    offset = 12 if version == 0 else 20
    struct.pack_into(">II" if version == 0 else ">IQ", data, offset, scale, round(duration * scale))
    if kind == b"mvhd":
        struct.pack_into(">I", data, 20 if version == 0 else 32, 65536)
        struct.pack_into(">H", data, 24 if version == 0 else 36, 256)
        struct.pack_into(">9i", data, 36 if version == 0 else 48,
                         65536, 0, 0, 0, 65536, 0, 0, 0, 1 << 30)
        struct.pack_into(">I", data, len(data) - 4, 3)
    return box(kind, data)


def edit_list(entries, version=0):
    payload = bytes([version, 0, 0, 0]) + struct.pack(">I", len(entries))
    payload += b"".join(struct.pack(">Iihh" if version == 0 else ">Qqhh", *entry) for entry in entries)
    return box(b"edts", box(b"elst", payload))


def composition(entries, version=0):
    return box(b"ctts", bytes([version, 0, 0, 0]) + struct.pack(">I", len(entries))
               + b"".join(struct.pack(">II" if version == 0 else ">Ii", *entry) for entry in entries))


def track(duration, offset, sample_size, version=0, audio=False, co64=False, fixed=False,
          movie_scale=1000, media_scale=1000, edits=b"", ctts=b""):
    tkhd = bytearray(84 if version == 0 else 96)
    tkhd[0] = version
    tkhd[3] = 3
    struct.pack_into(">I", tkhd, 12 if version == 0 else 20, 2 if audio else 1)
    struct.pack_into(">I" if version == 0 else ">Q", tkhd, 20 if version == 0 else 28,
                     round(duration * movie_scale))
    struct.pack_into(">9i", tkhd, 40 if version == 0 else 52,
                     65536, 0, 0, 0, 65536, 0, 0, 0, 1 << 30)
    struct.pack_into(">II", tkhd, 76 if version == 0 else 88,
                     0 if audio else 1280 << 16, 0 if audio else 720 << 16)
    handler = b"soun" if audio else b"vide"
    hdlr = box(b"hdlr", b"\0" * 8 + handler + b"\0" * 12 + b"Fixture\0")
    entry = bytearray(28 if audio else 78)
    struct.pack_into(">H", entry, 6, 1)
    if audio:
        struct.pack_into(">HH", entry, 16, 2, 16)
        struct.pack_into(">I", entry, 24, 48000 << 16)
    else:
        struct.pack_into(">HHII", entry, 24, 1280, 720, 72 << 16, 72 << 16)
        struct.pack_into(">H", entry, 40, 1)
        struct.pack_into(">Hh", entry, 74, 24, -1)
        # Minimal configuration-shaped data, not a codec-validation fixture.
        entry += box(b"avcC", bytes.fromhex("0142001effe100046742001e01000268ce"))
    stsd = box(b"stsd", b"\0" * 4 + struct.pack(">I", 1)
               + box(b"mp4a" if audio else b"avc1", entry))
    stts = box(b"stts", b"\0" * 4 + struct.pack(">III", 1, 1, round(duration * media_scale)))
    stsc = box(b"stsc", b"\0" * 4 + struct.pack(">IIII", 1, 1, 1, 1))
    sizes = struct.pack(">II", sample_size if fixed else 0, 1)
    if not fixed:
        sizes += struct.pack(">I", sample_size)
    stsz = box(b"stsz", b"\0" * 4 + sizes)
    stco = box(b"co64" if co64 else b"stco", b"\0" * 4 + struct.pack(">I", 1)
               + struct.pack(">Q" if co64 else ">I", offset))
    stbl = box(b"stbl", stsd + stts + stsc + stsz + stco + ctts)
    dref = box(b"dref", b"\0" * 4 + struct.pack(">I", 1) + box(b"url ", b"\0\0\0\1"))
    header = box(b"smhd", b"\0" * 8) if audio else box(b"vmhd", b"\0\0\0\1" + b"\0" * 8)
    minf = box(b"minf", header + box(b"dinf", dref) + stbl)
    mdia = box(b"mdia", timing(b"mdhd", duration, version, media_scale) + hdlr + minf)
    return box(b"trak", box(b"tkhd", tkhd) + edits + mdia)


def mp4(duration=5, audio=False, version=0, extended=False, co64=False,
        fixed=False, movie_duration=None, audio_duration=None, movie_scale=1000,
        media_scale=1000, edits=b"", ctts=b""):
    ftyp = box(b"ftyp", b"isom\0\0\0\0isommp42", extended)
    sample = bytes.fromhex("000000026588")
    audio_sample = b"\x21\x10\x04\x60" if audio else b""
    mdat = box(b"mdat", sample + audio_sample, extended)
    offset = len(ftyp) + (16 if extended else 8)
    video_track = track(duration, offset, len(sample), version, co64=co64, fixed=fixed,
                        movie_scale=movie_scale, media_scale=media_scale, edits=edits, ctts=ctts)
    audio_track = track(audio_duration or duration, offset + len(sample), len(audio_sample),
                        version, audio=True, co64=co64, fixed=fixed, movie_scale=movie_scale) if audio else b""
    moov = box(b"moov", timing(b"mvhd", movie_duration or duration, version, movie_scale)
               + video_track + audio_track, extended)
    return ftyp + mdat + moov


class OfflineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="video_quality_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Fail closed at both urllib and sockets, even if a stub is accidentally
        # removed. Native TaskClient tests explicitly mock the wire transport.
        for target in ("urllib.request.urlopen", "socket.create_connection",
                       "socket.socket.connect", "socket.socket.connect_ex", "src.dsapi._http_request"):
            patcher = mock.patch(target, side_effect=AssertionError("NETWORK IS FORBIDDEN IN VIDEO TESTS"))
            patcher.start()
            self.addCleanup(patcher.stop)

    def probe(self, data):
        path = self.root / "probe.mp4"
        path.write_bytes(data)
        return media_probe.inspect_video(path)


class MediaProbeTests(OfflineTest):
    def test_valid_v0_actual_duration_without_audio(self):
        result = self.probe(mp4(5.25, movie_duration=30))
        self.assertEqual(result, {"valid": True, "status": "valid", "duration_seconds": 5.25,
                                  "video_start_seconds": 0, "width": 1280, "height": 720,
                                  "has_video": True, "has_audio": False, "errors": []})

    def test_v1_extended_boxes_co64_fixed_samples_audio(self):
        result = self.probe(mp4(12, audio=True, version=1, extended=True, co64=True, fixed=True))
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["duration_seconds"], 12)
        self.assertTrue(result["has_audio"])

    def test_long_v1_duration_not_truncated_to_32_bits(self):
        # stts duration field is 32-bit, but multiple samples can produce a
        # 64-bit mdhd duration. Header parsing is checked independently here.
        data = timing(b"mdhd", 5_000_000, 1)
        path = self.root / "header.bin"
        path.write_bytes(data)
        with path.open("rb") as stream:
            reader = media_probe._Reader(stream, len(data))
            self.assertEqual(reader.timing(reader.boxes(0, len(data))[0]), (1000, 5_000_000_000))

    def test_audio_movie_duration_does_not_inflate_video_duration(self):
        result = self.probe(mp4(5, audio=True, movie_duration=30, audio_duration=30))
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["duration_seconds"], 5)

    def test_empty_fake_and_header_only_mp4_are_rejected(self):
        for data in (b"", b"not a video", b"\0\0\0\x18ftypmp42" + b"\0" * 2048,
                     box(b"ftyp", b"isom\0\0\0\0"),
                     box(b"ftyp", b"isom\0\0\0\0") + box(b"moov", b"") + box(b"mdat", b"x")):
            with self.subTest(length=len(data)):
                result = self.probe(data)
                self.assertFalse(result["valid"])
                self.assertTrue(result["errors"])

    def test_every_truncated_prefix_is_invalid(self):
        data = mp4(audio=True, version=1, extended=True)
        for length in range(len(data)):
            with self.subTest(length=length):
                self.assertFalse(self.probe(data[:length])["valid"])

    def test_missing_movie_or_media_or_sample_table(self):
        for kind in (b"moov", b"mdat", b"mvhd", b"trak", b"tkhd", b"mdia", b"hdlr", b"mdhd",
                     b"minf", b"stbl", b"stsd", b"stts", b"stsc", b"stsz", b"stco"):
            with self.subTest(kind=kind):
                self.assertFalse(self.probe(mp4().replace(kind, b"free", 1))["valid"])

    def test_audio_only_file_is_not_a_video(self):
        data = mp4(audio=True)
        # Change only video handler; the audio track remains structurally valid.
        result = self.probe(data.replace(b"vide", b"meta", 1))
        self.assertFalse(result["valid"])
        self.assertFalse(result["has_video"])

    def test_bad_table_fields_are_rejected(self):
        fields = ((b"stts", 8, 0xFFFFFFFF), (b"stts", 12, 0), (b"stts", 16, 0),
                  (b"stsz", 12, 2), (b"stsz", 16, 0), (b"stsc", 12, 2),
                  (b"stsc", 16, 2), (b"stsc", 20, 2), (b"stco", 12, 1),
                  (b"stco", 12, 0xFFFFFF00), (b"mdhd", 16, 0),
                  (b"mdhd", 20, 30000), (b"tkhd", 80, 0))
        for kind, offset, value in fields:
            with self.subTest(kind=kind, offset=offset, value=value):
                data = bytearray(mp4())
                struct.pack_into(">I", data, data.index(kind) + offset, value)
                self.assertFalse(self.probe(data)["valid"])

    def test_malformed_extended_size_and_size_zero(self):
        self.assertFalse(self.probe(struct.pack(">I4sQ", 1, b"ftyp", 2 ** 63))["valid"])
        self.assertFalse(self.probe(struct.pack(">I4sQ", 1, b"ftyp", 4))["valid"])
        # A size-zero last box consumes the remaining parent, as BMFF specifies.
        data = bytearray(mp4())
        struct.pack_into(">I", data, data.index(b"moov") - 4, 0)
        self.assertTrue(self.probe(data)["valid"])

    def test_missing_file_directory_and_size_limit(self):
        self.assertFalse(media_probe.inspect_video(self.root / "missing.mp4")["valid"])
        self.assertFalse(media_probe.inspect_video(self.root)["valid"])
        path = self.root / "oversized.mp4"
        with path.open("wb") as stream:
            stream.truncate(media_probe.MAX_VIDEO_BYTES)
        result = media_probe.inspect_video(path)
        self.assertFalse(result["valid"])
        self.assertIn("200-MB", result["errors"][0])

    def test_large_sparse_file_is_seeked_not_loaded(self):
        data = mp4()
        ftyp_size = struct.unpack(">I", data[:4])[0]
        padding = 64 * 1024 * 1024
        rest = bytearray(data[ftyp_size:])
        at = rest.index(b"stco") + 12
        struct.pack_into(">I", rest, at, struct.unpack_from(">I", rest, at)[0] + padding)
        path = self.root / "sparse.mp4"
        with path.open("wb") as stream:
            stream.write(data[:ftyp_size])
            stream.write(struct.pack(">I4s", padding, b"free"))
            stream.seek(ftyp_size + padding)
            stream.write(rest)
        read_sizes = []
        original_open = builtins.open

        class GuardedFile:
            def __init__(self, *args, **kwargs):
                self.stream = original_open(*args, **kwargs)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()

            def fileno(self):
                return self.stream.fileno()

            def seek(self, *args):
                return self.stream.seek(*args)

            def read(self, size=-1):
                if size < 0 or size > 4096:
                    raise AssertionError("unbounded media read")
                read_sizes.append(size)
                return self.stream.read(size)

        with mock.patch.object(media_probe, "open", GuardedFile, create=True):
            result = media_probe.inspect_video(path)
        self.assertTrue(result["valid"], result)
        self.assertLess(sum(read_sizes), 4096)

    def test_fragmented_timelines_are_unsupported_not_corrupt(self):
        for marker in (b"moof", b"mvex"):
            result = self.probe(mp4() + box(marker, b""))
            self.assertFalse(result["valid"])
            self.assertEqual(result["status"], "unsupported")
        self.assertEqual(self.probe(mp4().replace(b"tkhd", b"edts", 1))["status"], "invalid")

    def test_real_historical_mp4_fixture_without_copying(self):
        # Existing historical asset: external ffprobe/ffmpeg decoding was checked
        # separately by the caller. This test only establishes container/timeline.
        path = Path(__file__).resolve().parents[1] / "frontend/assets/product_video.mp4"
        self.assertTrue(path.is_file(), "the existing historical fixture must be present")
        result = media_probe.inspect_video(path)
        self.assertTrue(result["valid"], result)
        self.assertEqual((result["width"], result["height"]), (1920, 1080))
        self.assertEqual(result["duration_seconds"], 5.125)
        self.assertEqual(result["video_start_seconds"], 0)
        self.assertTrue(result["has_audio"])

    def test_edit_v0_v1_convert_movie_to_media_units(self):
        for version in (0, 1):
            for movie_scale, media_scale in ((1000, 48000), (90000, 12288), (3, 1000)):
                with self.subTest(version=version, movie_scale=movie_scale):
                    edits = edit_list([(3 * movie_scale, media_scale, 1, 0)], version)
                    result = self.probe(mp4(5, edits=edits, media_scale=media_scale, movie_scale=movie_scale))
                    self.assertTrue(result["valid"], result)
                    self.assertEqual(result["duration_seconds"], 3)
                    self.assertEqual(result["video_start_seconds"], 0)
        result = self.probe(mp4(5, edits=edit_list([(1, 1, 1, 0)]), movie_scale=3))
        self.assertAlmostEqual(result["duration_seconds"], 1 / 3)

    def test_composition_offsets_and_edit_trim_without_fabricated_padding(self):
        for version, offset in ((0, 1000), (1, -1000)):
            result = self.probe(mp4(5, ctts=composition([(1, offset)], version),
                                    edits=edit_list([(5000, max(0, offset), 1, 0)])))
            self.assertTrue(result["valid"], result)
            self.assertEqual(result["duration_seconds"], 5 if offset > 0 else 4)
        result = self.probe(mp4(5, edits=edit_list([(30000, 1000, 1, 0)])))
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["duration_seconds"], 4)
        self.assertEqual(self.probe(mp4(5, edits=edit_list([(1000, 5000, 1, 0)])))["status"], "invalid")

    def test_mdhd_can_match_edited_duration_but_not_arbitrary_ticks(self):
        data = bytearray(mp4(6, edits=edit_list([(5000, 1000, 1, 0)])))
        at = data.index(b"mdhd") + 20
        struct.pack_into(">I", data, at, 5000)
        result = self.probe(data)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["duration_seconds"], 5)
        for ticks in (4999, 5001, 30000):
            struct.pack_into(">I", data, at, ticks)
            self.assertEqual(self.probe(data)["status"], "invalid")

    def test_leading_empty_edit_is_delay_not_playable_duration(self):
        for version in (0, 1):
            result = self.probe(mp4(5, movie_scale=100, media_scale=48000,
                                    edits=edit_list([(200, -1, 1, 0), (400, 48000, 1, 0)], version)))
            self.assertTrue(result["valid"], result)
            self.assertEqual(result["duration_seconds"], 4)
            self.assertEqual(result["video_start_seconds"], 2)

    def test_v1_edit_64_bit_media_time_and_duration(self):
        offset = 2 ** 32 - 1
        result = self.probe(mp4(5, ctts=composition([(1, offset)]),
                                edits=edit_list([(2 ** 32 + 10, offset + 1000, 1, 0)], 1)))
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["duration_seconds"], 4)

    def test_edit_and_composition_tables_strict_boundaries(self):
        for version in (0, 1):
            valid = edit_list([(4000, 1000, 1, 0)], version)
            elst_at = valid.index(b"elst") + 4
            payload = valid[elst_at:]
            for length in range(len(payload)):
                result = self.probe(mp4(edits=box(b"edts", box(b"elst", payload[:length]))))
                self.assertEqual(result["status"], "invalid", (version, length, result))
            for count in (0, 2, 0xFFFFFFFF):
                broken = bytearray(payload)
                struct.pack_into(">I", broken, 4, count)
                self.assertEqual(self.probe(mp4(edits=box(b"edts", box(b"elst", broken))))["status"], "invalid")
            self.assertEqual(self.probe(mp4(edits=box(b"edts", box(b"elst", payload + b"x"))))["status"], "invalid")
            self.assertEqual(self.probe(mp4(edits=valid + valid))["status"], "invalid")
        for entries in ([(0, 0)], [(2, 0)], [(1, 0), (1, 0)]):
            self.assertEqual(self.probe(mp4(ctts=composition(entries)))["status"], "invalid")
        ctts = composition([(1, 0)])
        for payload in (ctts[8:-1], ctts[8:] + b"x"):
            self.assertEqual(self.probe(mp4(ctts=box(b"ctts", payload)))["status"], "invalid")
        self.assertEqual(self.probe(mp4(ctts=ctts + ctts))["status"], "invalid")

    def test_complex_edits_are_unsupported_and_bad_fields_are_invalid(self):
        for entries in ([(2000, 0, 1, 0), (2000, 2000, 1, 0)],
                        [(1000, -1, 1, 0)] * 2 + [(3000, 0, 1, 0)],
                        [(1000, -1, 1, 0)], [(5000, 0, 0, 0)], [(5000, 0, 1, 1)]):
            result = self.probe(mp4(edits=edit_list(entries)))
            self.assertEqual(result["status"], "unsupported", result)
            self.assertIsNone(result["duration_seconds"])
        for entries in ([(0, 0, 1, 0)], [(5000, -2, 1, 0)]):
            self.assertEqual(self.probe(mp4(edits=edit_list(entries)))["status"], "invalid")

    def test_multiple_video_tracks_are_not_silently_selected(self):
        data = mp4(audio=True).replace(b"soun", b"vide", 1)
        self.assertFalse(self.probe(data)["valid"])


class FakeBudget:
    def __init__(self, seconds=1000):
        self.seconds = seconds

    def remaining(self):
        return self.seconds

    def enough(self, required):
        return self.seconds >= required


class FakeTaskClient:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def generate(self, path, model, input_obj, parameters=None, **kwargs):
        self.calls.append({"path": path, "model": model, "input": input_obj, "parameters": parameters})
        if self.error:
            raise self.error
        return {"video_url": "https://media.invalid/clip.mp4?signature=do-not-persist"}


class GenerationTests(OfflineTest):
    def context(self, **overrides):
        result = {
            "product": {"subject": "Desk lamp", "images": ["https://source.invalid/original.jpg"],
                        "attributes": [{"attributeName": "Color", "value": "Black"}]},
            "output_dir": str(self.root), "budget": FakeBudget(), "task_client": FakeTaskClient(),
            "main_image_url": "https://generated.invalid/unverified.jpg",
            "anchor_url": "https://generated.invalid/anchor.jpg",
            "vision_brief": "Unsupported waterproof and fireproof claims",
        }
        result.update(overrides)
        return result

    def run_video(self, ctx, data=None):
        def download(url, destination, **kwargs):
            Path(destination).write_bytes(mp4() if data is None else data)
            return os.path.getsize(destination)
        with mock.patch.object(vg, "download_file", side_effect=download) as stub:
            result = vg.generate_video(ctx)
        return result, stub

    def test_rich_budget_submits_one_original_reference_clip_and_measures_it(self):
        ctx = self.context()
        result, download = self.run_video(ctx, mp4(5.25, movie_duration=30))
        self.assertEqual(len(ctx["task_client"].calls), 1)
        call = ctx["task_client"].calls[0]
        self.assertEqual(call["model"], vg.VIDEO_CHAIN[0][0])
        self.assertEqual(call["input"]["img_url"], ctx["product"]["images"][0])
        self.assertEqual(call["parameters"]["duration"], "5s")
        self.assertEqual(result["artifact_status"], "needs_review")
        self.assertEqual(result["requested_duration_seconds"], 5)
        self.assertEqual(result["planned"]["storyboard_duration_seconds"], 30)
        self.assertEqual(result["delivered"]["clip_completeness"], "complete_short_clip")
        self.assertIsNone(result["contest_minimum_duration_seconds"])
        self.assertEqual(result["duration_seconds"], 5.25)
        self.assertEqual(result["actual_duration_seconds"], 5.25)
        self.assertFalse(result["delivered"]["has_audio"])
        self.assertEqual(result["subtitles"]["status"], "not_generated")
        self.assertIsNone(result["subtitles"]["total_seconds"])
        self.assertEqual(result["bgm"]["status"], "not_generated")
        self.assertIs(ctx["video_meta"], result)
        self.assertEqual(result["planned"]["storyboard_status"], "plan_only_not_delivered")
        self.assertEqual(result["delivered"]["storyboard_status"], "not_verified")
        self.assertEqual(result["segments"], [])
        self.assertEqual(download.call_count, 1)
        self.assertFalse(list(self.root.glob("product_video_seg*")))
        self.assertFalse(list(self.root.glob(".video_candidate_*")))
        manifest = json.loads((self.root / "video_manifest.json").read_text())
        self.assertEqual(manifest["duration_seconds"], 5.25)
        self.assertTrue(media_probe.inspect_video(result["path"])["valid"])

    def test_matching_duration_still_requires_visual_review(self):
        result, _ = self.run_video(self.context(requested_duration_seconds=5), mp4(5))
        self.assertEqual(result["artifact_status"], "needs_review")
        self.assertTrue(result["delivered"]["meets_duration_target"])
        self.assertTrue(result["needs_review"])

    def test_duration_tolerance(self):
        for actual, expected in ((29.0, "needs_review"), (28.0, "partial"), (33.0, "partial")):
            with self.subTest(actual=actual):
                ctx = self.context(requested_duration_seconds=30,
                                   video_capabilities={vg.I2V_MODEL: {"durations": [30], "size": vg.VIDEO_SIZE}})
                result, _ = self.run_video(ctx, mp4(actual))
                self.assertEqual(result["artifact_status"], expected)

    def test_explicit_capabilities_select_smallest_covering_duration(self):
        for target, selected in ((5, 5), (6, 10), (10, 10), (12, 15), (15, 15)):
            ctx = self.context(requested_duration_seconds=target, video_capabilities={
                vg.I2V_MODEL: {"durations": [15, 5, 10], "size": "1920*1080"}})
            result, _ = self.run_video(ctx, mp4(selected))
            self.assertEqual(len(ctx["task_client"].calls), 1)
            call = ctx["task_client"].calls[0]
            self.assertEqual(call["parameters"], {"duration": f"{selected}s", "size": "1920*1080"})
            self.assertIn(f"target {selected} seconds", call["input"]["prompt"])
            self.assertEqual(result["requested_clip_duration_seconds"], selected)
            self.assertEqual(result["artifact_status"], "needs_review")
            self.assertTrue(result["delivered"]["meets_duration_target"])

    def test_no_covering_capability_never_submits_or_downloads(self):
        for settings in ({"requested_duration_seconds": 30},
                         {"requested_duration_seconds": 30, "video_capabilities": {
                             vg.I2V_MODEL: {"durations": [5, 10, 15], "size": vg.VIDEO_SIZE}}},
                         {"requested_duration_seconds": 10, "video_model": vg.T2V_MODEL,
                          "allow_unreferenced_video": True}):
            ctx = self.context(**settings)
            result, download = self.run_video(ctx)
            self.assertEqual(result["artifact_status"], "blocked_capability")
            self.assertTrue(result["blocked_capability"])
            self.assertEqual(result["capability_testing_status"], "pending_verification")
            self.assertIsNone(result["path"])
            self.assertIsNone(result["planned"]["parameters"])
            self.assertEqual(ctx["task_client"].calls, [])
            download.assert_not_called()

    def test_covering_model_is_selected_locally_not_after_failed_submission(self):
        second = vg.VIDEO_CHAIN[1][0]
        ctx = self.context(requested_duration_seconds=10, video_capabilities={
            second: {"durations": [5, 10], "size": vg.VIDEO_SIZE}})
        result, _ = self.run_video(ctx, mp4(10))
        self.assertEqual(result["model"], second)
        self.assertEqual(len(ctx["task_client"].calls), 1)
        ctx = self.context(requested_duration_seconds=10, task_client=FakeTaskClient(TimeoutError()),
                           video_capabilities={name: {"durations": [10], "size": vg.VIDEO_SIZE}
                                               for name, _ in vg.VIDEO_CHAIN})
        result, _ = self.run_video(ctx)
        self.assertEqual(result["artifact_status"], "failed")
        self.assertEqual(len(ctx["task_client"].calls), 1)

    def test_new_model_requires_explicit_known_protocol_and_parameters(self):
        model = "caller-verified-low-cost-model"
        for kind in ("i2v", "r2v", "t2v"):
            ctx = self.context(video_model=model, allow_unreferenced_video=True, video_capabilities={model: {
                "protocol": "dashscope-video-v1", "kind": kind, "durations": [5, 10], "size": vg.VIDEO_SIZE}})
            result, _ = self.run_video(ctx)
            self.assertEqual(result["model"], model)
            self.assertEqual(result["kind"], kind + "-single")
            self.assertEqual(len(ctx["task_client"].calls), 1)
        invalid_specs = ({}, {"durations": [5], "size": vg.VIDEO_SIZE},
                         {"kind": "i2v", "protocol": "unknown", "durations": [5], "size": vg.VIDEO_SIZE},
                         {"kind": "i2v", "protocol": "dashscope-video-v1", "durations": [5],
                          "size": vg.VIDEO_SIZE, "arbitrary_parameter": True})
        for spec in invalid_specs:
            ctx = self.context(video_model=model, video_capabilities={model: spec})
            result, download = self.run_video(ctx)
            self.assertEqual(result["artifact_status"], "blocked_capability")
            self.assertEqual(ctx["task_client"].calls, [])
            download.assert_not_called()
        ctx = self.context(video_model=model)
        result, _ = self.run_video(ctx)
        self.assertEqual(result["artifact_status"], "blocked_capability")

    def test_invalid_capabilities_targets_and_endpoints_block_before_submission(self):
        good = {"durations": [5, 10], "size": vg.VIDEO_SIZE}
        invalid = [{**good, "durations": d} for d in ([], [True], [0], [-5], [float("inf")], ["10"])]
        invalid += [{**good, "size": "auto"}, {**good, "parameters": {"duration": 5}},
                    {**good, "endpoint": "/unknown"}, {**good, "kind": "t2v"}, None]
        settings = [{"video_model": vg.I2V_MODEL, "video_capabilities": {vg.I2V_MODEL: spec}}
                    for spec in invalid]
        settings += [{"requested_duration_seconds": value} for value in (0, -1, True, "bad", float("nan"))]
        settings += [{"video_capabilities": []}, {"video_endpoint": "/unknown"}]
        for setting in settings:
            with self.subTest(setting=setting):
                ctx = self.context(**setting)
                result, download = self.run_video(ctx)
                self.assertEqual(result["artifact_status"], "blocked_capability")
                self.assertEqual(ctx["task_client"].calls, [])
                download.assert_not_called()

    def test_r2v_chain_link_actually_executes_when_selected_locally(self):
        model = vg.VIDEO_CHAIN[1][0]
        ctx = self.context(available_video_models=[model, vg.T2V_MODEL])
        result, _ = self.run_video(ctx)
        self.assertEqual(result["kind"], "r2v-single")
        self.assertEqual(ctx["task_client"].calls[0]["input"]["media"], ctx["product"]["images"])
        self.assertEqual(len(ctx["task_client"].calls), 1)

    def test_no_reference_denies_t2v_and_unverified_generated_anchors(self):
        ctx = self.context(product={"subject": "Lamp", "images": []})
        result, download = self.run_video(ctx)
        self.assertEqual(result["artifact_status"], "planned_only")
        self.assertIsNone(result["path"])
        self.assertEqual(ctx["task_client"].calls, [])
        download.assert_not_called()
        self.assertFalse((self.root / "product_video_srt.srt").exists())
        self.assertEqual(result["subtitles"]["status"], "not_generated")
        self.assertTrue((self.root / "video_manifest.json").exists())

    def test_verified_main_reference_is_eligible_only_without_original(self):
        ctx = self.context(product={"subject": "Lamp"}, main_image_verified=True)
        result, _ = self.run_video(ctx)
        self.assertEqual(result["reference"]["source"], "verified_main_image")
        self.assertEqual(ctx["task_client"].calls[0]["input"]["img_url"], ctx["main_image_url"])
        ctx = self.context(main_image_verified=True)
        result, _ = self.run_video(ctx)
        self.assertEqual(result["reference"]["source"], "original_product_image")

    def test_t2v_requires_literal_opt_in_and_never_claims_fidelity(self):
        for opt_in in (False, "true", 1, True):
            with self.subTest(opt_in=repr(opt_in)):
                ctx = self.context(product={"subject": "Desk lamp"}, allow_unreferenced_video=opt_in,
                                   requested_duration_seconds=5)
                result, _ = self.run_video(ctx)
                self.assertEqual(len(ctx["task_client"].calls), 1 if opt_in is True else 0)
                if opt_in is True:
                    self.assertEqual(result["kind"], "t2v-single")
                    self.assertEqual(result["artifact_status"], "needs_review")
                    self.assertEqual(result["reference"]["fidelity"], "unknown")
                    self.assertEqual(set(ctx["task_client"].calls[0]["input"]), {"prompt"})

    def test_budget_and_explicit_offline_modes_do_not_call_clients(self):
        for settings in ({"budget": FakeBudget(30)}, {"video_plan_only": True}, {"offline": True}):
            with self.subTest(settings=settings):
                ctx = self.context(**settings)
                result, download = self.run_video(ctx)
                self.assertEqual(result["artifact_status"], "planned_only")
                self.assertEqual(ctx["task_client"].calls, [])
                download.assert_not_called()
                self.assertIsNone(result["actual_duration_seconds"])
                self.assertEqual(result["subtitles"]["status"], "not_generated")

    def test_budget_selects_only_one_plan_before_submission(self):
        ctx = self.context(budget=FakeBudget(150))
        result, _ = self.run_video(ctx)
        self.assertEqual(result["planned"]["storyboard_duration_seconds"], 15)
        self.assertEqual(len(result["planned"]["storyboard"]), 5)
        self.assertEqual(len(ctx["task_client"].calls), 1)

    def test_invalid_candidates_never_become_final_or_subtitles(self):
        result, _ = self.run_video(self.context(), b"\0\0\0\x18ftypmp42" + b"\0" * 2048)
        self.assertEqual(result["artifact_status"], "invalid")
        self.assertIsNone(result["path"])
        self.assertIsNone(result["duration_seconds"])
        self.assertFalse((self.root / "product_video.mp4").exists())
        self.assertFalse((self.root / "product_video_srt.srt").exists())
        self.assertEqual(result["subtitles"]["status"], "not_generated")

    def test_segment_cannot_masquerade_as_whole_film(self):
        ctx = self.context()
        segment = self.root / "product_video_seg_3.mp4"
        segment.write_bytes(mp4(12))
        meta = {"degradation": []}
        self.assertIsNone(vg._generate_segmented(ctx, vg.build_shot_prompts(ctx["product"]),
                                               ctx["product"]["images"], time.monotonic() + 100, meta))
        self.assertFalse((self.root / "product_video.mp4").exists())
        self.assertEqual(ctx["task_client"].calls, [])
        self.assertTrue(segment.exists())

    def test_auth_validation_rate_limit_timeout_and_failure_never_resubmit(self):
        errors = [dsapi.ApiError("private provider error", status=status, retryable=True)
                  for status in (400, 401, 403, 404, 429, 500)] + [TimeoutError("private timeout")]
        for error in errors:
            with self.subTest(error=type(error).__name__, status=getattr(error, "status", None)):
                ctx = self.context(task_client=FakeTaskClient(error), allow_unreferenced_video=True)
                result, download = self.run_video(ctx)
                self.assertEqual(len(ctx["task_client"].calls), 1)
                self.assertEqual(result["artifact_status"], "failed")
                self.assertIsNone(result["duration_seconds"])
                download.assert_not_called()
                self.assertNotIn("private", json.dumps(result))

    def test_parameter_wrapper_does_not_strip_and_retry(self):
        client = FakeTaskClient(dsapi.ApiError("unsupported duration", status=400))
        params = {"duration": "5s", "size": vg.VIDEO_SIZE}
        with self.assertRaises(dsapi.ApiError):
            vg._submit_with_params(client, vg.I2V_MODEL, "i2v", "prompt", "https://source.invalid/x",
                                   time.monotonic() + 10, params)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["parameters"], params)

    def test_native_client_internal_retries_are_not_used(self):
        client = dsapi.TaskClient("offline-placeholder", "https://api.invalid/api/v1")
        for status in (400, 401, 403, 429, 500):
            with self.subTest(status=status), mock.patch.object(dsapi, "_http_request", return_value=(status, b"{}", {})) as wire, \
                    mock.patch.object(client, "generate", side_effect=AssertionError("unsafe retrying generate called")), \
                    mock.patch.object(client, "submit", side_effect=AssertionError("async resubmission called")):
                result, _ = self.run_video(self.context(task_client=client))
                self.assertEqual(result["artifact_status"], "failed")
                self.assertEqual(wire.call_count, 1)

    def test_native_timeout_and_failed_poll_do_not_resubmit(self):
        client = dsapi.TaskClient("offline-placeholder", "https://api.invalid/api/v1")
        with mock.patch.object(dsapi, "_http_request", side_effect=TimeoutError) as wire:
            result, _ = self.run_video(self.context(task_client=client))
            self.assertEqual(wire.call_count, 1)
            self.assertEqual(result["artifact_status"], "failed")
        response = json.dumps({"output": {"task_id": "offline-task"}}).encode()
        with mock.patch.object(dsapi, "_http_request", return_value=(200, response, {})) as wire, \
                mock.patch.object(client, "poll", side_effect=dsapi.ApiError("poll timeout")) as poll:
            result, _ = self.run_video(self.context(task_client=client))
            self.assertEqual(wire.call_count, 1)
            self.assertEqual(poll.call_count, 1)
            self.assertEqual(result["artifact_status"], "failed")

    def test_native_task_id_is_polled_without_new_submission(self):
        client = dsapi.TaskClient("offline-placeholder", "https://api.invalid/api/v1")
        response = json.dumps({"output": {"task_id": "offline-task"}}).encode()
        with mock.patch.object(dsapi, "_http_request", return_value=(200, response, {})) as wire, \
                mock.patch.object(client, "poll", return_value={"video_url": "https://media.invalid/x.mp4"}) as poll:
            result, _ = self.run_video(self.context(task_client=client))
            self.assertEqual(wire.call_count, 1)
            self.assertEqual(poll.call_count, 1)
            self.assertEqual(result["artifact_status"], "needs_review")

    def test_manifest_has_no_signed_urls_auth_or_raw_provider_error(self):
        ctx = self.context()
        ctx["product"]["images"] = ["https://user:secret@source.invalid/p.jpg?token=signature#private"]
        ctx["unrelated_secret"] = "not-to-be-copied"
        result, _ = self.run_video(ctx)
        manifest = (self.root / "video_manifest.json").read_text()
        for token in ("secret", "signature", "private", "not-to-be-copied", "Authorization"):
            self.assertNotIn(token, manifest)
        self.assertEqual(result["reference"]["url"], "https://source.invalid/p.jpg")
        self.assertEqual(ctx["task_client"].calls[0]["input"]["img_url"], ctx["product"]["images"][0])

    def test_unverified_copy_and_chinese_source_are_drafts_not_english_subtitles(self):
        (self.root / "product_description_en.md").write_text(
            "## Key Features\n- Waterproof and fireproof, with lifetime warranty.\n", encoding="utf-8")
        for subject in ("Desk lamp", "黑色台灯"):
            ctx = self.context()
            ctx["product"]["subject"] = subject
            result, _ = self.run_video(ctx)
            self.assertEqual(result["subtitles"]["status"], "not_generated")
            self.assertIsNone(result["subtitles"]["path"])
            self.assertFalse((self.root / "product_video_srt.srt").exists())
            self.assertIn(subject, result["planned"]["subtitle_sources"])
            self.assertIn("warranty", result["planned"]["subtitle_copy_draft"][0])
            self.assertNotIn("fireproof", result["planned"]["clip_prompt"])

    def test_only_caller_verified_english_cues_fit_actual_duration(self):
        ctx = self.context(verified_subtitle_features=["Black base.", "Round shape.", "Visible switch."])
        ctx["product"]["subject"] = "黑色台灯"
        result, _ = self.run_video(ctx, mp4(5.123))
        subtitles = result["subtitles"]
        self.assertEqual(subtitles["status"], "sidecar_only")
        self.assertEqual(subtitles["verification"], "caller_attested")
        self.assertEqual(subtitles["total_seconds"], 5.123)
        text = Path(subtitles["path"]).read_text()
        self.assertIn("Black base.", text)
        self.assertIn("00:00:05,123", text)
        self.assertNotIn("黑色台灯", text)

    def test_non_english_or_malformed_verified_cues_not_delivered(self):
        for values in (["黑色台灯"], ["Black 黑色台灯"], "Black base.", [None, 123], [],
                       [" ".join(["visible"] * 40) + "."]):
            result, _ = self.run_video(self.context(verified_subtitle_features=values))
            self.assertEqual(result["subtitles"]["status"], "not_generated")
            self.assertIsNone(result["subtitles"]["path"])

    def test_subtitle_timeline_skips_leading_empty_edit(self):
        data = mp4(5, edits=edit_list([(2000, -1, 1, 0), (5000, 0, 1, 0)]))
        result, _ = self.run_video(self.context(verified_subtitle_features=["Black base."]), data)
        subtitles = result["subtitles"]
        self.assertEqual(subtitles["start_seconds"], 2)
        self.assertEqual(subtitles["total_seconds"], 5)
        self.assertIn("00:00:02,000 --> 00:00:07,000", Path(subtitles["path"]).read_text())

    def test_fractional_empty_edit_cues_do_not_round_outside_visible_content(self):
        data = mp4(5, movie_scale=3000, edits=edit_list([(1, -1, 1, 0), (15000, 0, 1, 0)]))
        result, _ = self.run_video(self.context(verified_subtitle_features=["Black base."]), data)
        subtitles = result["subtitles"]
        self.assertEqual(subtitles["start_seconds"], .001)
        self.assertIn("00:00:00,001 --> 00:00:05,000", Path(subtitles["path"]).read_text())

    def test_unsupported_candidate_is_not_labeled_corrupt_or_promoted(self):
        result, _ = self.run_video(self.context(), mp4(edits=edit_list([(5000, 0, 0, 0)])))
        self.assertEqual(result["artifact_status"], "unsupported")
        self.assertIsNone(result["path"])
        self.assertFalse((self.root / "product_video.mp4").exists())

    def test_preexisting_artifact_is_not_claimed_by_failed_run(self):
        existing = self.root / "product_video.mp4"
        existing.write_bytes(mp4(30))
        result, _ = self.run_video(self.context(task_client=FakeTaskClient(TimeoutError())))
        self.assertIsNone(result["path"])
        self.assertEqual(result["delivered"]["clip_count"], 0)
        self.assertTrue(any("Pre-existing" in text for text in result["limitations"]))
        self.assertTrue(existing.exists())

    def test_download_delegates_to_shared_policy_without_retries(self):
        destination = self.root / "download.mp4"
        with mock.patch.object(dsapi, "download_file", return_value=1024) as download:
            self.assertEqual(vg.download_file("https://media.invalid/x.mp4", destination, max_retries=9), 1024)
            download.assert_called_once_with("https://media.invalid/x.mp4", str(destination),
                                             max_retries=0, label="dl:video")
        with mock.patch.object(dsapi, "download_file", return_value=media_probe.MAX_VIDEO_BYTES):
            with self.assertRaises(ValueError):
                vg.download_file("https://media.invalid/x.mp4", destination)

    def test_download_denied_by_policy_before_transport(self):
        with mock.patch.dict(os.environ, {"AGENT_ALLOW_PAID_CALLS": "0"}), \
                mock.patch("urllib.request.urlopen") as wire:
            with self.assertRaises(runtime_policy.PolicyError):
                vg.download_file("https://media.invalid/x.mp4", self.root / "denied.mp4")
            wire.assert_not_called()
        expired = runtime_policy.RuntimePolicy(deadline=time.monotonic() - 1)
        with mock.patch.object(dsapi, "policy", return_value=expired), \
                mock.patch.dict(os.environ, {"AGENT_ALLOW_PAID_CALLS": "1"}), \
                mock.patch("urllib.request.urlopen") as wire:
            with self.assertRaises(runtime_policy.PolicyError):
                vg.download_file("https://media.invalid/x.mp4", self.root / "expired.mp4")
            wire.assert_not_called()

    def test_shared_download_checks_deadline_while_reading_and_cleans_partial(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"sample"
        guard = mock.Mock()
        guard.remaining.return_value = 30
        guard.check_time.side_effect = [None, None, runtime_policy.PolicyError("expired")]
        path = self.root / "expired.mp4"
        with mock.patch.object(dsapi, "policy", return_value=guard), \
                mock.patch("urllib.request.urlopen", return_value=response) as wire:
            with self.assertRaises(runtime_policy.PolicyError):
                vg.download_file("https://media.invalid/x.mp4", path)
            guard.authorize.assert_called_once_with("https://media.invalid/x.mp4")
            self.assertEqual(wire.call_count, 1)
            self.assertEqual(response.read.call_count, 1)
        self.assertFalse(path.exists())
        self.assertFalse(Path(str(path) + ".part").exists())

    def test_network_guard_is_active(self):
        with self.assertRaisesRegex(AssertionError, "NETWORK IS FORBIDDEN"):
            socket.create_connection(("localhost", 9))


class PromptAndSubtitleTests(OfflineTest):
    def test_both_plans_are_pure_generic_complete_five_beats(self):
        for subject in ("Desk lamp", "Coffee mug", "Running shoes", "Pleated skirt"):
            product = {"subject": subject, "attributes": [{"attributeName": "Color", "value": "Blue"}]}
            original = copy.deepcopy(product)
            for builder, total in ((vg.build_shot_prompts, 30), (vg.build_compressed_shot_prompts, 15)):
                shots = builder(product, "Invented claim: fireproof")
                self.assertEqual([s["name"] for s in shots], ["Hook", "Problem", "Product", "Proof", "CTA"])
                self.assertEqual(shots[0]["start"], 0)
                self.assertEqual(shots[-1]["end"], total)
                self.assertTrue(all(a["end"] == b["start"] for a, b in zip(shots, shots[1:])))
                prompts = " ".join(s["prompt"] for s in shots)
                self.assertNotIn("waistband", prompts)
                self.assertNotIn("model wearing", prompts)
                self.assertNotIn("fireproof", prompts)
                self.assertIn("reference image is authoritative", prompts)
                self.assertEqual(product, original)
                self.assertEqual(shots, builder(product, "Another unverified brief"))

    def test_combined_t2v_does_not_claim_one_take_and_five_cuts(self):
        product = {"subject": "Cup"}
        prompt = vg.build_combined_t2v_prompt(vg.build_shot_prompts(product), product)
        self.assertIn("sequential cuts", prompt)
        self.assertNotIn("one take without cuts", prompt)
        self.assertNotIn("restore product fidelity", prompt)
        self.assertIn("fidelity is unknown", prompt)

    def test_srt_preserves_words_and_sentences_beyond_sixty_characters(self):
        fact = "The source lists a matte black surface and a round base with a clearly visible switch."
        cues = vg.build_srt_entries([fact], "", [], 15)
        self.assertEqual(" ".join(" ".join(c[2].split()) for c in cues), fact)
        self.assertGreater(len(fact), 60)
        self.assertEqual(cues[0][0], 0)
        self.assertEqual(cues[-1][1], 15)
        self.assertTrue(all(len(c[2].splitlines()) <= 2 for c in cues))

    def test_no_minimum_cue_padding_or_invented_features(self):
        cues = vg.build_srt_entries(["Black."], "Ignored", ["Invented fallback"], 5)
        self.assertEqual(cues, [(0.0, 5.0, "Black.")])
        self.assertEqual(vg.build_srt_entries([], "", [], 5), [])
        self.assertEqual(vg.build_srt_entries([], "黑色台灯", ["Black base."], 5), [])
        self.assertEqual(vg.build_srt_entries(["黑色台灯"], "", [], 5), [])
        self.assertEqual(vg.build_srt_entries(["Black."], "", [], None), [])

    def test_subtitle_boundaries_fractional_duration_and_readability(self):
        duration = 5.1234
        cues = vg.build_srt_entries(["Black base.", "Round shape.", "Visible switch."], "", [], duration)
        self.assertTrue(cues)
        self.assertLessEqual(cues[-1][1], duration)
        self.assertEqual(cues[-1][1], 5.123)
        for start, end, caption in cues:
            self.assertLess(start, end)
            self.assertGreaterEqual(end - start, 1.499)
        for a, b in zip(cues, cues[1:]):
            self.assertEqual(a[1], b[0])
        self.assertIn("00:00:05,123", vg.format_srt(cues))
        for duration in (0, -1, float("nan"), float("inf"), "bad"):
            self.assertEqual(vg.build_srt_entries(["Black base."], "", [], duration), [])

    def test_long_word_is_never_sliced_and_long_sentence_is_not_half_delivered(self):
        word = "x" * 90
        cues = vg.build_srt_entries([word], "", [], 10)
        self.assertEqual(cues[0][2], word)
        sentence = " ".join(["visible"] * 40) + "."
        self.assertEqual(vg.build_srt_entries([sentence], "", [], 5), [])


if __name__ == "__main__":
    unittest.main()
