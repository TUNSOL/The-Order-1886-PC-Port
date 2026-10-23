from paths import ROOT  # noqa: F401 - adds scripts/ to sys.path
import struct
import unittest

from order_fps import (ANCHOR, ANCHOR_TO_INTERVAL, FRAME_TIME_PATTERNS, INTERVAL,
                       fps_writes, locate)


def elf_with_segment(address, size=0x1000):
    offset = 0x100
    elf = bytearray(offset + size)
    struct.pack_into('<Q', elf, 0x20, 0x40)
    struct.pack_into('<HH', elf, 0x36, 56, 1)
    struct.pack_into('<IIQQQQQQ', elf, 0x40, 1, 1, offset, address, 0, size, size, 0x1000)
    return elf, offset


def add_frame_patterns(elf, offset, address, first_at=0x100):
    targets = []
    for index, (spec, immediate_at) in enumerate(FRAME_TIME_PATTERNS):
        pattern = bytes(0xa0 + index if token == '??' else int(token, 16)
                        for token in spec.split())
        at = first_at + index * 0x80
        elf[offset + at:offset + at + len(pattern)] = pattern
        targets.append(address + at + immediate_at)
    return targets


class OrderFrameRateTests(unittest.TestCase):
    def test_reference_instruction_supports_30_60_and_120(self):
        target, opcode = INTERVAL
        elf, offset = elf_with_segment(0x450000)
        at = offset + target - 0x450000
        elf[at:at + len(opcode)] = opcode
        struct.pack_into('<I', elf, at + len(opcode), 2)
        frame_targets = add_frame_patterns(elf, offset, 0x450000)

        self.assertEqual(locate(elf), target)
        for mode, interval in [('30', 2), ('60', 1)]:
            self.assertEqual(fps_writes(elf, mode),
                             [(target + len(opcode), struct.pack('<I', interval))])
        self.assertEqual(fps_writes(elf, '120'),
                         [(target + len(opcode), struct.pack('<I', 0))] +
                         [(frame_target, struct.pack('<I', 8333))
                          for frame_target in frame_targets])

    def test_shifted_instruction_is_found_from_validated_anchor(self):
        elf, offset = elf_with_segment(0x500000)
        anchor_at = 0x80
        elf[offset + anchor_at:offset + anchor_at + len(ANCHOR)] = ANCHOR
        instruction = offset + anchor_at + ANCHOR_TO_INTERVAL
        elf[instruction:instruction + 2] = INTERVAL[1][:2]
        struct.pack_into('<I', elf, instruction + len(INTERVAL[1]), 2)
        frame_targets = add_frame_patterns(elf, offset, 0x500000, 0x300)

        target = 0x500000 + anchor_at + ANCHOR_TO_INTERVAL
        self.assertEqual(locate(elf), target)
        self.assertEqual(fps_writes(elf, '120'),
                         [(target + len(INTERVAL[1]), struct.pack('<I', 0))] +
                         [(frame_target, struct.pack('<I', 8333))
                          for frame_target in frame_targets])

    def test_unknown_mode_and_unexpected_original_are_rejected(self):
        elf, offset = elf_with_segment(0x450000)
        target, opcode = INTERVAL
        at = offset + target - 0x450000
        elf[at:at + len(opcode)] = opcode
        struct.pack_into('<I', elf, at + len(opcode), 7)
        with self.assertRaisesRegex(ValueError, 'intervalo inesperado'):
            fps_writes(elf, '120')
        with self.assertRaisesRegex(ValueError, '30, 60 ou 120'):
            fps_writes(elf, '90')


if __name__ == '__main__':
    unittest.main()
