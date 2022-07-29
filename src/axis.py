
import math

#===============================================================================
class Axis:

   def __init__(self, *args):
      self.callbacks = []
      if len(args) == 1 and isinstance(args[0], dict):
         self.deserialize(args[0])
      elif len(args) > 0:
         self.set(*args)

   def registerCallback(self, callback):
      self.callbacks.append(callback)

   def onUpdate(self):
      for callback in self.callbacks:
         callback()

#===============================================================================
class Time(Axis):

   def set(self, total_time_ms):
      self.total_time_ms = total_time_ms
      self.onUpdate()

   def serialize(self):
      return {'Total time [ms]': self.total_time_ms}

   def deserialize(self, input):
      self.set(input['Total time [ms]'])

   def getUnit(self):
      return '[ms]'

   # Convert from range [0,1] to time in milliseconds.
   def convertTo(self, x):
      return (x * self.total_time_ms)

#===============================================================================
class Frequency(Axis):

   def set(self, min_freq_hz, max_freq_hz):
      self.min_freq_hz = min_freq_hz
      self.max_freq_hz = max_freq_hz
      self.onUpdate()

   def serialize(self):
      return {
         'Min frequency [Hz]': self.min_freq_hz,
         'Max frequency [Hz]': self.max_freq_hz}

   def deserialize(self, input):
      self.set(
         input['Min frequency [Hz]'],
         input['Max frequency [Hz]'])

   def getUnit(self):
      return '[Hz]'

   # Convert from range [0,1] to frequency in Hz.
   def convertTo(self, y):
      return (10.0**((1.0 - y) * math.log10(self.min_freq_hz / self.max_freq_hz)) * self.max_freq_hz)

#===============================================================================
class Amplitude(Axis):

   def set(self, amplitude_range_db):
      self.amplitude_range_db = amplitude_range_db
      self.onUpdate()

   def serialize(self):
      return {'Amplitude range [dB]': self.amplitude_range_db}

   def deserialize(self, input):
      self.set(input['Amplitude range [dB]'])

   def getUnit(self):
      return '[dB]'

   # Convert from range [0,1] to amplitude in dB.
   def convertTo(self, y):
      return ((y - 1.0) * self.amplitude_range_db)

#===============================================================================
class Angle(Axis):

   def getUnit(self):
      return '[deg]'

   # Convert from range [0,1] to [0,360].
   def convertTo(self, x):
      return (x * 360.0)

#===============================================================================
class Unit(Axis):

   def getUnit(self):
      return ''

   # Convert from range [0,1] to [-1,1].
   def convertTo(self, x):
      return (x * 2.0 - 1.0)
