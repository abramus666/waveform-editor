
from src import axis

import ctypes, math, threading, winsound

POINTS_PER_CURVE = 100

#===============================================================================
class Curve:

   def __init__(self, input_curve):
      self.points = []
      for ix in range(len(input_curve)-1):
         pt1 = input_curve[ix][1]
         pt2 = input_curve[ix][2]
         pt3 = input_curve[ix+1][0]
         pt4 = input_curve[ix+1][1]
         # Current control point.
         self.points.append(pt1)
         # Points between the current and next control point.
         self.points += [self.calculateCurveAt(pt1, pt2, pt3, pt4, i/POINTS_PER_CURVE) for i in range(1, POINTS_PER_CURVE)]
      # Last control point.
      self.points.append(pt4)

   def calculateCurveAt(self, pt1, pt2, pt3, pt4, relative_pos):
      # 1st round.
      x1 = pt2[0] * relative_pos + pt1[0] * (1.0 - relative_pos)
      y1 = pt2[1] * relative_pos + pt1[1] * (1.0 - relative_pos)
      x2 = pt3[0] * relative_pos + pt2[0] * (1.0 - relative_pos)
      y2 = pt3[1] * relative_pos + pt2[1] * (1.0 - relative_pos)
      x3 = pt4[0] * relative_pos + pt3[0] * (1.0 - relative_pos)
      y3 = pt4[1] * relative_pos + pt3[1] * (1.0 - relative_pos)
      # 2nd round.
      x1 = x2 * relative_pos + x1 * (1.0 - relative_pos)
      y1 = y2 * relative_pos + y1 * (1.0 - relative_pos)
      x2 = x3 * relative_pos + x2 * (1.0 - relative_pos)
      y2 = y3 * relative_pos + y2 * (1.0 - relative_pos)
      # 3rd round.
      x1 = x2 * relative_pos + x1 * (1.0 - relative_pos)
      y1 = y2 * relative_pos + y1 * (1.0 - relative_pos)
      return (x1, y1)

   def getY(self, x):
      # Binary search for rightmost element.
      left = 0
      right = len(self.points)
      while left < right:
         ix = (left + right) // 2
         if self.points[ix][0] > x:
            right = ix
         else:
            left = ix+1
      ix = right-1
      # Check boundaries.
      if ix < 0:
         y = self.points[0][1]
      elif ix+1 >= len(self.points):
         y = self.points[-1][1]
      else:
         pt1 = self.points[ix]
         pt2 = self.points[ix+1]
         # Linear interpolation.
         pos = (x - pt1[0]) / (pt2[0] - pt1[0])
         y = pt2[1] * pos + pt1[1] * (1.0 - pos)
      return y

#===============================================================================
class SoundInfo:

   def __init__(self, input_sound):
      self.input_sound      = input_sound
      self.sampling_rate_hz = input_sound['Sampling rate [Hz]']
      self.time_axis        = axis.Time(input_sound['Time axis'])
      self.frequency_axis   = axis.Frequency(input_sound['Frequency axis'])
      self.amplitude_axis   = axis.Amplitude(input_sound['Amplitude axis'])
      self.total_time_ms    = self.time_axis.convertTo(1.0)
      self.min_amplitude_db = self.amplitude_axis.convertTo(0.0)
      self.num_samples      = round(self.sampling_rate_hz * (self.total_time_ms / 1000.0))

