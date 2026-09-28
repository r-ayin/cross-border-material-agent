# -*- coding: utf-8 -*-
"""Offline quality regression tests. All sockets and real HTTP are forbidden."""
import copy
import itertools
import json
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from src import aesthetic_critic as critic
from src import dsapi
from src import image_gen as images

SOURCE = "https://source.invalid/front.png"
SOURCE_TWO = "https://source.invalid/detail.png"
CANDIDATE = "https://generated.invalid/candidate.png"


def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))


def png(color=(255, 255, 255), width=8, height=8, filter_type=0, raw=None,
        compressed=None, color_type=2, extras=b""):
    if raw is None:
        raw = b"".join(bytes([filter_type]) + bytes(color) * width for _ in range(height))
    return (images.PNG_MAGIC
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0))
            + extras + chunk(b"IDAT", zlib.compress(raw) if compressed is None else compressed)
            + chunk(b"IEND", b""))


def report(score=8, verdict="accept", **updates):
    result = {"scores": dict.fromkeys(critic.SCORE_KEYS, score), "total": 40,
              "verdict": verdict, "reason": "fixture", "role_match": True}
    result.update(updates)
    return result


class FakeBudget:
    def remaining(self):
        return 600

    def enough(self, seconds):
        return True


class FakeTask:
    def __init__(self):
        self.calls = []
        self.sequence = itertools.count(1)

    def generate(self, path, model, input_obj, parameters=None, deadline=None, label=""):
        index = next(self.sequence)
        self.calls.append((path, model, input_obj, parameters))
        return {"results": [{"url": f"https://generated.invalid/{index}.png"}]}


class FakeChat:
    def __init__(self, score=None, compliance="NO"):
        self.score = report() if score is None else score
        self.compliance = compliance
        self.calls = []

    def chat(self, model, messages, **kwargs):
        self.calls.append((model, messages, kwargs))
        if messages[0]["content"] == critic.COMPLIANCE_SYSTEM:
            return self.compliance
        return json.dumps(self.score)


class OfflineTest(unittest.TestCase):
    def setUp(self):
        self.network_guards = []
        for target in ("socket.socket", "socket.create_connection", "socket.getaddrinfo",
                       "urllib.request.urlopen", "src.dsapi._http_request"):
            guard = patch(target, side_effect=AssertionError("Real network is forbidden"))
            mock = guard.start()
            self.addCleanup(guard.stop)
            self.network_guards.append(mock)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = self.temp.name

    def tearDown(self):
        for guard in self.network_guards:
            guard.assert_not_called()

    def context(self, **updates):
        ctx = {"output_dir": self.output, "product": {"subject": "skirt", "images": [SOURCE, SOURCE_TWO]},
               "task_client": FakeTask(), "chat": FakeChat(), "budget": FakeBudget()}
        ctx.update(updates)
        return ctx

    def download(self, url, destination, **kwargs):
        Path(destination).write_bytes(png())
        return os.path.getsize(destination)

    def generate_one(self, ctx=None, sink=None, **kwargs):
        ctx = ctx if ctx is not None else self.context()
        defaults = dict(slot_name="main_image", prompt="source-locked product photo", ref_url=[SOURCE],
                        size=images.MAIN_SIZE, model_chain=["primary", "fallback", "last"],
                        dest_base=os.path.join(self.output, "main_image"),
                        deadline=time.monotonic() + 60, white_bg=True, url_sink=sink)
        defaults.update(kwargs)
        return images._gen_one(ctx["task_client"], ctx, **defaults)

    def write_fixture(self, data, name="fixture.tmp"):
        path = Path(self.output) / name
        path.write_bytes(data)
        return str(path)


