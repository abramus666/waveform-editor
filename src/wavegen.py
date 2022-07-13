
import ctypes, math, threading, winsound

POINTS_PER_CURVE = 100

#===============================================================================
class Curve:

   def __init__(self, plot):
      self.curves = list(plot.getCurves())
      self.x_axis = plot.getXaxis().clone()
      self.y_axis = plot.getYaxis().clone()

   def generate(self):
      self.points = []
      for pt1,pt2,pt3,pt4 in self.curves:
         # Current control point.
         self.points += [(pt1.x, pt1.y)]
         # Points between the current and next control point.
         self.points += [self.calculateCurveAt(pt1, pt2, pt3, pt4, i/POINTS_PER_CURVE) for i in range(1, POINTS_PER_CURVE)]
      # Last control point.
      self.points += [(pt4.x, pt4.y)]

   def calculateCurveAt(self, pt1, pt2, pt3, pt4, relative_pos):
      # 1st round.
      x1 = pt2.x * relative_pos + pt1.x * (1.0 - relative_pos)
      y1 = pt2.y * relative_pos + pt1.y * (1.0 - relative_pos)
      x2 = pt3.x * relative_pos + pt2.x * (1.0 - relative_pos)
      y2 = pt3.y * relative_pos + pt2.y * (1.0 - relative_pos)
      x3 = pt4.x * relative_pos + pt3.x * (1.0 - relative_pos)
      y3 = pt4.y * relative_pos + pt3.y * (1.0 - relative_pos)
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
      # Convert from X axis unit to range [0,1].
      x = self.x_axis.convertFrom(x)
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
      # Convert from range [0,1] to Y axis unit.
      return self.y_axis.convertTo(y)

#===============================================================================
class Wave:

   def __init__(self, frequency_curve, amplitude_curve, sample_freq_hz):
      self.frequency_curve  = frequency_curve
      self.amplitude_curve  = amplitude_curve
      self.min_amplitude_db = amplitude_curve.y_axis.convertTo(0.0)
      self.total_time_ms    = amplitude_curve.x_axis.convertTo(1.0)
      self.sample_freq_hz   = round(sample_freq_hz)
      self.num_samples      = round(sample_freq_hz * (self.total_time_ms / 1000.0))

   def generate(self):
      self.frequency_curve.generate()
      self.amplitude_curve.generate()
      self.serializeWavFileHeader()
      self.serializeWavFileData()

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

   def serializeWavFileHeader(self):
      # Allocate buffer.
      self.buffer = ctypes.create_string_buffer(44+self.num_samples*2)
      self.buffer_ix = 0
      # Main chunk header.
      self.serializeString('RIFF')                   # Chunk ID.
      self.serializeInt32((44-8)+self.num_samples*2) # Chunk size.
      self.serializeString('WAVE')                   # Riff type.
      # Format chunk header.
      self.serializeString('fmt ')                   # Chunk ID.
      self.serializeInt32(16)                        # Chunk size.
      self.serializeInt16(1)                         # Format code (PCM).
      self.serializeInt16(1)                         # Number of channels.
      self.serializeInt32(self.sample_freq_hz)       # Samples per second.
      self.serializeInt32(self.sample_freq_hz*2)     # Bytes per second.
      self.serializeInt16(2)                         # Bytes per block.
      self.serializeInt16(16)                        # Bits per sample.
      # Data chunk header.
      self.serializeString('data')                   # Chunk ID.
      self.serializeInt32(self.num_samples*2)        # Chunk size.

   def serializeWavFileData(self):
      for value in self.calculateWave():
         # Convert from [-1,1] to the range of 16-bit signed integer and clip.
         value = round(32767.0 * value)
         value = min(max(value, -32768), 32767)
         self.serializeInt16(value)

   def calculateWave(self):
      waveform_x = 0.0
      samples = [0.0 for i in range(self.num_samples)]
      for i in range(self.num_samples):
         # Calculate current time, frequency, and amplitude.
         t_ms = self.total_time_ms * (i / (self.num_samples - 1))
         frequency_hz = self.frequency_curve.getY(t_ms)
         amplitude_db = self.amplitude_curve.getY(t_ms)
         if amplitude_db > self.min_amplitude_db:
            # Convert from dB to relative amplitude in range [0,1].
            # 20 dB change corresponds to a change in relative amplitude by a factor of 10.
            amplitude = 10.0**(amplitude_db / 20.0)
            # Calculate waveform value.
            waveform_y = math.sin(waveform_x)
            # Scale waveform value by amplitude.
            samples[i] = (waveform_y * amplitude)
         else:
            samples[i] = 0.0
         # Calculate the next position within the waveform.
         waveform_x += 2.0*math.pi * (frequency_hz / self.sample_freq_hz)
         if waveform_x >= 2.0*math.pi:
            waveform_x -= 2.0*math.pi
      return samples

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
      prep_wave = None
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
            temp_wave = Wave(*cmd[1])
            temp_wave.generate()
            PlaySound(temp_wave.buffer, 0, winsound.SND_ASYNC | winsound.SND_LOOP | winsound.SND_MEMORY | winsound.SND_NODEFAULT)
         # PREPARE command: Generate WAV and save it for later.
         elif cmd[0] == 'PREPARE':
            prep_wave = Wave(*cmd[1])
            prep_wave.generate()
         # WRITE command: Write the previously generated WAV to the given file.
         elif cmd[0] == 'WRITE':
            prep_wave.writeToFile(cmd[1])
            prep_wave = None
         # DROP command: Drop the previously generated WAV.
         elif cmd[0] == 'DROP':
            prep_wave = None
