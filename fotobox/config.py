from dataclasses import dataclass
from .geometry import RectRel, abs_to_rel

@dataclass(frozen=True)
class Zones:
    # MAIN buttons
    main_take_1: RectRel
    main_take_2: RectRel
    main_take_4: RectRel
    main_last_image_frame: RectRel

    # PREVIEW frame
    preview_feed_frame: RectRel

    # FINAL frame + print buttons
    final_image_frame: RectRel
    final_print_0: RectRel
    final_print_1: RectRel
    final_print_2: RectRel
    final_print_3: RectRel

def default_zones() -> Zones:
    # MAIN:
    # 1 Bild: (290,370) zu (70,180)
    # 2 Bilder: (510,380) zu (290,180)
    # 4 Bilder: (720,380) zu (510,170)
    # last image frame: (950,390) zu (730,180)
    #
    # PREVIEW feed: (110,480) zu (910,120)
    #
    # FINAL frame: (180,390) zu (840,120)
    # Buttons:
    # 0: (330,580) zu (180,420)
    # 1: (350,580) zu (500,420)
    # 2: (520,580) zu (680,420)
    # 3: (690,580) zu (850,420)

    return Zones(
        main_take_1=abs_to_rel(290, 370, 70, 180),
        main_take_2=abs_to_rel(510, 380, 290, 180),
        main_take_4=abs_to_rel(720, 380, 510, 170),
        main_last_image_frame=abs_to_rel(950, 390, 730, 180),

        preview_feed_frame=abs_to_rel(110, 480, 910, 120),

        final_image_frame=abs_to_rel(180, 390, 840, 120),
        final_print_0=abs_to_rel(330, 580, 180, 420),
        final_print_1=abs_to_rel(350, 580, 500, 420),
        final_print_2=abs_to_rel(520, 580, 680, 420),
        final_print_3=abs_to_rel(690, 580, 850, 420),
    )

WINDOW_W = 1024
WINDOW_H = 600

GLOBAL_FONT_PATH = "assets/fonts/Pacifico-Regular.ttf"
