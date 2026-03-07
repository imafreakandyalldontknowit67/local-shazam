"""Tunable constants for fingerprinting."""

# Audio decoding
SAMPLE_RATE = 11025

# Spectrogram (FFT)
FFT_WINDOW = 1024
OVERLAP_RATIO = 0.5
HOP_SIZE = int(FFT_WINDOW * (1 - OVERLAP_RATIO))  # 512

# Peak finding
PEAK_NEIGHBORHOOD = 10  # pixels in each direction for local max detection
MIN_PEAK_AMPLITUDE = 10  # minimum dB above floor to count as a peak

# Constellation hashing
FAN_VALUE = 5           # number of target peaks to pair with each anchor
FAN_VALUE_COMPACT = 3   # reduced fan value for --compact mode
TARGET_T_MIN = 1        # minimum time offset between anchor and target (frames)
TARGET_T_MAX = 100      # maximum time offset between anchor and target (frames)
TARGET_F_RANGE = 200    # maximum frequency bin distance for target peaks

# Hash encoding
HASH_BITS = 32          # output hash is 32-bit integer

# Database
BATCH_INSERT_SIZE = 100_000

# Matching
MIN_ALIGNED_HASHES = 5       # minimum aligned hashes to report a match
CONFIDENCE_HIGH = 0.20        # 20%+ = high confidence
CONFIDENCE_PROBABLE = 0.10    # 10-20% = probable
CONFIDENCE_POSSIBLE = 0.05   # 5-10% = possible

# Scanner
AUDIO_EXTENSIONS = frozenset({
    ".mp3", ".flac", ".wav", ".ogg", ".opus", ".m4a", ".aac",
    ".wma", ".alac", ".aiff", ".aif", ".ape", ".wv", ".mpc",
    ".mp4", ".mkv", ".webm", ".3gp",
})
FILE_HASH_BYTES = 8192  # first 8KB for identity hash
