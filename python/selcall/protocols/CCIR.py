import numpy as np

# ==========================
#  CCIR FREQUENCY AND SYMBOL DEFINITIONS
# ==========================
CCIR_FREQS = {
    "1": 1124, "2": 1197, "3": 1275, "4": 1358, "5": 1446,
    "6": 1540, "7": 1640, "8": 1747, "9": 1860, "0": 1981,
    "A": 2400, "B": 930,  "C": 2246, "D": 991,  "E": 2110
}
CCIR_SYMBOLS = list(CCIR_FREQS.keys())
CCIR_VALUES = np.array(list(CCIR_FREQS.values()), dtype=float)

# ==========================
#  PCCIR FREQUENCY AND SYMBOL DEFINITIONS
# ==========================
PCCIR_FREQS = {
    "1": 1124, "2": 1197, "3": 1275, "4": 1358, "5": 1446,
    "6": 1540, "7": 1640, "8": 1747, "9": 1860, "0": 1981,
    "A": 1050, "B": 930,  "C": 2400, "D": 991,  "E": 2110
}
PCCIR_SYMBOLS = list(PCCIR_FREQS.keys())
PCCIR_VALUES = np.array(list(PCCIR_FREQS.values()), dtype=float)

# ==========================
#  CCIR CODE LENGTH DEFINITIONS
# ==========================
CCIR_CODE_LEN_MS = {
    "CCIR-1": 100,
    "CCIR-2": 70,
    "CCIR-7": 70,
    "PCCIR": 100
}

# ==========================
#  CCIR REPEATER TONE DEFINITION
# ==========================
CCIR_TONE_CH_REPEATER = "E"
CCIR_TONE_CH_REPEATER_FREQ = CCIR_FREQS[CCIR_TONE_CH_REPEATER]

# ==========================
#  CCIR GROUP TONE DEFINITION
# ==========================
CCIR_TONE_CH_GROUP = "A"
CCIR_TONE_CH_GROUP_FREQ = CCIR_FREQS[CCIR_TONE_CH_GROUP]


# ==========================
#  PCCIR REPEATER TONE DEFINITION
# ==========================
PCCIR_TONE_CH_REPEATER = "E"
PCCIR_TONE_CH_REPEATER_FREQ = PCCIR_FREQS[PCCIR_TONE_CH_REPEATER]

# ==========================
#  PCCIR GROUP TONE DEFINITION
# ==========================
PCCIR_TONE_CH_GROUP = "A"
PCCIR_TONE_CH_GROUP_FREQ = PCCIR_FREQS[PCCIR_TONE_CH_GROUP]

# ==========================
#  PCCIR RESET TONE DEFINITION
# ==========================
CCIR_TONE_CH_RESET = "C"
CCIR_TONE_CH_RESET_FREQ = CCIR_FREQS[CCIR_TONE_CH_RESET]

# ==========================
#  ZVEI PAUSE TONE DEFINITION
# ==========================
CCIR_TONE_CH_PAUSE = "C"
CCIR_TONE_CH_EOM_FREQ = CCIR_FREQS[CCIR_TONE_CH_PAUSE]