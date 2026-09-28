"""Bounded ISO BMFF inspection using only the standard library.

``valid`` means a supported, internally consistent *container*, NOT successful
codec decoding or verified playback/visual quality. Single rate-1 edits (with an
optional leading empty edit) are supported; complex timelines are unsupported,
not evidence of corruption. Media payloads are never loaded or decoded.
"""
import os
import stat
import struct
from collections import namedtuple
from fractions import Fraction

MAX_VIDEO_BYTES = 200_000_000  # strictly less than 200 MB
_MAX_BOXES = 20_000
_MAX_ENTRIES = 1_000_000
Box = namedtuple("Box", "kind start end")


class _Invalid(ValueError):
    pass


class _Unsupported(ValueError):
    pass


class _Reader:
    def __init__(self, stream, size):
        self.stream = stream
        self.size = size
        self.box_count = 0

    def read(self, offset, length, end=None):
        if length < 0 or offset < 0 or offset + length > (self.size if end is None else end):
            raise _Invalid("truncated box or field")
        self.stream.seek(offset)
        data = self.stream.read(length)
        if len(data) != length:
            raise _Invalid("truncated file")
        return data

    def unpack(self, fmt, offset, end):
        return struct.unpack(fmt, self.read(offset, struct.calcsize(fmt), end))

    def boxes(self, start, end):
        result = []
        while start < end:
            self.box_count += 1
            if self.box_count > _MAX_BOXES:
                raise _Invalid("too many boxes")
            length, kind = self.unpack(">I4s", start, end)
            header = 8
            if length == 1:
                length, = self.unpack(">Q", start + 8, end)
                header = 16
            elif length == 0:
                length = end - start
            if length < header or length > end - start:
                raise _Invalid("invalid or truncated box size")
            result.append(Box(kind, start + header, start + length))
            start += length
        return result

    @staticmethod
    def one(boxes, kind):
        found = [box for box in boxes if box.kind == kind]
        if len(found) != 1:
            raise _Invalid("missing or duplicate " + kind.decode("ascii"))
        return found[0]

    def full_version(self, box, allowed=(0,)):
        data = self.read(box.start, 4, box.end)
        if data[0] not in allowed:
            raise _Unsupported("unsupported " + box.kind.decode("ascii") + " version")
        return data[0]

    def timing(self, box):
        version = self.full_version(box, (0, 1))
        minimum = (100 if version == 0 else 112) if box.kind == b"mvhd" else (24 if version == 0 else 36)
        self.read(box.start, minimum, box.end)
        offset = box.start + (12 if version == 0 else 20)
        scale, ticks = self.unpack(">II" if version == 0 else ">IQ", offset, box.end)
        if not scale or ticks in (0, (1 << (32 if version == 0 else 64)) - 1):
            raise _Invalid("unknown or zero media duration/timescale")
        return scale, ticks

    def table(self, box, fmt, versions=(0,)):
        self.full_version(box, versions)
        count, = self.unpack(">I", box.start + 4, box.end)
        stride = struct.calcsize(fmt)
        if not 0 < count <= _MAX_ENTRIES or box.end - box.start != 8 + count * stride:
            raise _Invalid("invalid " + box.kind.decode("ascii") + " entry count")
        # Yield entries without allocating a table from an untrusted count.
        return count, (self.unpack(fmt, box.start + 8 + i * stride, box.end) for i in range(count))

    def presentation(self, boxes, stts, sample_count, sample_ticks):
        """Composition coverage, including B-frame offsets; never use DTS alone."""
        ctts = [b for b in boxes if b.kind == b"ctts"]
        if not ctts:
            return 0, sample_ticks
        ctts = self.one(ctts, b"ctts")
        version = self.full_version(ctts, (0, 1))
        _, entries = self.table(ctts, ">II" if version == 0 else ">Ii", (0, 1))
        _, times = self.table(stts, ">II")
        remaining = decoded = covered = 0
        intervals = []
        for count, delta in times:
            while count:
                if not remaining:
                    entry = next(entries, None)
                    if entry is None or not entry[0]:
                        raise _Invalid("invalid ctts sample count")
                    remaining, offset = entry
                take = min(count, remaining)
                intervals.append((decoded + offset, decoded + offset + take * delta))
                decoded += take * delta
                covered += take
                remaining -= take
                count -= take
        if remaining or next(entries, None) is not None or covered != sample_count:
            raise _Invalid("ctts sample count disagrees with stts")
        intervals.sort()
        start, end = intervals[0]
        for begin, finish in intervals[1:]:
            if begin != end:
                raise _Unsupported("gapped or overlapping composition timeline is unsupported")
            end = finish
        return start, end

    def edited_timeline(self, boxes, movie_scale, media_scale, coverage):
        start, end = coverage
        edits = [b for b in boxes if b.kind == b"edts"]
        if not edits:
            start = max(0, start)
            if end <= start:
                raise _Invalid("no presenting media samples")
            return Fraction(end - start, media_scale), Fraction(start, media_scale)
        edts = self.one(edits, b"edts")
        elst = self.one(self.boxes(edts.start, edts.end), b"elst")
        version = self.full_version(elst, (0, 1))
        count, entries = self.table(elst, ">Iihh" if version == 0 else ">Qqhh", (0, 1))
        supported = self.read(elst.start + 1, 3, elst.end) == b"\0\0\0"
        selected = []
        # Check every declared entry/byte even when the timeline is unsupported.
        for duration, media_time, rate, fraction in entries:
            if duration <= 0 or media_time < -1:
                raise _Invalid("invalid elst duration or media_time")
            supported = supported and (rate, fraction) == (1, 0)
            if len(selected) < 2:
                selected.append((duration, media_time))
        if (not supported or count > 2 or selected[-1][1] < 0
                or (count == 2 and selected[0][1] != -1)):
            raise _Unsupported("complex edit-list timeline is unsupported")
        empty_ticks = selected[0][0] if count == 2 else 0
        duration, media_time = selected[-1]
        # elst durations use mvhd units; media_time and CTTS use mdhd units.
        requested_end = media_time + Fraction(duration * media_scale, movie_scale)
        visible_start, visible_end = max(start, media_time), min(end, requested_end)
        if visible_end <= visible_start:
            raise _Invalid("edit list selects no presenting media samples")
        # Clip to actual sample coverage: empty edits/padding never count as content.
        actual = Fraction(visible_end - visible_start, media_scale)
        begins = Fraction(empty_ticks, movie_scale) + Fraction(visible_start - media_time, media_scale)
        return actual, begins

    def samples(self, stbl, handler, mdhd, mdats):
        boxes = self.boxes(stbl.start, stbl.end)
        stsd = self.one(boxes, b"stsd")
        self.full_version(stsd)
        count, = self.unpack(">I", stsd.start + 4, stsd.end)
        descriptions = self.boxes(stsd.start + 8, stsd.end)
        if not descriptions or count != len(descriptions):
            raise _Invalid("missing sample description")
        for description in descriptions:
            # SampleEntry + VisualSampleEntry / AudioSampleEntry fixed fields.
            minimum = 78 if handler == b"vide" else 28
            self.read(description.start, minimum, description.end)
            reference, = self.unpack(">H", description.start + 6, description.end)
            if reference != 1:
                raise _Unsupported("unsupported external sample data reference")
            if handler == b"vide":
                w, h = self.unpack(">HH", description.start + 24, description.end)
                if not w or not h:
                    raise _Invalid("zero sample dimensions")
            if description.kind in (b"encv", b"enca"):
                raise _Unsupported("encrypted media is unsupported")

        stts = self.one(boxes, b"stts")
        _, times = self.table(stts, ">II")
        sample_count = sample_ticks = 0
        for n, delta in times:
            if not n or not delta:
                raise _Invalid("zero sample count or duration")
            sample_count += n
            sample_ticks += n * delta
        if sample_count > _MAX_ENTRIES:
            raise _Invalid("too many media samples")
        scale, ticks = self.timing(mdhd)
        # Reconcile after applying edits: some muxers store the presentation
        # duration here, excluding encoder priming still present in stts.
        stsz = self.one(boxes, b"stsz")
        self.full_version(stsz)
        fixed_size, size_count = self.unpack(">II", stsz.start + 4, stsz.end)
        if size_count != sample_count or stsz.end - stsz.start != 12 + (0 if fixed_size else size_count * 4):
            raise _Invalid("invalid sample sizes/count")
        if fixed_size:
            sizes = iter([fixed_size])  # fixed-size samples need no table
        else:
            sizes = (self.unpack(">I", stsz.start + 12 + i * 4, stsz.end)[0] for i in range(size_count))

        stsc = self.one(boxes, b"stsc")
        _, mappings = self.table(stsc, ">III")
        offsets = [b for b in boxes if b.kind in (b"stco", b"co64")]
        if len(offsets) != 1:
            raise _Invalid("missing or duplicate chunk offsets")
        chunk_count, chunks = self.table(offsets[0], ">I" if offsets[0].kind == b"stco" else ">Q")
        current = next(mappings)
        following = next(mappings, None)
        if current[0] != 1:
            raise _Invalid("first chunk mapping must start at 1")
        consumed = 0
        previous_end = 0
        for index, (offset,) in enumerate(chunks, 1):
            if following and not current[0] < following[0] <= chunk_count:
                raise _Invalid("invalid sample-to-chunk mapping order")
            if following and index == following[0]:
                current = following
                following = next(mappings, None)
            first, per_chunk, description_index = current
            if (not per_chunk or not 1 <= description_index <= count
                    or first > chunk_count or (following and not first < following[0] <= chunk_count)):
                raise _Invalid("invalid sample-to-chunk mapping")
            if consumed + per_chunk > sample_count:
                raise _Invalid("chunk sample count exceeds sample table")
            length = fixed_size * per_chunk
            if not fixed_size:
                length = 0
                for _ in range(per_chunk):
                    size = next(sizes)
                    if not size:
                        raise _Invalid("empty media sample")
                    length += size
            if length <= 0 or offset < previous_end:
                raise _Invalid("empty or overlapping media chunks")
            if not any(begin <= offset and offset + length <= end for begin, end in mdats):
                raise _Invalid("sample data is outside mdat")
            previous_end = offset + length
            consumed += per_chunk
        if consumed != sample_count or following:
            raise _Invalid("incomplete sample-to-chunk mapping")
        return scale, ticks, sample_ticks, self.presentation(boxes, stts, sample_count, sample_ticks)

    def track(self, trak, mdats, movie_scale):
        boxes = self.boxes(trak.start, trak.end)
        tkhd = self.one(boxes, b"tkhd")
        version = self.full_version(tkhd, (0, 1))
        self.read(tkhd.start, 84 if version == 0 else 96, tkhd.end)
        dimensions = tkhd.start + (76 if version == 0 else 88)
        w, h = self.unpack(">II", dimensions, tkhd.end)
        width, height = round(w / 65536), round(h / 65536)
        matrix = tkhd.start + (40 if version == 0 else 52)
        a, b, _, c, d = self.unpack(">iiiii", matrix, tkhd.end)
        if a == d == 0 and abs(b) == abs(c) == 65536:
            width, height = height, width
        mdia = self.one(boxes, b"mdia")
        media = self.boxes(mdia.start, mdia.end)
        hdlr = self.one(media, b"hdlr")
        self.full_version(hdlr)
        self.read(hdlr.start, 24, hdlr.end)
        handler = self.read(hdlr.start + 8, 4, hdlr.end)
        mdhd = self.one(media, b"mdhd")
        self.timing(mdhd)
        if handler not in (b"vide", b"soun"):
            return handler, None, None, None, None
        if handler == b"vide" and not (width > 0 and height > 0):
            raise _Invalid("zero video dimensions")
        minf = self.one(media, b"minf")
        stbl = self.one(self.boxes(minf.start, minf.end), b"stbl")
        scale, ticks, sample_ticks, coverage = self.samples(stbl, handler, mdhd, mdats)
        duration, start = self.edited_timeline(boxes, movie_scale, scale, coverage)
        has_edit = any(b.kind == b"edts" for b in boxes)
        if ticks != sample_ticks and not (has_edit and ticks == duration * scale):
            raise _Invalid("mdhd duration disagrees with sample/edit timing")
        return handler, float(duration), width, height, float(start)