#===============================================================================
class Wave:

   def __init__(self):
      self.input_wave = None
      self.sound_info = None

   def generate(self, input_wave, sound_info):
      # Samples are only calculated if the input data is different than before.
      # Otherwise, the previously calculated samples are used.
      if self.input_wave != input_wave or self.sound_info.input_sound != sound_info.input_sound:
         self.input_wave = input_wave
         self.sound_info = sound_info
         # Curves.
         self.frequency_curve = Curve(input_wave['Frequency'])
         self.amplitude_curve = Curve(input_wave['Amplitude'])
         # Function to calculate waveform.
         self.setupWaveformFunc(input_wave['Waveform'])
         # Calculate samples.
         self.calculateSamples()
      # Return samples.
      return self.samples

   def setupWaveformFunc(self, waveform):
      if waveform['Type'] == 'Sine':
         self.waveform_func = self.calculateWaveformSine
      elif waveform['Type'] == 'Square':
         self.waveform_func = self.calculateWaveformSquare
      elif waveform['Type'] == 'Triangle':
         self.waveform_func = self.calculateWaveformTriangle
      elif waveform['Type'] == 'Sawtooth':
         self.waveform_func = self.calculateWaveformSawtooth
      else:
         self.waveform_func = lambda x: 0

   def calculateWaveformSine(self, x):
      return math.sin(x * 2.0*math.pi)

   def calculateWaveformSquare(self, x):
      return (1.0 if (x < 0.5) else -1.0)

   def calculateWaveformTriangle(self, x):
      x = math.modf(x + 0.75)[0]
      return ((1.0-4.0*x) if (x < 0.5) else (4.0*x-3.0))

   def calculateWaveformSawtooth(self, x):
      x = math.modf(x + 0.5)[0]
      return (2.0*x - 1.0)

   def calculateSamples(self):
      frequency_func = self.sound_info.frequency_axis.convertTo
      amplitude_func = self.sound_info.amplitude_axis.convertTo
      sampling_rate_hz = self.sound_info.sampling_rate_hz
      min_amplitude_db = self.sound_info.min_amplitude_db
      num_samples = self.sound_info.num_samples
      # Allocate array for samples.
      self.samples = [0.0 for i in range(num_samples)]
      waveform_x = 0.0
      for ix in range(num_samples):
         # Calculate frequency and amplitude.
         x = (ix / (num_samples - 1.0))
         frequency_hz = frequency_func(self.frequency_curve.getY(x))
         amplitude_db = amplitude_func(self.amplitude_curve.getY(x))
         if amplitude_db > min_amplitude_db:
            # Convert from dB to relative amplitude in range [0,1].
            # 20 dB change corresponds to a change in relative amplitude by a factor of 10.
            amplitude = 10.0**(amplitude_db / 20.0)
            # Calculate waveform value.
            waveform_y = self.waveform_func(waveform_x)
            # Scale waveform value by amplitude.
            self.samples[ix] = (waveform_y * amplitude)
         else:
            self.samples[ix] = 0.0
         # Calculate the next position within the waveform.
         waveform_x = math.modf(waveform_x + (frequency_hz / sampling_rate_hz))[0]

#===============================================================================
class WavFile:

   def __init__(self):
      # Wave objects are preserved so that it is possible
      # to avoid generating samples when a wave is not changed.
      self.all_waves = []

   def generate(self, input):
      self.sound_info = SoundInfo(input['Sound'])
      # Prepare waves that will be used to generate samples.
      while len(self.all_waves) < len(input['Waves']):
         self.all_waves.append(Wave())
      while len(self.all_waves) > len(input['Waves']):
         self.all_waves.pop()
      # Generate samples from each wave.
      self.all_samples = []
      for wave,input_wave in zip(self.all_waves, input['Waves']):
         self.all_samples.append(wave.generate(input_wave, self.sound_info))
      # Merge samples from different waves, and serialize them into WAV file.
      self.serializeHeader()
      self.serializeData()

   def writeToFile(self, path):
      with open(path, 'wb') as f:
         f.write(self.buffer)

   def serializeInt16(self, value):
      self.buffer[self.buffer_ix] = value & 0xff
      self.buffer[self.buffer_ix+1] = (value >> 8) & 0xff
      self.buffer_ix += 2

   def serializeInt32(self, value):
      self.buffer[self.buffer_ix] = value & 0xff
      self.buffer[self.buffer_ix+1] = (value >> 8) & 0xff
      self.buffer[self.buffer_ix+2] = (value >> 16) & 0xff
      self.buffer[self.buffer_ix+3] = (value >> 24) & 0xff
      self.buffer_ix += 4

   def serializeString(self, value):
      for c in value:
         self.buffer[self.buffer_ix] = ord(c)
         self.buffer_ix += 1

   def serializeHeader(self):
      sampling_rate_hz = self.sound_info.sampling_rate_hz
      num_samples = self.sound_info.num_samples
      # Allocate buffer.
      self.buffer = ctypes.create_string_buffer(44+num_samples*2)
      self.buffer_ix = 0
      # Main chunk header.
      self.serializeString('RIFF')              # Chunk ID.
      self.serializeInt32((44-8)+num_samples*2) # Chunk size.
      self.serializeString('WAVE')              # Riff type.
      # Format chunk header.
      self.serializeString('fmt ')              # Chunk ID.
      self.serializeInt32(16)                   # Chunk size.
      self.serializeInt16(1)                    # Format code (PCM).
      self.serializeInt16(1)                    # Number of channels.
      self.serializeInt32(sampling_rate_hz)     # Samples per second.
      self.serializeInt32(sampling_rate_hz*2)   # Bytes per second.
      self.serializeInt16(2)                    # Bytes per block.
      self.serializeInt16(16)                   # Bits per sample.
      # Data chunk header.
      self.serializeString('data')              # Chunk ID.
      self.serializeInt32(num_samples*2)        # Chunk size.

   def serializeData(self):
      for ix in range(self.sound_info.num_samples):
         # Merge samples from different waves.
         value = sum([samples[ix] for samples in self.all_samples])
         # Convert from [-1,1] to the range of 16-bit signed integer and clip.
         value = round(32767.0 * value)
         value = min(max(value, -32768), 32767)
         self.serializeInt16(value)

