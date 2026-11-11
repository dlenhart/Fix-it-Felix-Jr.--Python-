"""The roof ending's animation records, from the exe animation table at 0x419800.

Every value is [EXE], read from the exe bytes. No pygame dependency.
"""

from types import MappingProxyType

from graphics.animation import Animation, AnimationFrame, AnimationMode


def _animation(mode: AnimationMode, *records: tuple[int, int, int, int]) -> Animation:
    return Animation(mode, tuple(AnimationFrame(*record) for record in records))


# [EXE] animation table 0x419800, read from the exe bytes. Records are
# (right frame, hold, origin x, origin y).
ROOF_ANIMATIONS: MappingProxyType[int, Animation] = MappingProxyType({
    2: _animation(AnimationMode.STATIC, (6, 0, 44, 39)),  # cloud
    3: _animation(AnimationMode.STATIC, (7, 0, 10, 47)),  # Felix standing
    5: _animation(AnimationMode.STATIC, (36, 0, 10, 47)),  # Felix looks at the door
    6: _animation(AnimationMode.LOOP, (27, 10, 10, 47), (28, 10, 10, 47)),  # eating the pie
    7: _animation(AnimationMode.LOOP, (30, 10, 10, 47), (29, 10, 10, 47)),  # kissed
    16: _animation(AnimationMode.ONCE, (31, 10, 10, 47), (32, 10, 10, 47)),  # hammer raised
    17: _animation(AnimationMode.ONCE, (26, 10, 10, 47), (27, 10, 10, 47), (28, 10, 10, 47)),
    18: _animation(AnimationMode.STATIC, (25, 0, 10, 47)),  # wearing the medal
    29: _animation(AnimationMode.ONCE, (90, 0, 33, 71)),  # Ralph standing
    30: _animation(AnimationMode.ONCE, (91, 0, 33, 71)),  # Ralph carried, lying
    31: _animation(AnimationMode.LOOP, (94, 8, 33, 71), (95, 8, 33, 71), (92, 8, 33, 71),
                   (93, 8, 33, 71)),  # Ralph tumbling
    32: _animation(AnimationMode.ONCE, (96, 10, 50, 38), (97, 10, 50, 38),
                   (98, 10, 50, 38)),  # Ralph lands in the mud
    50: _animation(AnimationMode.LOOP, (141, 6, 6, 23), (141, 6, 6, 24)),
    51: _animation(AnimationMode.LOOP, (142, 6, 6, 24), (142, 6, 6, 23)),
    52: _animation(AnimationMode.LOOP, (143, 6, 6, 23), (143, 6, 6, 24)),
    53: _animation(AnimationMode.LOOP, (144, 6, 6, 24), (144, 6, 6, 23)),
    54: _animation(AnimationMode.LOOP, (145, 6, 6, 23), (145, 6, 6, 24)),
    56: _animation(AnimationMode.STATIC, (147, 0, 6, 23)),  # frowning
    57: _animation(AnimationMode.STATIC, (148, 0, 6, 23)),
    58: _animation(AnimationMode.STATIC, (149, 0, 6, 23)),
    59: _animation(AnimationMode.STATIC, (150, 0, 6, 23)),
    60: _animation(AnimationMode.STATIC, (151, 0, 6, 23)),
    62: _animation(AnimationMode.ONCE, (153, 10, 22, 23), (154, 0, 14, 23)),  # holds out the pie
    63: _animation(AnimationMode.ONCE, (141, 9, 6, 23), (141, 9, 6, 27), (141, 9, 6, 35),
                   (155, 9, 2, 35), (155, 9, 4, 35), (141, 9, 6, 29),
                   (141, 9, 6, 23)),  # jumps up to kiss Felix
    70: _animation(AnimationMode.ONCE, (178, 10, 0, 0), (179, 30, 0, 0), (180, 30, 0, 0)),  # hatch
    71: _animation(AnimationMode.ONCE, (181, 20, 32, 95), (182, 20, 32, 95), (183, 20, 32, 95),
                   (184, 60, 32, 95), (184, 4, 40, 87), (185, 4, 48, 33),
                   (186, 4, 48, -3)),  # the medal
})