def inspect_video(path):
    """Return a conservative structural MP4 report; never invoke a decoder.

    ``status=unsupported`` distinguishes unimplemented timelines from malformed
    files. Duration is video composition coverage intersected with its edit, not
    audio/movie duration; video_start_seconds locates content after empty edits.
    """
    result = {"valid": False, "status": "invalid", "duration_seconds": None,
              "video_start_seconds": None, "width": None,
              "height": None, "has_video": False, "has_audio": False, "errors": []}
    try:
        info = os.stat(path)
        if not stat.S_ISREG(info.st_mode):
            raise _Invalid("not a regular media file")
        if not 0 < info.st_size < MAX_VIDEO_BYTES:
            raise _Invalid("empty file or file exceeds the less-than-200-MB limit")
        with open(path, "rb") as stream:
            size = os.fstat(stream.fileno()).st_size
            if size != info.st_size:
                raise _Invalid("media changed during inspection")
            reader = _Reader(stream, size)
            top = reader.boxes(0, size)
            ftyp = reader.one(top, b"ftyp")
            if ftyp.end - ftyp.start < 8 or (ftyp.end - ftyp.start) % 4:
                raise _Invalid("invalid ftyp")
            moov = reader.one(top, b"moov")
            mdats = [(b.start, b.end) for b in top if b.kind == b"mdat" and b.end > b.start]
            if not mdats:
                raise _Invalid("missing nonempty mdat")
            movie = reader.boxes(moov.start, moov.end)
            if any(b.kind in (b"moof", b"mvex") for b in top + movie):
                raise _Unsupported("fragmented MP4 is unsupported")
            movie_scale, _ = reader.timing(reader.one(movie, b"mvhd"))
            tracks = [b for b in movie if b.kind == b"trak"]
            if not 0 < len(tracks) <= 128:
                raise _Invalid("missing or excessive tracks")
            video_tracks = []
            for track in tracks:
                handler, duration, width, height, start = reader.track(track, mdats, movie_scale)
                if handler == b"vide":
                    video_tracks.append((duration, width, height, start))
                elif handler == b"soun":
                    result["has_audio"] = True
            if not video_tracks:
                raise _Invalid("no video track")
            if len(video_tracks) != 1:
                raise _Unsupported("multiple video timelines are unsupported")
            duration, width, height, start = video_tracks[0]
            result.update(has_video=True, duration_seconds=duration, width=width, height=height,
                          video_start_seconds=start)
            if os.fstat(stream.fileno()).st_size != size:
                raise _Invalid("media changed during inspection")
            result.update(valid=True, status="valid")
    except _Unsupported as exc:
        result["status"] = "unsupported"
        result["errors"].append(str(exc))
    except _Invalid as exc:
        result["errors"].append(str(exc))
    except (OSError, ValueError, TypeError, OverflowError, struct.error, StopIteration):
        result["errors"].append("unreadable or malformed media file")
    return result
