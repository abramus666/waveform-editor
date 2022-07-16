
from src import plot, wavegen

import math, re
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkfiledialog

INTEGER_ENTRY_WIDTH = 5

#===============================================================================
class TimeAxis:

   def __init__(self, total_time_ms):
      self.set(total_time_ms)

   def set(self, total_time_ms):
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

   def __init__(self, min_freq_hz, max_freq_hz):
      self.set(min_freq_hz, max_freq_hz)

   def set(self, min_freq_hz, max_freq_hz):
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

   def __init__(self, amplitude_range_db):
      self.set(amplitude_range_db)

   def set(self, amplitude_range_db):
      self.amplitude_range_db = amplitude_range_db

   def clone(self):
      return AmplitudeAxis(self.amplitude_range_db)

   def getUnit(self):
      return '[dB]'

   # Convert from range [0,1] to amplitude in dB.
   def convertTo(self, y):
      return ((y - 1.0) * self.amplitude_range_db)

#===============================================================================
class IntegerEntry:

   def __init__(self, tk_parent, text, init_value, lower_limit, upper_limit, callback):
      self.value = init_value
      self.lower_limit = lower_limit
      self.upper_limit = upper_limit
      self.callback = callback
      self.max_digits = len(str(upper_limit))
      # String variable associated with the entry.
      self.string_var = tk.StringVar()
      self.string_var.set(str(init_value))
      self.string_var.trace_add('write', self.onUpdate)
      # Frame.
      self.frame = tk.Frame(tk_parent)
      # Label.
      self.label = tk.Label(self.frame, text = text)
      self.label.grid(row = 0, column = 0, sticky = 'NE', padx = (0,5))
      # Entry.
      self.entry = ttk.Entry(self.frame, textvariable = self.string_var, width = INTEGER_ENTRY_WIDTH)
      self.entry.grid(row = 0, column = 1, sticky = 'NE')
      self.entry.bind('<Return>', self.onCommit)
      self.entry.bind('<FocusOut>', self.onCommit)

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def configure(self, **kwargs):
      self.label.configure(**kwargs)
      self.entry.configure(**kwargs)

   def get(self):
      return self.value

   def onUpdate(self, *args):
      s = self.string_var.get()
      # Prevent user from entering non-digit characters.
      if len(s) > 0 and not s.isdigit():
         s = re.sub(r'[^\d]+', '', s)
      # Prevent user from entering too many digits.
      if len(s) > self.max_digits:
         s = s[:self.max_digits]
      self.string_var.set(s)

   def onCommit(self, event):
      s = self.string_var.get()
      if len(s) > 0:
         # Apply limits.
         v = min(max(int(s), self.lower_limit), self.upper_limit)
         self.string_var.set(str(v))
         # Execute callback if the value is changed.
         if self.value != v:
            self.value = v
            self.callback(v)
      else:
         # Bring back the last value is the entry is empty.
         self.string_var.set(str(self.value))

#===============================================================================
class WaveformSelector:

   def __init__(self, tk_parent, callback):
      basic_waveforms = ('Sine', 'Square', 'Triangle', 'Sawtooth')
      self.value = basic_waveforms[0]
      self.callback = callback
      # String variable associated with the radio button.
      self.string_var = tk.StringVar()
      self.string_var.set(self.value)
      self.string_var.trace_add('write', self.onUpdate)
      # Frame.
      self.frame = ttk.LabelFrame(tk_parent, text = 'Waveform', labelanchor = 'n')
      # Radio button.
      self.radio = [ttk.Radiobutton(self.frame, text = v, variable = self.string_var, value = v) for v in basic_waveforms]
      for ix,item in enumerate(self.radio):
         item.grid(row = ix, column = 0, sticky = 'NW', padx = 5)

      self.custom_radio = ttk.Radiobutton(self.frame, text = 'Custom', variable = self.string_var, value = 'Custom')
      self.custom_btn = ttk.Button(self.frame, text = 'Define', command = self.onCustomDefine)

      self.custom_radio.grid (row = 7, column = 0, sticky = 'NW', padx = 5)
      self.custom_btn.grid(row = 8, column = 0, sticky = 'NEW', padx = (5+18,5), pady = (0,5))
      self.custom_btn.configure(state = 'disabled')

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def get(self):
      return self.value

   def onCustomDefine(self):
      pass

   def onUpdate(self, *args):
      s = self.string_var.get()
      if self.value != s:
         self.value = s
         self.custom_btn.configure(state = 'normal' if (s == 'Custom') else 'disabled')
         self.callback()