#===============================================================================
class CommPort:

   def __init__(self):
      self.queue = []
      self.value = None
      self.event = threading.Event()

   def set(self, cmd):
      # PLAY / STOP commands overwrite previous, not yet processed commands of these types.
      if (cmd[0] == 'PLAY') or (cmd[0] == 'STOP'):
         self.value = cmd
      # Otherwise command goes into the queue.
      else:
         self.queue.append(cmd)
      # Signal that there is command to process.
      self.event.set()

   def get(self):
      self.event.wait()
      # Queue has higher priority.
      if len(self.queue) > 0:
         cmd = self.queue.pop(0)
      else:
         cmd = self.value
         self.value = None
      # Indicate that there is no command to process.
      if (len(self.queue) == 0) and (self.value is None):
         self.event.clear()
      return cmd

#===============================================================================
class Thread:

   def __init__(self):
      self.port = CommPort()
      self.thread = threading.Thread(target = self.waveGenThread)
      self.thread.start()

   def quit(self):
      self.port.set(('QUIT',))

   def stop(self):
      self.port.set(('STOP',))

   def play(self, params):
      self.port.set(('PLAY', params))

   def prepare(self, params):
      self.port.set(('PREPARE', params))

   def write(self, path):
      self.port.set(('WRITE', path))

   def drop(self):
      self.port.set(('DROP',))

   def waveGenThread(self):
      PlaySound = ctypes.windll.winmm.PlaySound
      play_wav = WavFile()
      prep_wav = None
      while True:
         cmd = self.port.get()
         # QUIT command: Stop playing and exit from function.
         if cmd[0] == 'QUIT':
            PlaySound(0, 0, 0)
            return
         # STOP command: Stop playing.
         elif cmd[0] == 'STOP':
            PlaySound(0, 0, 0)
         # PLAY command: Generate WAV and play it from memory.
         elif cmd[0] == 'PLAY':
            play_wav.generate(cmd[1])
            PlaySound(play_wav.buffer, 0, winsound.SND_ASYNC | winsound.SND_LOOP | winsound.SND_MEMORY | winsound.SND_NODEFAULT)
         # PREPARE command: Generate WAV and save it for later.
         elif cmd[0] == 'PREPARE':
            prep_wav =  WavFile()
            prep_wav.generate(cmd[1])
         # WRITE command: Write the previously generated WAV to the given file.
         elif cmd[0] == 'WRITE':
            prep_wav.writeToFile(cmd[1])
            prep_wav = None
         # DROP command: Drop the previously generated WAV.
         elif cmd[0] == 'DROP':
            prep_wav = None
