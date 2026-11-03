"""Generate a silent, original Motion JPEG AVI for decoder integration tests."""

import struct

from fluentpy.qt import QtCore, QtGui


def video_fixture(path, frames=24, fps=12, source=None):
    width, height = (160, 90) if source is None else (source.width(), source.height())
    samples = []
    for number in range(frames):
        if source is None:
            image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_RGB32)
            image.fill(QtGui.QColor.fromHsv(number * 360 // frames, 160, 210))
        else:
            image = source.scaled(width, height)
        painter = QtGui.QPainter(image)
        if source is None:
            painter.fillRect(number * 5 % width, 20, 20, 40, QtGui.QColor("white"))
        else:
            painter.fillRect(
                30 + number * 5 % (width - 120), height - 20, 80, 4, QtGui.QColor("white")
            )
        painter.end()
        data = QtCore.QByteArray()
        buffer = QtCore.QBuffer(data)
        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "JPEG"):
            raise RuntimeError("JPEG image plugin is required for the video test")
        buffer.close()
        samples.append(bytes(data))

    def chunk(tag, data):
        return tag + struct.pack("<I", len(data)) + data + (b"\0" if len(data) % 2 else b"")

    maximum = max(map(len, samples))
    avih = struct.pack(
        "<14I",
        1000000 // fps,
        maximum * fps,
        0,
        0x10,
        frames,
        0,
        1,
        maximum,
        width,
        height,
        0,
        0,
        0,
        0,
    )
    strh = struct.pack(
        "<4s4sIHH8Ihhhh",
        b"vids",
        b"MJPG",
        0,
        0,
        0,
        0,
        1,
        fps,
        0,
        frames,
        maximum,
        0xFFFFFFFF,
        0,
        0,
        0,
        width,
        height,
    )
    strf = struct.pack(
        "<IiiHH4sIiiII", 40, width, height, 1, 24, b"MJPG", width * height * 3, 0, 0, 0, 0
    )
    stream = chunk(b"LIST", b"strl" + chunk(b"strh", strh) + chunk(b"strf", strf))
    header = chunk(b"LIST", b"hdrl" + chunk(b"avih", avih) + stream)
    movie = b""
    index = b""
    for sample in samples:
        index += struct.pack("<4sIII", b"00dc", 0x10, len(movie) + 4, len(sample))
        movie += chunk(b"00dc", sample)
    content = b"AVI " + header + chunk(b"LIST", b"movi" + movie) + chunk(b"idx1", index)
    path.write_bytes(chunk(b"RIFF", content))
    return path
