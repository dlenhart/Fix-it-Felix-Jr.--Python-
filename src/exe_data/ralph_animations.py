"""Ralph's play animations, from the exe animation table at 0x419800: (frame id, hold).

Every value is [EXE]. No pygame dependency.
"""

from graphics.animation import Animation, AnimationFrame, AnimationMode

RALPH_ORIGIN_Y = 71  # [EXE] every Ralph record stands the frame on his feet


def _ralph_animation(mode: AnimationMode, origin_x: int, *frames: tuple[int, int]) -> Animation:
    return Animation(mode, tuple(AnimationFrame(frame_id, hold, origin_x, RALPH_ORIGIN_Y)
                                 for frame_id, hold in frames))


ANIM_STANDING = _ralph_animation(AnimationMode.STATIC, 24, (75, 0))  # 20: FUN_0040e3f0, last-section pose
ANIM_WALK = _ralph_animation(AnimationMode.LOOP, 33, (78, 8), (79, 8))  # 23: FUN_0040df6f
ANIM_POUND = _ralph_animation(  # 24: FUN_0040d870 on arrival
    AnimationMode.ONCE, 33, (80, 6), (81, 12), (82, 6), (83, 6), (84, 6), (85, 6),
    (82, 6), (83, 6), (84, 6), (85, 6))
ANIM_RAGE = _ralph_animation(AnimationMode.LOOP, 33, (86, 6), (87, 6))  # 25: FUN_0040dd90
ANIM_FISTS_UP = _ralph_animation(AnimationMode.LOOP, 33, (80, 6), (81, 6))  # 26: rage wind-up, pose, ledge
ANIM_CLIMB = _ralph_animation(AnimationMode.LOOP, 33, (88, 6), (89, 6))  # 27: FUN_0040dbb0
