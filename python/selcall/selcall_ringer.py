"""
Block: Selcall Ringer (Event-Based Ringtone Generator)
"""
import numpy as np
from gnuradio import gr
import pmt

class selcall_ringer(gr.sync_block):
    """
    SelCall Ringer Block

    Generates a European-style siren tone (alternating 800Hz/1010Hz) upon receiving
    an asynchronous message trigger.

    Args:
        sample_rate (int): Audio sampling rate (default: 48000).
        duration (float): Duration of the ringtone in seconds.
        amplitude (float): Volume of the output tone (0.0 - 1.0).

    Ports:
        trigger (in): Message port. Any received message resets the timer and starts audio.
        audio_out (out): Float stream of the generated audio.
        led (out): Message port. Sends (True) when ringing starts, (False) when finished.
    """

    def __init__(self, sample_rate=48000, duration=5, amplitude=0.5):
        gr.sync_block.__init__(
            self,
            name='Selcall Ringer',
            in_sig=None,  # Only input messages
            out_sig=[np.float32]  # Audio output stream
        )
        self.fs = sample_rate
        self.duration_samples = int(sample_rate * duration) # Duration in samples
        self.freqA = 800.0  # Frequency A of the ring tone
        self.freqB = 1010.0  # Frequency B of the ring tone
        self.amplitude = amplitude

        # --- Internal State ---
        self.remaining_samples = 0

        # -- Message Port ---
        self.port_in = pmt.intern("trigger")
        self.message_port_register_in(self.port_in)
        self.set_msg_handler(self.port_in, self.handle_msg)

        # --- Ringer Port ---
        self.port_match_event = pmt.intern("led")
        self.message_port_register_out(self.port_match_event)

    def handle_msg(self, msg):
        """
        Callback activated by ANY incoming message.
        Resets the timer and starts the sound.
        """
        # We don't care about the content of the message (it can be True, False, String...)
        # As long as something arrives to trigger the alarm.
        self.remaining_samples = self.duration_samples
        self._manage_led(True)  # Accende il LED di chiamata

    def _manage_led(self, state: bool):
        """Send a message to switch the call LED on/off"""
        self.message_port_pub(
            self.port_match_event,
            pmt.cons(pmt.intern("value"), pmt.from_bool(state))
        )

    def generate_tone(self, freq, n_samples):
        """Generates a sinusoidal tone of frequency `freq` for `n_samples` samples"""
        t = np.arange(n_samples)
        tone = self.amplitude * np.sin(2 * np.pi * freq * t / self.fs)
        return tone

    def work(self, input_items, output_items):
        # Retrieve the pointer to the output buffer (where to write the audio)
        out = output_items[0]
        n_out = len(out)

        # --- ACTIVE STATUS CHECK ---
        # If remaining_samples > 0, it means that the alarm is sounding
        if self.remaining_samples > 0:

            # Let's calculate how many samples to generate NOW.
            # It is the minimum between ‘space in the buffer’ (n_out) and ‘how much time is left until the end of the alarm’.
            samples_to_generate = min(n_out, self.remaining_samples)

            # Defines the duration of a single tone (300ms converted into number of samples)
            half_cycle = int(self.fs * 0.3)

            tone = np.array([], dtype=np.float32)
            samples_generated = 0

            # --- GENERATION CYCLE ---
            # We use a while loop because a single output buffer may need to contain
            # PIECES of two different frequencies (e.g. end of tone A and start of tone B).
            while samples_generated < samples_to_generate:
                # 1. Calculation of time elapsed since the alarm started
                samples_elapsed = self.duration_samples - self.remaining_samples

                # 2. Frequency Selection (A or B)
                # Divide the elapsed time by 300ms. If the result is even, use A; if odd, use B.
                # This creates the two-tone siren effect.
                current_cycle_index = samples_elapsed // half_cycle
                current_freq = self.freqA if current_cycle_index % 2 == 0 else self.freqB

                # 3. Calculate how many samples are missing until the NEXT frequency change
                # ‘Where are they within the current 300ms?’
                offset_in_cycle = samples_elapsed % half_cycle
                samples_left_in_tone = half_cycle - offset_in_cycle

                # 4. We decide how many samples to generate in this step of the while loop:
                # We cannot generate more than what is needed to fill the buffer (samples_to_generate - samples_generated)
                # And we cannot generate more than what is needed to change the frequency (samples_left_in_tone)
                samples_left_to_fill = samples_to_generate - samples_generated
                samples_this_cycle = min(samples_left_in_tone, samples_left_to_fill)

                # 5. Wave generation and concatenation
                tone_segment = self.generate_tone(current_freq, samples_this_cycle)
                tone = np.concatenate((tone, tone_segment))

                # 6. Updating counters for the next round of the while loop
                samples_generated += samples_this_cycle
                self.remaining_samples -= samples_this_cycle

            # Writes the generated audio to the output buffer
            out[:samples_to_generate] = tone

            # --- ALARM END MANAGEMENT (MID-BUFFER) ---
            # If the alarm ends BEFORE filling the entire n_out buffer,
            # we fill the remaining part with silence (zeros).
            if samples_to_generate < n_out:
                out[samples_to_generate:n_out] = 0.0

        else:
            # --- INACTIVE STATE ---
            # If we don't have to play, we fill the entire buffer with zeros
            out[:] = 0.0
            # We ensure that the LED is switched off.
            self._manage_led(False)

        return n_out