class PlanTests(OfflineTest):
    def test_six_fixed_roles_and_pure_source_lock(self):
        ctx = {"product": {"subject": "skirt", "images": [SOURCE, SOURCE_TWO]},
               "output_dir": self.output, "anchor_url": CANDIDATE,
               "style_profile": {"detail_themes": ["imaginary back"],
                                 "image_modifiers": "pure white background"}}
        before = copy.deepcopy(ctx)
        jobs = images.build_image_jobs(ctx)
        self.assertEqual(ctx, before)
        self.assertEqual([j["name"] for j in jobs], ["main_image"] + [f"detail_image_{i}" for i in range(1, 6)])
        self.assertEqual(len({j["role"] for j in jobs}), 6)
        self.assertEqual(len({j["prompt"] for j in jobs}), 6)
        for job in jobs:
            self.assertTrue(job["prompt"].strip())
            self.assertEqual(job["ref"], [SOURCE, SOURCE_TWO])
            self.assertTrue(all(key in job for key in ("name", "prompt", "ref", "size", "chain", "dest", "white_bg")))
            self.assertIn("sole visual authority", job["prompt"])
            self.assertIn("Do not invent dimensions", job["prompt"])
            self.assertNotIn("imaginary back", job["prompt"])
            self.assertNotIn("wearing ONLY", job["prompt"])
        self.assertIn("flat lay or hanging", jobs[0]["prompt"])
        self.assertTrue(jobs[0]["white_bg"])
        self.assertEqual(sum(j["white_bg"] for j in jobs), 1)
        lifestyle = jobs[4]
        self.assertEqual(lifestyle["role"], "lifestyle")
        self.assertNotIn("indoor scene", lifestyle["negative_prompt"])
        self.assertNotIn("outdoor scene", lifestyle["negative_prompt"])
        self.assertNotIn("colored background", lifestyle["negative_prompt"])
        self.assertIn("normal complete", lifestyle["prompt"])
        self.assertIn("ONE source-supported", jobs[5]["prompt"])
        json.dumps(jobs)
        jobs[0]["ref"].clear()
        self.assertEqual(jobs[1]["ref"], [SOURCE, SOURCE_TWO])

    def test_anchor_helper_never_generates(self):
        ctx = self.context()
        self.assertEqual(images.generate_anchor(ctx, time.monotonic() + 60), (SOURCE, None))
        self.assertEqual(ctx["task_client"].calls, [])

    def test_empty_or_oversized_style_themes_still_six(self):
        for themes in ([], ["one"], ["one"] * 20):
            self.assertEqual(len(images.build_image_jobs(self.context(style_profile={"detail_themes": themes}))), 6)


