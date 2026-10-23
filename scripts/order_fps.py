"""BB_ORDER_FPS=60/120: frame-rate unlock for The Order 01.02.

illusion0001's published GoldHEN patch changes the game's vsync interval at eboot.bin
0x8507c4 (image 0x4507c4): 2 vblanks per frame is 30 FPS and 1 gives 60 FPS. The
same validated instruction accepts 0 for an uncapped producer; bbport's independent
``fps_limit`` then caps presentation at 120 FPS.

The original patch warns that chapters 6 and 9 can softlock during QTEs above 30 FPS.
120 FPS is additionally experimental and may expose animation or physics timing bugs."""
import struct


def exec_segments(elf):
    phoff, = struct.unpack_from('<Q', elf, 0x20)
    entry_size, count = struct.unpack_from('<HH', elf, 0x36)
    for index in range(count):
        kind, flags, offset, address, _, size, _, _ = struct.unpack_from(
            '<IIQQQQQQ', elf, phoff + index * entry_size)
        if kind == 1 and flags & 1:
            yield offset, address, size


def elf_offset(elf, target, length):
    for offset, address, size in exec_segments(elf):
        if address <= target and target + length <= address + size:
            return offset + target - address
    raise ValueError(f'FPS: {target:#x} fora de segmento executavel')

# movl $imm32, rel32(%rip): opcode, displacement, then the interval (patched at +6).
INTERVAL = (0x4507be, bytes.fromhex('c7 05 8c 05 17 01'))
# The stores just before it (rdx into 0xc58(%rbx); test r14d; jz; call) locate the
# instruction when another dump has it elsewhere.
ANCHOR = bytes.fromhex('48 89 93 58 0c 00 00 45 85 f6 74 08 48 89 df e8')
ANCHOR_TO_INTERVAL = 0x4507be - 0x4507aa  # past the call rel32
INTERVALS = {'30': 2, '60': 1, '120': 0}

# The experimental 120 FPS path also lowers the engine's four 33,333 us frame-time clamps.
# These signatures and 8,333 us value are carried by the open-source theorder1886-port patch
# database; addresses are deliberately not trusted, so another 01.02 dump must match each
# complete instruction pattern exactly once before any write is emitted.
FRAME_TIME_PATTERNS = (
    ('49 69 97 18 01 00 00 35 82 00 00 48 39 d1', 7),
    ('48 69 c2 35 82 00 00 e9 ?? ?? ?? ??', 3),
    ('48 69 c1 35 82 00 00 eb ??', 3),
    ('48 c7 ?? 80 00 00 00 35 82 00 00 c7 ?? 7c 01 00 00 00', 7),
)


def _pattern_sites(elf, spec):
    pattern = tuple(None if token == '??' else int(token, 16) for token in spec.split())
    runs = []
    start = 0
    while start < len(pattern):
        while start < len(pattern) and pattern[start] is None:
            start += 1
        end = start
        while end < len(pattern) and pattern[end] is not None:
            end += 1
        if end > start:
            runs.append((end - start, start, bytes(pattern[start:end])))
        start = end
    _, run_at, needle = max(runs)
    found = []
    for offset, address, size in exec_segments(elf):
        segment = elf[offset:offset + size]
        at = segment.find(needle)
        while at >= 0:
            candidate = at - run_at
            if 0 <= candidate <= len(segment) - len(pattern) and all(
                    byte is None or segment[candidate + index] == byte
                    for index, byte in enumerate(pattern)):
                found.append(address + candidate)
            at = segment.find(needle, at + 1)
    return found


def frame_time_writes(elf, micros):
    writes = []
    for spec, immediate_at in FRAME_TIME_PATTERNS:
        found = _pattern_sites(elf, spec)
        if len(found) != 1:
            raise ValueError(f'FPS: constante de frame nao encontrada ({len(found)} ocorrencias)')
        target = found[0] + immediate_at
        start = elf_offset(elf, target, 4)
        current, = struct.unpack_from('<I', elf, start)
        if current != 33333:
            raise ValueError(f'FPS: constante de frame inesperada {current} em {target:#x}')
        writes.append((target, struct.pack('<I', micros)))
    if len({target for target, _ in writes}) != len(writes):
        raise ValueError('FPS: assinaturas de frame apontam para o mesmo endereco')
    return writes


def locate(elf):
    target, opcode = INTERVAL
    try:
        start = elf_offset(elf, target, len(opcode) + 4)
    except ValueError:
        start = None
    if start is not None and elf[start:start + len(opcode)] == opcode:
        return target
    found = []
    for offset, address, size in exec_segments(elf):
        segment = elf[offset:offset + size]
        at = segment.find(ANCHOR)
        while at >= 0:
            candidate = address + at + ANCHOR_TO_INTERVAL
            start = offset + at + ANCHOR_TO_INTERVAL
            # Same store into the same global, so the displacement shifts with the code.
            if elf[start:start + 2] == opcode[:2]:
                found.append(candidate)
            at = segment.find(ANCHOR, at + 1)
    if len(found) != 1:
        raise ValueError(f'FPS: intervalo de vsync nao encontrado ({len(found)} ocorrencias); eboot nao suportado')
    print(f'FPS: instrucao deslocada {found[0] - target:+#x} em relacao ao eboot de referencia')
    return found[0]


def fps_writes(elf, mode):
    if mode not in INTERVALS:
        raise ValueError(f'BB_ORDER_FPS: modo nao suportado: {mode} (use 30, 60 ou 120)')
    target = locate(elf)
    start = elf_offset(elf, target, 10)
    current, = struct.unpack_from('<I', elf, start + 6)
    if current not in INTERVALS.values():
        raise ValueError(f'FPS: intervalo inesperado {current} em {target:#x}')
    wanted = INTERVALS[mode]
    writes = [(target + 6, struct.pack('<I', wanted))]
    if mode == '120':
        writes += frame_time_writes(elf, 8333)
    print(f'The Order: {mode} FPS (intervalo de vsync {current} -> {wanted}'
          + (', 4 limites de frame 33333 -> 8333 us)' if mode == '120' else ')')
          + ('; ATENCAO: experimental; QTEs dos capitulos 6 e 9 travam, use 30 FPS para passar'
             if mode != '30' else ''))
    return writes
