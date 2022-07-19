
from src import axis, plot, wavegen

import re
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkfiledialog

INTEGER_ENTRY_WIDTH = 5

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
      # Entry.
      self.entry = ttk.Entry(self.frame, textvariable = self.string_var, width = INTEGER_ENTRY_WIDTH)
      self.entry.bind('<Return>', self.onCommit)
      self.entry.bind('<FocusOut>', self.onCommit)
      # Configure inner grid.
      self.label.grid(row = 0, column = 0, sticky = 'NE', padx = (0,5))
      self.entry.grid(row = 0, column = 1, sticky = 'NE')

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

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
class WaveformWidget:

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
      # Basic waveforms.
      self.radio = [ttk.Radiobutton(self.frame, text = v, variable = self.string_var, value = v) for v in basic_waveforms]
      # Custom waveform.
      self.custom_radio = ttk.Radiobutton(self.frame, text = 'Custom', variable = self.string_var, value = 'Custom')
      self.custom_btn = ttk.Button(self.frame, text = 'Define', command = self.onCustomDefine)
      self.custom_btn.configure(state = 'disabled')
      # Configure inner grid.
      for ix,item in enumerate(self.radio):
         item.grid(row = ix, column = 0, sticky = 'NW', padx = 5)
      ix = len(self.radio)
      self.custom_radio.grid(row = ix, column = 0, sticky = 'NW', padx = 5)
      self.custom_btn.grid(row = ix+1, column = 0, sticky = 'NEW', padx = (5+18,5), pady = (0,5))

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def serialize(self):
      return self.value

   def deserialize(self, input):
      pass

   def onCustomDefine(self):
      pass

   def onUpdate(self, *args):
      s = self.string_var.get()
      if self.value != s:
         self.value = s
         self.custom_btn.configure(state = 'normal' if (s == 'Custom') else 'disabled')
         self.callback()

#===============================================================================
class SoundWidget:

   def __init__(self, tk_parent, callback):
      self.callback = callback
      self.playing = False
      # Frame.
      self.frame = ttk.LabelFrame(tk_parent, text = 'Sound', labelanchor = 'n')
      # Total time entry.
      self.time_entry = IntegerEntry(self.frame,
         text        = 'Total time [ms]',
         init_value  = 500,
         lower_limit = 10,
         upper_limit = 5000,
         callback    = callback.onTimeChange)
      # Play/stop button.
      self.play_btn = ttk.Button(self.frame, text = 'Play', command = self.onPlayStop)
      # Save button.
      self.save_btn = ttk.Button(self.frame, text = 'Save', command = callback.onSave)
      # Configure inner grid.
      self.time_entry.grid(row = 0, column = 0, sticky = 'NE', padx = 5, pady = 5)
      self.play_btn.grid  (row = 1, column = 0, sticky = 'NE', padx = 5, pady = (0,5))
      self.save_btn.grid  (row = 2, column = 0, sticky = 'NE', padx = 5, pady = (0,5))

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def getTotalTime(self):
      return self.time_entry.get()

   def isPlaying(self):
      return self.playing

   def onPlayStop(self):
      if not self.playing:
         self.playing = True
         self.play_btn.configure(text = 'Stop')
         self.callback.onPlay()
      else:
         self.playing = False
         self.play_btn.configure(text = 'Play')
         self.callback.onStop()

#===============================================================================
class WaveformEditor:

   def __init__(self):
      self.wnd = tk.Tk()
      self.wnd.title('Waveform Editor')
      # Wave generator thread.
      self.wavegen_thread = wavegen.Thread()
      # Waveform widget.
      self.waveform_widget = WaveformWidget(self.wnd, self.onWaveChange)
      # Sound widget.
      self.sound_widget = SoundWidget(self.wnd, self)
      # Axes.
      self.time_axis = axis.Time(self.sound_widget.getTotalTime())
      self.frequency_axis = axis.Frequency(20, 20000)
      self.amplitude_axis = axis.Amplitude(60)
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
      self.wnd.columnconfigure(0, weight = 1)
      self.wnd.columnconfigure(1, weight = 0)
      self.wnd.columnconfigure(2, weight = 0)
      self.wnd.rowconfigure   (0, weight = 1)
      self.wnd.rowconfigure   (1, weight = 1)
      self.frequency_plot.grid (row = 0, column = 0, sticky = 'NSEW')
      self.amplitude_plot.grid (row = 1, column = 0, sticky = 'NSEW')
      self.waveform_widget.grid(row = 0, column = 1, rowspan = 2, sticky = 'NE', padx = 5)
      self.sound_widget.grid   (row = 0, column = 2, rowspan = 2, sticky = 'NE', padx = (0,5))

   def serializeCurrentWave(self):
      return {
         'Time axis': self.time_axis.serialize(),
         'Frequency axis': self.frequency_axis.serialize(),
         'Amplitude axis': self.amplitude_axis.serialize(),
         'Frequency': self.frequency_plot.serialize(),
         'Amplitude': self.amplitude_plot.serialize(),
         'Waveform': self.waveform_widget.serialize()}

   def serialize(self):
      return {
         'Waves': [self.serializeCurrentWave()],
         'Sample frequency [Hz]': 44100}

   def onTimeChange(self, value):
      self.time_axis.set(value)
      self.frequency_plot.updateGrid()
      self.amplitude_plot.updateGrid()
      if self.sound_widget.isPlaying():
         self.wavegen_thread.play(self.serialize())

   def onWaveChange(self):
      if self.sound_widget.isPlaying():
         self.wavegen_thread.play(self.serialize())

   def onPlay(self):
      self.wavegen_thread.play(self.serialize())

   def onStop(self):
      self.wavegen_thread.stop()

   def onSave(self):
      self.wavegen_thread.prepare(self.serialize())
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