class CriticTests(OfflineTest):
    def test_reference_urls_in_messages_and_total_recomputed(self):
        chat = FakeChat(report(score=7, total="untrusted"))
        result = critic.score_image_url(chat, CANDIDATE, reference_urls=[SOURCE, SOURCE_TWO])
        self.assertEqual(result["total"], 28)
        content = chat.calls[0][1][-1]["content"]
        self.assertEqual([p["image_url"]["url"] for p in content if p["type"] == "image_url"],
                         [SOURCE, SOURCE_TWO, CANDIDATE])
        self.assertTrue(result["reference_checked"])

    def test_single_low_dimension_overrides_accept_and_forged_total(self):
        value = report(score=10)
        value["scores"]["product_fidelity"] = 4
        validated = critic.validate_critique(value)
        self.assertEqual(validated["total"], 34)
        self.assertEqual(validated["verdict"], "retry")
        self.assertTrue(critic.should_retry(value))
        self.assertTrue(critic.should_retry(report(score=6)))

    def test_malformed_scores_rejected(self):
        for invalid in (True, "9", None, -1, 11, 10 ** 1000, float("inf"), float("nan"), [], {}):
            with self.subTest(value=invalid):
                value = report()
                value["scores"]["artifact_free"] = invalid
                self.assertIsNone(critic.validate_critique(value))
                self.assertTrue(critic.should_retry(value))
        for value in ([], {}, {"total": 40}, {"scores": {"artifact_free": 8}}):
            self.assertIsNone(critic.validate_critique(value))
        chat = FakeChat({"total": 40, "verdict": "accept"})
        result = critic.score_image_url(chat, CANDIDATE, reference_urls=[SOURCE])
        self.assertTrue(result["invalid"])
        self.assertEqual(len(chat.calls), 2)

    def test_unknown_and_no_reference_never_accept(self):
        for verdict in ("unknown", "ACCEPT", None, "unexpected"):
            self.assertTrue(critic.should_retry(report(verdict=verdict)))
        self.assertTrue(critic.should_retry(None))
        result = critic.score_image_url(FakeChat(), CANDIDATE)
        self.assertEqual(result["verdict"], "unknown")
        best, _ = critic.pick_best_url(FakeChat(report(verdict="unknown")), [CANDIDATE], reference_urls=[SOURCE])
        self.assertIsNone(best)

    def test_ambiguous_compliance_is_unknown(self):
        for answer in ("NOT SURE", "NO, there is a logo", "NOPE", "YESterday", "UNKNOWN", ""):
            with self.subTest(answer=answer):
                self.assertIsNone(critic.check_compliance(FakeChat(compliance=answer), CANDIDATE))
        self.assertIs(critic.check_compliance(FakeChat(compliance="YES watermark"), CANDIDATE), True)
        self.assertIs(critic.check_compliance(FakeChat(compliance="NO"), CANDIDATE), False)

    def test_expired_critic_and_compliance_do_not_call(self):
        chat = FakeChat()
        self.assertIsNone(critic.score_image_url(chat, CANDIDATE, deadline=0))
        self.assertIsNone(critic.check_compliance(chat, CANDIDATE, deadline=0))
        self.assertEqual(chat.calls, [])

    def test_primary_malformed_critic_can_use_valid_fallback(self):
        chat = Mock()
        chat.chat.side_effect = [json.dumps({"scores": []}), json.dumps(report())]
        result = critic.score_image_url(chat, CANDIDATE, reference_urls=SOURCE)
        self.assertEqual(result["verdict"], "accept")
        self.assertEqual(result["model"], critic.CRITIC_MODEL_FALLBACK)


