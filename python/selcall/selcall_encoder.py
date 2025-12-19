"""
Embedded Python Block: SelCall Generator (TX)
"""

from gnuradio import gr
import pmt
import time

from .core.protocols.CCIR import *
from .core.protocols.ZVEI import *


class selcall_encoder(gr.sync_block):
    """
    SelCall Generator Block for GNU Radio.
    Generates ZVEI/CCIR tones upon receiving a destination code via message.
    Combines Personal Code (Param) + Pause + Destination Code (Msg).
    """

    def __init__(self, sample_rate=48000, protocol="ZVEI-1", amplitude=0.8, own_id="12345"):
        gr.sync_block.__init__(
            self,
            name='SelCall Encoder',
            in_sig=None,  # Message input only
            out_sig=[np.float32]  # Audio output
        )

        self.fs = sample_rate
        self.amplitude = amplitude
        self.protocol = protocol
        self.own_id = str(own_id)  # Must be a string

        # --- Setup Protocollo ---
        self.tone_map = {}  # Dictionary { 'Char': Freq }
        self.tone_duration_s = 0.07  # Default 70ms
        self.pause_freq = 0.0  # Frequency during the separating pause (0 = silence)
        self.repeater_char = 'E'  # Symbol used for repetitions

        self._configure_protocol()

        # --- Audio Buffer ---
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_index = 0
        self.transmitting = False
        self.last_tx_state = False  # Per edge detection

        # --- Flag to manage USRP burst start TAGs ---
        self.new_burst_started = False

        # --- Message Port ---
        self.port_name = pmt.intern("msg_in")
        self.message_port_register_in(self.port_name)
        self.set_msg_handler(self.port_name, self.handle_msg)

        # --- PTT Output Port ---
        self.port_name_ptt = pmt.intern("ptt_out")
        self.message_port_register_out(self.port_name_ptt)

    def _configure_protocol(self):
        """
        Configures frequency tables and times based on user selection
        """
        p = self.protocol.upper()

        vals = []
        syms = []
        duration_ms = 70.0

        # Get the specific pause frequency if available (e.g. ZVEI_TONE_CH_PAUSE)
        # If it is a numerical constant (Hz) in the protocol file, we use it.
        # Otherwise, default to 0 (silence).
        pause_val = 0

        if p == "ZVEI-1":
            vals = ZVEI1_VALUES
            syms = ZVEI1_SYMBOLS
            duration_ms = ZVEI_TONE_MS
            pause_val = ZVEI_TONE_CH_EOM_FREQ
            self.repeater_char = ZVEI_TONE_CH_REPEATER

        elif p == "ZVEI-2":
            vals = ZVEI2_VALUES
            syms = ZVEI2_SYMBOLS
            duration_ms = ZVEI_TONE_MS
            pause_val = ZVEI_TONE_CH_EOM_FREQ  # Assumiamo sia definito anche qui o usiamo default
            self.repeater_char = ZVEI_TONE_CH_REPEATER

        elif p in ["CCIR-1", "CCIR-2", "CCIR-7"]:
            vals = CCIR_VALUES
            syms = CCIR_SYMBOLS
            duration_ms = CCIR_CODE_LEN_MS.get(p, 100.0)
            pause_val = CCIR_TONE_CH_EOM_FREQ
            self.repeater_char = CCIR_TONE_CH_REPEATER

        elif p == "PCCIR":
            vals = PCCIR_VALUES
            syms = PCCIR_SYMBOLS
            duration_ms = 100.0
            pause_val = CCIR_TONE_CH_EOM_FREQ
            self.repeater_char = PCCIR_TONE_CH_REPEATER

        else:
            print(f"[SelCall Encoder] Unknown protocol {p}, using ZVEI-1")
            vals = ZVEI1_VALUES
            syms = ZVEI1_SYMBOLS
            duration_ms = 70.0
            pause_val = ZVEI_TONE_CH_EOM_FREQ
            self.repeater_char = ZVEI_TONE_CH_REPEATER

        self.tone_map = dict(zip(syms, vals))
        self.tone_duration_s = duration_ms / 1000.0

        # If pauses_val is a number (frequency), we use it. If it is an index or something else, we use 0.
        if isinstance(pause_val, (int, float)):
            self.pause_freq = float(pause_val)
        else:
            self.pause_freq = 0.0

        # Debug Info
        print(f"[SelCall Encoder] Protocol: {p}")
        print(f"[SelCall Encoder] Tone Duration: {self.tone_duration_s*1000} ms")
        print(f"[SelCall Encoder] Pause Frequency: {self.pause_freq} Hz")

    def generate_sine(self, freq, duration_s):
        """ Generates a pure sine wave at a certain frequency and for a certain duration. """
        if freq <= 0:
            return np.zeros(int(self.fs * duration_s), dtype=np.float32)

        t = np.arange(int(self.fs * duration_s)) / self.fs
        return (self.amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)

    def handle_msg(self, msg):
        """
        Callback messages.
        The message contains ONLY the recipient code (e.g. ‘67890’).
        The block constructs: Source + “-” + Dest (e.g. ‘12345-67890’).
        """

        # FIXME: Extract destination code from PMT message
        if pmt.is_null(msg):
            print("[SelCall Encoder] Received null message, ignoring.")
            return

        dest_code = pmt.to_python(msg)[1]  # Assuming msg is a PMT symbol

        if not dest_code:
            print("[SelCall Encoder] Received empty destination code, ignoring.")
            return

        # Building the complete sequence: SOURCE - RECIPIENT
        # The character “-” will tell the next loop to insert the pause.
        full_sequence = f"{self.own_id}-{dest_code}"
        print(f"[SelCall Encoder] Sent: {self.own_id} -> {dest_code} (Seq: {full_sequence})")
        full_wave = np.array([], dtype=np.float32)

        # Split to manage parts (Part 0 = Source, Part 1 = Dest)
        parts = full_sequence.split('-')

        # === Add Initial Silence (Padding) ===
        # 700ms of silence to allow time for the TX to open
        padding = np.zeros(int(self.fs * 0.7), dtype=np.float32)
        full_wave = np.concatenate((full_wave, padding))
        # ========================================================

        for i, part in enumerate(parts):
            # If we are between one part and another, we insert a pause.
            if i > 0:
                pause_wave = self.generate_sine(self.pause_freq, self.tone_duration_s)
                full_wave = np.concatenate((full_wave, pause_wave))

            last_char = None

            for char in part:
                target_char = char

                # Repeat Tone Logic (e.g. 11 -> 1E)
                if char == last_char:
                    target_char = self.repeater_char

                freq = self.tone_map.get(target_char, 0.0)
                tone = self.generate_sine(freq, self.tone_duration_s)
                full_wave = np.concatenate((full_wave, tone))

                last_char = char

        # === Addition of Final Silence ===
        # A little queue to avoid clicks when shutting down
        full_wave = np.concatenate((full_wave, padding))
        # ============================================

        self.audio_buffer = full_wave
        self.buffer_index = 0
        self.transmitting = True

        # === This is a new package ===
        self.new_burst_started = True

    # --- Helper functions for PTT / Messaging ---s
    def _send_ptt_message(self, state):
        """Builds and sends the Boolean PMT message for PTT state."""
        msg = pmt.cons(pmt.intern("value"), pmt.from_bool(state))
        self.message_port_pub(self.port_name_ptt, msg)

    def _update_ptt_status(self):
        """Check whether the transmission status has changed and notify if needed"""
        if self.transmitting != self.last_tx_state:
            self._send_ptt_message(self.transmitting)
            self.last_tx_state = self.transmitting

    def work(self, input_items, output_items):
        out_audio = output_items[0]
        n_out = len(out_audio)
        n_written = 0

        # 1. GUI management (Active Message)
        if self.transmitting != self.last_tx_state:
            self._send_ptt_message(self.transmitting)
            self.last_tx_state = self.transmitting

        # 2. IF WE ARE NOT TRANSMITTING:
        # Do not produce anything. Return 0.
        # This forces the USRP to empty the buffer and shut down (Underrun).
        if not self.transmitting:
            time.sleep(0.01)  # Short sleep to avoid overloading the CPU
            return 0

        # 3. IF WE ARE TRANSMITTING:
        remaining = len(self.audio_buffer) - self.buffer_index

        # --- Tag START (tx_sob) ---
        if self.new_burst_started:
            self.add_item_tag(
                0,
                self.nitems_written(0),
                pmt.intern("tx_sob"),
                pmt.PMT_T
            )
            self.new_burst_started = False

        if remaining > 0:
            to_write = min(n_out, remaining)
            out_audio[:to_write] = self.audio_buffer[self.buffer_index: self.buffer_index + to_write]
            self.buffer_index += to_write
            n_written = to_write

            # --- Tag STOP (tx_eob) ---
            if self.buffer_index >= len(self.audio_buffer):
                tag_index = self.nitems_written(0) + n_written - 1
                self.add_item_tag(
                    0,
                    tag_index,
                    pmt.intern("tx_eob"),
                    pmt.PMT_T
                )

                self.transmitting = False
                self.buffer_index = 0
                print("[SelCall TX] Burst completato. Stop stream.")

        # 4. Important: Do not fill in the rest with zeros!
        # Only return what you have actually written.
        return n_written