#===============================================================================
class WaveformEditor:

   def __init__(self):
      self.wnd = tk.Tk()
      self.wnd.title('Waveform Editor')
      self.wnd.columnconfigure(0, weight = 1)
      self.wnd.columnconfigure(1, weight = 0)
      self.wnd.columnconfigure(2, weight = 0)
      self.wnd.rowconfigure(0, weight = 1)
      self.wnd.rowconfigure(1, weight = 1)

      # Toolbox frame.
      self.toolbox = ttk.LabelFrame(self.wnd, text = 'Sound', labelanchor = 'n')
      self.toolbox.grid(row = 0, column = 2, rowspan = 2, sticky = 'NE')
      self.toolbox.columnconfigure(0, weight = 0)
      self.toolbox.rowconfigure(0, weight = 0)
      self.toolbox.rowconfigure(1, weight = 0)
      self.toolbox.rowconfigure(2, weight = 0)
      # Total time entry.
      self.total_time = IntegerEntry(self.toolbox,
         text        = 'Total time [ms]',
         init_value  = 500,
         lower_limit = 10,
         upper_limit = 5000,
         callback    = self.onTotalTimeChange)
      # Play button.
      self.playing = False
      self.play_button = ttk.Button(self.toolbox, text = 'Play', command = self.onPlay)
      # Save button.
      self.save_button = ttk.Button(self.toolbox, text = 'Save', command = self.onSave)
      # Configure grid.
      self.total_time.grid (row = 0, column = 0, sticky = 'NE', padx = 5, pady = 5)
      self.play_button.grid(row = 1, column = 0, sticky = 'NE', padx = 5, pady = (0,5))
      self.save_button.grid(row = 2, column = 0, sticky = 'NE', padx = 5, pady = (0,5))

      self.waveform_select = WaveformSelector(self.wnd, self.onWaveChange)
      self.waveform_select.grid(row = 0, column = 1, rowspan = 2, sticky = 'NE', padx = 5, pady = (0,5))

      # Axes.
      self.time_axis = TimeAxis(self.total_time.get())
      self.frequency_axis = FrequencyAxis(20, 20000)
      self.amplitude_axis = AmplitudeAxis(60)
      # Frequency plot.
      self.frequency_plot = plot.Panel(self.wnd,
         width    = 400,
         height   = 200,
         x_axis   = self.time_axis,
         y_axis   = self.frequency_axis,
         callback = self.onWaveChange)
      # Amplitude plot.
      self.amplitude_plot = plot.Panel(self.wnd,
         width    = 400,
         height   = 200,
         x_axis   = self.time_axis,
         y_axis   = self.amplitude_axis,
         callback = self.onWaveChange)
      # Keep zoom level on both plots in sync.
      self.frequency_plot.installViewChangeCallback(lambda param: self.amplitude_plot.setView(param))
      self.amplitude_plot.installViewChangeCallback(lambda param: self.frequency_plot.setView(param))
      # Configure grid.
      self.frequency_plot.grid(row = 0, column = 0, sticky = 'NSEW')
      self.amplitude_plot.grid(row = 1, column = 0, sticky = 'NSEW')

      # Wave generator thread.
      self.wavegen_thread = wavegen.Thread()

   def getWaveGenParams(self):
      return (
         wavegen.Curve(self.frequency_plot),
         wavegen.Curve(self.amplitude_plot),
         self.waveform_select.get(),
         44100)

   def onTotalTimeChange(self, value):
      self.time_axis.set(value)
      self.frequency_plot.updateGrid()
      self.amplitude_plot.updateGrid()
      if self.playing:
         self.wavegen_thread.play(self.getWaveGenParams())

   def onWaveChange(self):
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

   def run(self):
      self.wnd.mainloop()
      self.wavegen_thread.quit()