class PngTests(OfflineTest):
    def test_white_dark_and_transparent_edges(self):
        self.assertEqual(images._png_near_white_edge_ratio(self.write_fixture(png())), 1)
        self.assertEqual(images._png_near_white_edge_ratio(self.write_fixture(png(color=(40, 40, 40)))), 0)
        self.assertEqual(images._png_near_white_edge_ratio(self.write_fixture(png(color=(255, 255, 255, 0), color_type=6))), 0)
        extra = chunk(b"tRNS", struct.pack(">HHH", 255, 255, 255))
        self.assertEqual(images._png_near_white_edge_ratio(self.write_fixture(png(extras=extra))), 0)

    def test_all_five_png_filters(self):
        for kind in range(5):
            with self.subTest(filter=kind):
                raw = bytearray()
                row = bytes([255] * 24)
                previous = bytes(24)
                for _ in range(8):
                    raw.append(kind)
                    for i, value in enumerate(row):
                        left = row[i - 3] if i >= 3 else 0
                        up = previous[i]
                        upper_left = previous[i - 3] if i >= 3 else 0
                        predictor = (0 if kind == 0 else left if kind == 1 else up if kind == 2
                                     else (left + up) // 2 if kind == 3 else images._paeth(left, up, upper_left))
                        raw.append((value - predictor) & 255)
                    previous = row
                self.assertEqual(images._png_near_white_edge_ratio(self.write_fixture(png(raw=bytes(raw)))), 1)

    def test_corrupt_truncated_and_bad_filter_rejected(self):
        good = png()
        bad_crc = good[:29] + bytes([good[29] ^ 1]) + good[30:]
        fixtures = [b"<html>not an image</html>", b"\xff\xd8junk", good[:-1], good[:-12],
                    good + b"trailing", bad_crc, png(filter_type=5),
                    png(raw=b"too short"), png(compressed=zlib.compress(b"x" * 10000)),
                    png(compressed=zlib.compress(b"\x00" * 200)[:-2]),
                    png(compressed=zlib.compress(b"\x00" * 200) + b"extra")]
        for i, data in enumerate(fixtures):
            with self.subTest(case=i):
                path = self.write_fixture(data)
                self.assertIsNone(images._png_near_white_edge_ratio(path))
                with self.assertRaises((ValueError, zlib.error)):
                    images._detect_ext_and_finalize(path, os.path.join(self.output, "published"))
                self.assertFalse(Path(self.output, "published.png").exists())

    def test_huge_dimensions_and_chunk_length_fail_before_decompression(self):
        huge = (images.PNG_MAGIC
                + chunk(b"IHDR", struct.pack(">IIBBBBB", 0xffffffff, 0xffffffff, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", b"x") + chunk(b"IEND", b""))
        overflow = images.PNG_MAGIC + struct.pack(">I", 0xffffffff) + b"IHDR"
        for data in (huge, overflow):
            with patch.object(images.zlib, "decompressobj") as decompress:
                self.assertIsNone(images._png_near_white_edge_ratio(self.write_fixture(data)))
                decompress.assert_not_called()

    def test_file_size_and_decode_cap(self):
        path = self.write_fixture(png())
        with patch.object(images, "MAX_IMAGE_BYTES", 16):
            self.assertIsNone(images._png_near_white_edge_ratio(path))
        with patch.object(images, "MAX_PNG_DECOMPRESSED_BYTES", 16):
            self.assertIsNone(images._png_near_white_edge_ratio(path))

    def test_invalid_palette_index_rejected(self):
        data = png(color=(1,), color_type=3, extras=chunk(b"PLTE", b"\xff\xff\xff"))
        self.assertIsNone(images._png_near_white_edge_ratio(self.write_fixture(data)))


class GenerationTests(OfflineTest):
    def test_known_violations_never_publish_or_propagate(self):
        ctx, sink = self.context(), {"main_image": "stale"}
        with patch.object(images, "download_file", side_effect=self.download):
            path = self.generate_one(ctx, sink, compliance=lambda url: True, critique_retries=100)
        self.assertIsNone(path)
        self.assertEqual(sink, {})
        self.assertEqual(len(ctx["task_client"].calls), 3)
        self.assertEqual([c[1] for c in ctx["task_client"].calls], ["primary", "fallback", "last"])
        quality = ctx["image_quality"]["main_image"]
        self.assertEqual(quality["status"], "rejected")
        self.assertEqual(quality["checks"]["compliance"], "failed")
        self.assertIsNone(quality["path"])
        self.assertEqual(os.listdir(self.output), [])

    def test_rejected_url_replaced_only_after_accepted_fallback(self):
        ctx, sink = self.context(), {}
        compliance = Mock(side_effect=[True, False])
        def download(url, destination, **kwargs):
            self.assertEqual(sink, {})
            return self.download(url, destination, **kwargs)
        with patch.object(images, "download_file", side_effect=download):
            path = self.generate_one(ctx, sink, compliance=compliance)
        self.assertEqual(path, os.path.join(self.output, "main_image.png"))
        self.assertEqual(sink, {"main_image": "https://generated.invalid/2.png"})
        self.assertEqual(ctx["image_quality"]["main_image"]["model"], "fallback")

    def test_bad_image_format_retried_without_checks_or_publication(self):
        ctx, sink = self.context(), {}
        def download(url, destination, **kwargs):
            Path(destination).write_bytes(b"<html>error</html>")
        with patch.object(images, "download_file", side_effect=download):
            self.assertIsNone(self.generate_one(ctx, sink))
        self.assertEqual(len(ctx["task_client"].calls), 3)
        self.assertEqual(ctx["chat"].calls, [])
        self.assertEqual(ctx["image_quality"]["main_image"]["checks"]["format"], "failed")
        self.assertEqual(sink, {})

    def test_dark_main_image_never_publish(self):
        ctx = self.context()
        def download(url, destination, **kwargs):
            Path(destination).write_bytes(png(color=(30, 30, 30)))
        with patch.object(images, "download_file", side_effect=download):
            self.assertIsNone(self.generate_one(ctx))
        self.assertEqual(ctx["image_quality"]["main_image"]["checks"]["white_background"], "failed")
        self.assertEqual(len(ctx["task_client"].calls), 3)
        retry_prompt = ctx["task_client"].calls[1][2]["messages"][0]["content"][-1]["text"]
        self.assertIn("FLAT SOLID PURE WHITE", retry_prompt)

    def test_malformed_and_low_scores_never_publish(self):
        low = report(score=10)
        low["scores"]["product_fidelity"] = 4
        for value in ({"total": 40, "verdict": "accept"}, low):
            ctx = self.context(chat=FakeChat(value))
            with patch.object(images, "download_file", side_effect=self.download):
                self.assertIsNone(self.generate_one(ctx))
            self.assertEqual(ctx["image_quality"]["main_image"]["checks"]["critic"], "failed")
            self.assertEqual(len(ctx["task_client"].calls), 3)

    def test_unknown_checks_keep_review_path_not_canonical(self):
        for ctx in (self.context(chat=None), self.context(chat=FakeChat(report(verdict="unknown"))),
                    self.context(chat=FakeChat(compliance="UNKNOWN"))):
            sink = {}
            with patch.object(images, "download_file", side_effect=self.download):
                path = self.generate_one(ctx, sink)
            self.assertTrue(path.endswith(".needs_review.png"))
            self.assertFalse(Path(self.output, "main_image.png").exists())
            self.assertEqual(ctx["image_quality"]["main_image"]["status"], "needs_review")
            self.assertEqual(ctx["image_quality"]["main_image"]["path"], path)
            self.assertEqual(len(sink), 1)

    def test_openai_reference_loss_disabled_by_default(self):
        openai = Mock()
        ctx = self.context(openai_image=openai)
        with patch.object(images, "submit_image_task", side_effect=dsapi.ApiError("unavailable")) as submit:
            self.assertIsNone(self.generate_one(ctx))
        self.assertEqual(submit.call_count, 3)
        openai.generate.assert_not_called()

    def test_authorized_openai_uses_same_gates_and_total_cap(self):
        for violation in (True, False):
            with self.subTest(violation=violation):
                openai = Mock()
                openai.generate.return_value = [CANDIDATE]
                ctx = self.context(openai_image=openai, allow_unreferenced_image_fallback=True)
                sink = {}
                with patch.object(images, "submit_image_task", side_effect=dsapi.ApiError("unavailable")) as submit, \
                        patch.object(images, "download_file", side_effect=self.download):
                    path = self.generate_one(ctx, sink, compliance=lambda url: violation)
                self.assertEqual(submit.call_count + openai.generate.call_count, 3)
                quality = ctx["image_quality"]["main_image"]
                self.assertEqual(quality["checks"]["source_reference"], "unknown")
                if violation:
                    self.assertIsNone(path)
                    self.assertEqual(quality["status"], "rejected")
                    self.assertEqual(sink, {})
                else:
                    self.assertTrue(path.endswith(".needs_review.png"))
                    self.assertEqual(quality["status"], "needs_review")
                self.assertFalse(Path(self.output, "main_image.png").exists())

    def test_authorized_openai_cannot_bypass_format_or_white_gate(self):
        for data, gate in ((b"not an image", "format"), (png(color=(0, 0, 0)), "white_background")):
            openai = Mock()
            openai.generate.return_value = [CANDIDATE]
            ctx = self.context(openai_image=openai, allow_unreferenced_image_fallback=True)
            def download(url, destination, **kwargs):
                Path(destination).write_bytes(data)
            with patch.object(images, "submit_image_task", side_effect=dsapi.ApiError("unavailable")), \
                    patch.object(images, "download_file", side_effect=download):
                self.assertIsNone(self.generate_one(ctx))
            self.assertEqual(ctx["image_quality"]["main_image"]["checks"][gate], "failed")

    def test_expired_deadline_stops_generation_and_download(self):
        ctx = self.context()
        with patch.object(images, "download_file") as download:
            self.assertIsNone(self.generate_one(ctx, deadline=0))
        self.assertEqual(ctx["task_client"].calls, [])
        download.assert_not_called()

    def test_deadline_after_generation_prevents_download(self):
        ctx = self.context()
        clock = [0]
        def submit(*args, **kwargs):
            clock[0] = 20
            return {"results": [{"url": CANDIDATE}]}
        with patch.object(images.time, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(images, "submit_image_task", side_effect=submit), \
                patch.object(images, "download_file") as download:
            self.assertIsNone(self.generate_one(ctx, deadline=10))
        download.assert_not_called()
        self.assertIn("deadline", ctx["image_quality"]["main_image"]["reasons"][0])

    def test_deadline_after_quality_check_prevents_publication(self):
        ctx, sink = self.context(), {}
        clock = [0]
        def compliance(url):
            clock[0] = 20
            return False
        with patch.object(images.time, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(images, "download_file", side_effect=self.download):
            self.assertIsNone(self.generate_one(ctx, sink, deadline=10, compliance=compliance))
        self.assertEqual(sink, {})
        self.assertEqual(os.listdir(self.output), [])

    def test_transport_layout_fallback_always_keeps_source(self):
        task = Mock()
        task.generate.side_effect = [dsapi.ApiError("multi unsupported", status=400), dsapi.ApiError("endpoint unsupported", status=404),
                                     {"results": [{"url": CANDIDATE}]}]
        images.submit_image_task(task, "model", "prompt", [SOURCE, SOURCE_TWO], images.MAIN_SIZE,
                                 time.monotonic() + 60, negative_prompt="slot-specific")
        self.assertEqual(task.generate.call_count, 3)
        for call in task.generate.call_args_list:
            self.assertIn(SOURCE, json.dumps(call.args[2]))
            self.assertEqual(call.args[3]["negative_prompt"], "slot-specific")
            self.assertEqual(call.args[3]["n"], 1)

    def test_six_jobs_no_generated_anchor_all_metadata_present(self):
        ctx = self.context(anchor_url=CANDIDATE)
        with patch.object(images, "download_file", side_effect=self.download), \
                patch.object(images, "generate_anchor", side_effect=AssertionError("No anchor generation")):
            paths = images.generate_images(ctx)
        self.assertEqual(len(paths), 6)
        self.assertEqual(len(ctx["task_client"].calls), 6)
        self.assertEqual(ctx["anchor_url"], SOURCE)
        self.assertTrue(ctx["main_image_url"].startswith("https://generated.invalid/"))
        for name, quality in ctx["image_quality"].items():
            self.assertEqual(quality["status"], "accepted")
            self.assertEqual(quality["path"], paths[name])
            self.assertTrue(all(key in quality for key in ("status", "checks", "reasons", "model", "path")))
        for call in ctx["task_client"].calls:
            content = call[2]["messages"][0]["content"]
            self.assertEqual([p["image"] for p in content if "image" in p], [SOURCE, SOURCE_TWO])

    def test_failed_or_review_main_does_not_leak_to_video(self):
        for chat, status in ((FakeChat(compliance="YES logo"), "rejected"), (None, "needs_review")):
            ctx = self.context(chat=chat, main_image_url="stale", anchor_url=CANDIDATE)
            with patch.object(images, "download_file", side_effect=self.download):
                images.generate_images(ctx)
            self.assertIsNone(ctx["main_image_url"])
            self.assertEqual(ctx["anchor_url"], SOURCE)
            self.assertEqual(ctx["image_quality"]["main_image"]["status"], status)

    def test_missing_source_fails_without_generation(self):
        ctx = self.context(product={"subject": "skirt", "images": []})
        self.assertEqual(images.generate_images(ctx), {})
        self.assertEqual(ctx["task_client"].calls, [])
        self.assertEqual(len(ctx["image_quality"]), 6)
        self.assertIsNone(ctx["anchor_url"])

    def test_actual_task_client_with_mock_http_transport(self):
        # Dummy credentials are constructed locally, never read from the environment.
        task = dsapi.TaskClient("offline-placeholder", "https://transport.invalid/api/v1")
        payload = json.dumps({"output": {"results": [{"url": CANDIDATE}]}}).encode()
        ctx, sink = self.context(task_client=task), {}
        with patch.object(dsapi, "_http_request", return_value=(200, payload, {})) as transport, \
                patch.object(images, "download_file", side_effect=self.download):
            path = self.generate_one(ctx, sink)
        self.assertTrue(path.endswith("main_image.png"))
        transport.assert_called_once()
        request = transport.call_args.kwargs["data"]
        self.assertEqual(request["input"]["messages"][0]["content"][0]["image"], SOURCE)
        self.assertEqual(request["parameters"]["n"], 1)
        self.assertEqual(sink["main_image"], CANDIDATE)

    def test_unsolicited_extra_urls_do_not_expand_candidate_budget(self):
        ctx = self.context()
        ctx["task_client"].generate = Mock(return_value={
            "results": [{"url": f"https://generated.invalid/{i}.png"} for i in range(30)]})
        with patch.object(images, "download_file", side_effect=self.download) as download:
            self.assertIsNone(self.generate_one(ctx, compliance=lambda url: True))
        self.assertEqual(download.call_count, 3)
        self.assertEqual(ctx["task_client"].generate.call_count, 3)

    def test_failed_download_cleans_partial_and_does_not_propagate(self):
        ctx, sink = self.context(), {}
        def download(url, destination, **kwargs):
            Path(destination + ".part").write_bytes(b"partial")
            raise OSError("mock transport interrupted")
        with patch.object(images, "download_file", side_effect=download):
            self.assertIsNone(self.generate_one(ctx, sink))
        self.assertEqual(sink, {})
        self.assertEqual(os.listdir(self.output), [])
        self.assertEqual(ctx["image_quality"]["main_image"]["status"], "failed")

    def test_structural_jpeg_only_retained_for_review(self):
        def segment(marker, body):
            return b"\xff" + bytes([marker]) + struct.pack(">H", len(body) + 2) + body
        # Structurally readable, but no stdlib entropy decoder can certify this scan.
        data = (b"\xff\xd8" + segment(0xc0, b"\x08\x00\x08\x00\x08\x01\x01\x11\x00")
                + segment(0xda, b"\x01\x01\x00\x00\x3f\x00") + b"\x11\xff\xd9")
        ctx = self.context()
        def download(url, destination, **kwargs):
            Path(destination).write_bytes(data)
        with patch.object(images, "download_file", side_effect=download):
            path = self.generate_one(ctx)
        self.assertTrue(path.endswith(".needs_review.jpeg"))
        quality = ctx["image_quality"]["main_image"]
        self.assertEqual(quality["status"], "needs_review")
        self.assertEqual(quality["checks"]["format"], "unknown")
        self.assertEqual(quality["checks"]["white_background"], "unknown")
        self.assertFalse(Path(self.output, "main_image.jpeg").exists())

    def test_deadline_stops_endpoint_layout_fallback(self):
        task = Mock()
        clock = [0]
        def fail(*args, **kwargs):
            clock[0] = 20
            raise dsapi.ApiError("first endpoint unavailable", status=404)
        task.generate.side_effect = fail
        with patch.object(images.time, "monotonic", side_effect=lambda: clock[0]):
            with self.assertRaises(TimeoutError):
                images.submit_image_task(task, "model", "prompt", [SOURCE, SOURCE_TWO], images.MAIN_SIZE, 10)
        task.generate.assert_called_once()

    def test_nonwhite_lifestyle_not_subject_to_main_white_gate(self):
        ctx = self.context()
        def download(url, destination, **kwargs):
            Path(destination).write_bytes(png(color=(30, 30, 30)))
        with patch.object(images, "download_file", side_effect=download):
            path = self.generate_one(ctx, slot_name="detail_image_4", white_bg=False,
                                     dest_base=os.path.join(self.output, "detail_image_4"))
        self.assertTrue(path.endswith("detail_image_4.png"))
        self.assertEqual(ctx["image_quality"]["detail_image_4"]["checks"]["white_background"], "not_applicable")


if __name__ == "__main__":
    unittest.main()
