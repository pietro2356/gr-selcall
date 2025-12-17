"""
Embedded Python Block: SelCall Decoder
"""

import numpy as np
from gnuradio import gr
import pmt
import time

# Import logic from the provided library files
# Note: In a standard OOT module, imports might look like 'from my_module import ...'
from python.selcall.protocols.CCIR import *
from python.selcall.protocols.ZVEI import *
from python.selcall.core.SelectiveCalling import SelectiveCalling

class selcall_decoder(gr.sync_block):
    """
    SelCall Decoder Block for GNU Radio.
    Decodes CCIR/ZVEI protocols in real-time and controls an audio gate.
    """

    def __init__(self,
                 sample_rate=48000,
                 protocol="ZVEI-1",
                 target_code="50101",
                 code_length=5,
                 tone_duration_ms=0.0,
                 debug=False):

        # [A] Block Initialization
        # Standard GNU Radio Sync Block init (1:1 input/output ratio)
        gr.sync_block.__init__(
            self,
            name='SelCall Decoder',
            in_sig=[np.float32],
            out_sig=[np.float32]
        )

        # --- User Parameters ---
        self.fs = sample_rate
        self.protocol = protocol
        self.target_code = target_code
        self.code_length = code_length
        self.user_tone_ms = tone_duration_ms
        self.debug_mode = debug

        # [A] Optimization: Decimation Strategy
        # We analyze audio at 8kHz instead of 48kHz to reduce Goertzel CPU load.
        # Factor 6: 48000 / 6 = 8000 Hz.
        # NOTE: Requires an external Bandpass Filter (300-3800Hz) upstream to prevent aliasing.
        self.decim_factor = 6
        self.fs_analysis = self.fs / self.decim_factor

        # --- SelCall Logic Setup ---
        self.decoder_lib = SelectiveCalling(debug=debug)
        self.freq_list = []
        self.symbol_list = []
        self.tone_ms = 100.0  # Default
        self._configure_protocol()

        # --- Message Port ---
        self.message_port_name = pmt.intern("selcall_out")
        self.message_port_register_out(self.message_port_name)

        # --- Audio Gate State ---
        self.gate_open = False
        self.gate_timer_samples = 0
        self.gate_duration_samples = int(20.0 * self.fs)  # Duration: 20 seconds

        # [A] Buffer Sizing
        # The analysis window must roughly match the tone duration
        self.samples_per_tone = int(self.fs * (self.tone_ms / 1000.0))
        # Hop size: how much we slide the window (e.g., 50% overlap)
        self.hop_size = max(1, self.samples_per_tone // 2)

        # Internal buffer to accumulate samples across work() calls
        self.internal_buffer = np.array([], dtype=np.float32)

        # --- Decoding State Machine ---
        self.detected_symbols_history = []  # Temporary list of (symbol, power)
        self.last_valid_sequence = ""
        self.avg_noise_power = 10.0  # Initial noise floor estimate

        if self.debug_mode:
            print(f"[SelCall] Init: Protocol={protocol}, Tone={self.tone_ms}ms, Gate={self.target_code}")

    def _configure_protocol(self):
        """ Configures frequency tables based on the selected protocol """
        p = self.protocol.upper()

        if p == "ZVEI-1":
            self.freq_list = ZVEI1_VALUES
            self.symbol_list = ZVEI1_SYMBOLS
            base_ms = ZVEI_TONE_MS
        elif p == "ZVEI-2":
            self.freq_list = ZVEI2_VALUES
            self.symbol_list = ZVEI2_SYMBOLS
            base_ms = ZVEI_TONE_MS
        elif p in ["CCIR-1", "CCIR-2", "CCIR-7"]:
            self.freq_list = CCIR_VALUES
            self.symbol_list = CCIR_SYMBOLS
            base_ms = CCIR_CODE_LEN_MS.get(p, 100)
        elif p == "PCCIR":
            self.freq_list = PCCIR_VALUES
            self.symbol_list = PCCIR_SYMBOLS
            base_ms = 100
        else:
            # Fallback
            self.freq_list = ZVEI1_VALUES
            self.symbol_list = ZVEI1_SYMBOLS
            base_ms = 70

        # Override if user specified a custom duration (>0)
        if self.user_tone_ms > 0:
            self.tone_ms = self.user_tone_ms
        else:
            self.tone_ms = base_ms

    def work(self, input_items, output_items):
        in0 = input_items[0]
        out0 = output_items[0]
        n_samples = len(in0)

        # [B] Data Accumulation
        # Append incoming samples to the internal buffer.
        # We assume in0 is already filtered by an upstream Bandpass Filter.
        self.internal_buffer = np.concatenate((self.internal_buffer, in0))

        # [C] Analysis Loop
        # Process as long as we have enough data for a full tone window
        while len(self.internal_buffer) >= self.samples_per_tone:

            # Extract window at full resolution (e.g., 48kHz)
            frame_48k = self.internal_buffer[:self.samples_per_tone]

            # [D] Decimation (Downsampling)
            # Create a "lightweight" version for Goertzel analysis: take 1 sample every 6.
            frame_analysis = frame_48k[::self.decim_factor]

            # [E] DSP Analysis (Goertzel)
            # Call the library using the reduced sample rate (fs_analysis)
            symbol, max_p, second_p, idx = self.decoder_lib.detect_symbol_for_frame(
                frame_analysis,
                self.fs_analysis,
                freq_list=self.freq_list,
                symbol_list=self.symbol_list,
                band=8,
                ratio_threshold=2.5  # Slightly lower threshold for real-time
            )

            # [F] Adaptive Noise Thresholding
            # Exponential moving average to estimate noise floor
            if max_p < (self.avg_noise_power * 20):
                self.avg_noise_power = 0.95 * self.avg_noise_power + 0.05 * max_p

            adaptive_thresh = self.avg_noise_power * 8.0

            valid_symbol = "-"
            if max_p > adaptive_thresh and max_p > 100.0:  # Hard floor check
                valid_symbol = symbol

            # [G] Symbol Stream Processing
            # Pass the detected symbol to the State Machine
            self._process_symbol_stream(valid_symbol, max_p)

            # [H] Buffer Sliding (Hop)
            # Advance the buffer for the next analysis window
            self.internal_buffer = self.internal_buffer[self.hop_size:]

        # [M] Audio Gate / Pass-through Logic
        # Decide whether to mute or pass audio based on the timer
        if self.gate_open:
            if self.gate_timer_samples > 0:
                # Copy input to output (Pass-through)
                out0[:] = in0[:]
                self.gate_timer_samples -= n_samples
            else:
                # Timer expired -> Mute
                self.gate_open = False
                out0[:] = 0.0
                if self.debug_mode:
                    print("[SelCall] Gate closed (timeout).")
        else:
            # Default Mute
            out0[:] = 0.0

        return n_samples

    def _process_symbol_stream(self, symbol, power):
        """
        [G] State Machine: Reconstructs the string from raw symbols (Debouncing)
        and checks for sequence completion.
        """
        self.detected_symbols_history.append(symbol)

        # Keep history short to save memory
        if len(self.detected_symbols_history) > 100:
            self.detected_symbols_history.pop(0)

        # [I] End-of-Sequence Detection
        # If we detect silence ("-") for a few frames after data, assume transmission ended.
        suffix_len = 4
        if len(self.detected_symbols_history) > suffix_len:
            last_n = self.detected_symbols_history[-suffix_len:]

            # If the last N symbols are all silence
            if all(s == "-" for s in last_n):
                # Extract non-silence symbols
                raw_seq = [s for s in self.detected_symbols_history if s != "-"]

                if not raw_seq:
                    return # Nothing to process

                # [J] Compression (RLE - Run Length Encoding logic)
                # Merge adjacent identical symbols (e.g., 1, 1, 1 -> 1)
                compressed = []
                if raw_seq:
                    prev = raw_seq[0]
                    compressed.append(prev)
                    for s in raw_seq[1:]:
                        if s != prev:
                            compressed.append(s)
                            prev = s

                final_str = "".join(compressed)

                # [K] Sequence Validation & Formatting
                # Filter noise (min length 3) and avoid reprocessing the same sequence
                if len(final_str) >= 3:
                    if final_str != self.last_valid_sequence:
                        self.last_valid_sequence = final_str
                        self._analyze_sequence(final_str)

                        # Reset history after valid processing
                        self.detected_symbols_history = []

    def _analyze_sequence(self, decoded_string):
        """
        [K] Analyzes the compressed string, applies protocol logic,
        and checks against the Target Code.
        """
        # Apply protocol formatter (Handle 'E' repeats, pauses, etc.)
        formatted_str = self.decoder_lib.selective_formatter(
            decoded_string,
            group_size=self.code_length,
            protocol=self.protocol,
            format_output="MINIMAL"
        )

        clean_str = formatted_str.replace("-", "")
        target = self.target_code.upper()

        match_found = False

        # [L] Target Matching Logic
        # Check if Target is inside the decoded string (Source or Dest)
        if target in clean_str:
            match_found = True
            self.gate_open = True
            self.gate_timer_samples = self.gate_duration_samples  # Reset/Retrigger Timer
            if self.debug_mode:
                print(f"[SelCall] MATCH! Target {target} found in {clean_str}. Gate OPEN.")

        # [N] Message Emission
        self._send_message(formatted_str, match_found)

    def _send_message(self, decoded_code, match_status):
        """ [N] PMT Message Construction & Publishing """
        timestamp = time.time()

        # Build Metadata Dictionary
        meta = pmt.make_dict()
        meta = pmt.dict_add(meta, pmt.intern("timestamp"), pmt.from_double(timestamp))
        meta = pmt.dict_add(meta, pmt.intern("protocol"), pmt.intern(self.protocol))
        meta = pmt.dict_add(meta, pmt.intern("gate_active"), pmt.from_bool(match_status))
        meta = pmt.dict_add(meta, pmt.intern("code"), pmt.intern(decoded_code))

        # Create Pair: (Code_String, Metadata_Dict)
        msg = pmt.cons(pmt.intern("sel"), meta)

        self.message_port_pub(self.message_port_name, msg)