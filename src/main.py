
from src import plot, wavegen

import math, re
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkfiledialog

DEF_TOTAL_TIME_MS = 500
MAX_TOTAL_TIME_MS = 9999
MIN_TOTAL_TIME_MS = 1

#===============================================================================
class TimeAxis:

   def __init__(self, total_time_ms):
      self.total_time_ms = total_time_ms

   def clone(self):
      return TimeAxis(self.total_time_ms)

   def getUnit(self):
      return '[ms]'

   # Convert from time in milliseconds to range [0,1].
   def convertFrom(self, t):
      return (t / self.total_time_ms)

   # Convert from range [0,1] to time in milliseconds.
   def convertTo(self, x):
      return (x * self.total_time_ms)

#===============================================================================
class FrequencyAxis:

   def __init__(self, min_freq_hz = 50, max_freq_hz = 12000):
      self.min_freq_hz = min_freq_hz
      self.max_freq_hz = max_freq_hz

   def clone(self):
      return FrequencyAxis(self.min_freq_hz, self.max_freq_hz)

   def getUnit(self):
      return '[Hz]'

   # Convert from range [0,1] to frequency in Hz.
   def convertTo(self, y):
      return (10.0**((1.0 - y) * math.log10(self.min_freq_hz / self.max_freq_hz)) * self.max_freq_hz)

#===============================================================================
class AmplitudeAxis:

   def __init__(self, amplitude_range_db = 50):
      self.amplitude_range_db = amplitude_range_db

   def clone(self):
      return AmplitudeAxis(self.amplitude_range_db)

   def getUnit(self):
      return '[dB]'

   # Convert from range [0,1] to amplitude in dB.
   def convertTo(self, y):
      return ((y - 1.0) * self.amplitude_range_db)

#===============================================================================
class WaveformEditor:

   def __init__(self):
      self.wnd = tk.Tk()
      self.wnd.title('Waveform Editor')
      self.wnd.columnconfigure(0, weight = 1)
      self.wnd.columnconfigure(1, weight = 0)
      self.wnd.rowconfigure(0, weight = 1)
      self.wnd.rowconfigure(1, weight = 1)
      # Frequency and amplitude plots.
      self.time_axis = TimeAxis(DEF_TOTAL_TIME_MS)
      self.frequency_axis = FrequencyAxis()
      self.amplitude_axis = AmplitudeAxis()
      self.frequency_plot = plot.Panel(self, 0, 0, 400, 200, self.time_axis, self.frequency_axis)
      self.amplitude_plot = plot.Panel(self, 1, 0, 400, 200, self.time_axis, self.amplitude_axis)
      # Toolbox frame.
      self.toolbox = ttk.Frame(self.wnd)
      self.toolbox.grid(row = 0, column = 1, rowspan = 2, sticky = 'N')
      self.toolbox.columnconfigure(0, weight = 0)
      self.toolbox.rowconfigure(0, weight = 0)
      self.toolbox.rowconfigure(1, weight = 0)
      self.toolbox.rowconfigure(2, weight = 0)
      # Total time entry.
      self.total_time_var = tk.StringVar()
      self.total_time_var.trace_add('write', self.onTotalTimeChange)
      self.total_time_entry = ttk.Entry(self.toolbox, textvariable = self.total_time_var)
      self.total_time_entry.grid(row = 0, column = 0, sticky = 'N', padx = 5, pady = 5)
      # Play button.
      self.play_button = ttk.Button(self.toolbox, text = 'Play', command = self.onPlay)
      self.play_button.grid(row = 1, column = 0, sticky = 'N', padx = 5, pady = (0,5))
      self.playing = False
      # Save button.
      self.save_button = ttk.Button(self.toolbox, text = 'Save', command = self.onSave)
      self.save_button.grid(row = 2, column = 0, sticky = 'N', padx = 5, pady = (0,5))

      self.wavegen_thread = wavegen.Thread()

   def getTk(self):
      return self.wnd

   def getWaveGenParams(self):
      return (
         wavegen.Curve(self.frequency_plot),
         wavegen.Curve(self.amplitude_plot),
         44100)

   def onViewChangeRequest(self, param):
      self.frequency_plot.setView(param)
      self.amplitude_plot.setView(param)

   def onCurveChange(self):
      if self.playing:
         self.wavegen_thread.play(self.getWaveGenParams())

   def onPlay(self):
      if not self.playing:
         self.playing = True
         self.play_button.configure(text = 'Stop')
         self.wavegen_thread.play(self.getWaveGenParams())
      else:
         self.playing = False
         self.play_button.configure(text = 'Play')
         self.wavegen_thread.stop()

   def onSave(self):
      self.wavegen_thread.prepare(self.getWaveGenParams())
      path = tkfiledialog.asksaveasfilename(
         title = 'Save',
         defaultextension = '.wav',
         filetypes = (('Waveform audio format (*.wav)', '.wav'),))
      if path:
         self.wavegen_thread.write(path)
      else:
         self.wavegen_thread.drop()

   def onTotalTimeChange(self, *args):
      s = self.total_time_var.get()
      if len(s) > 0 and not s.isdigit():
         s = re.sub(r'[^\d]+', '', s)
         self.total_time_var.set(s)
      if len(s) > 0:
         n = min(max(int(s), MIN_TOTAL_TIME_MS), MAX_TOTAL_TIME_MS)
         self.total_time_var.set(str(n))
         self.time_axis.total_time_ms = n
         self.frequency_plot.grid.draw()
         self.amplitude_plot.grid.draw()
         if self.playing:
            self.wavegen_thread.play(self.getWaveGenParams())

   def run(self):
      self.wnd.mainloop()
      self.wavegen_thread.quit()
