import numpy as np

# ==========================
#  ZVEI-1 FREQUENCY AND SYMBOL DEFINITIONS
# ==========================
ZVEI1_FREQS = {
    "1": 1060, "2": 1160, "3": 1270, "4": 1400, "5": 1530,
    "6": 1670, "7": 1830, "8": 2000, "9": 2200, "0": 2400,
    "A": 2800, "B": 810,  "C": 970, "D": 886,  "E": 2600
}
ZVEI1_SYMBOLS = list(ZVEI1_FREQS.keys())
ZVEI1_VALUES = np.array(list(ZVEI1_FREQS.values()), dtype=float)


# ==========================
#  ZVEI-2 FREQUENCY AND SYMBOL DEFINITIONS
# ==========================
ZVEI2_FREQS = {
    "1": 1060, "2": 1160, "3": 1270, "4": 1400, "5": 1530,
    "6": 1670, "7": 1830, "8": 2000, "9": 2200, "0": 2400,
    "A": 885, "B": 810,  "C": 740, "D": 680,  "E": 970
}
ZVEI2_SYMBOLS = list(ZVEI2_FREQS.keys())
ZVEI2_VALUES = np.array(list(ZVEI2_FREQS.values()), dtype=float)


# ==========================
#  ZVEI CODE LENGTH DEFINITIONS
# ==========================
ZVEI_TONE_MS = 70

# ==========================
#  ZVEI REPEATER TONE DEFINITION
# ==========================
ZVEI_TONE_CH_REPEATER = "E"
ZVEI_TONE_CH_REPEATER_FREQ = ZVEI1_FREQS[ZVEI_TONE_CH_REPEATER]

# ==========================
#  ZVEI GROUP TONE DEFINITION
# ==========================
ZVEI_TONE_CH_GROUP = "A"
ZVEI_TONE_CH_GROUP_FREQ = ZVEI1_FREQS[ZVEI_TONE_CH_GROUP]

# ==========================
#  ZVEI PAUSE TONE DEFINITION
# ==========================
ZVEI_TONE_CH_PAUSE = "C"  # FIXME: Some references say "E"
ZVEI_TONE_CH_EOM_FREQ = ZVEI1_FREQS[ZVEI_TONE_CH_PAUSE]