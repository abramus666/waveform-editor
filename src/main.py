
from src import axis, plot, wavegen

import re
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkfiledialog

INTEGER_SELECT_WIDTH = 5
INTEGER_ENTRY_WIDTH  = 8

#===============================================================================
def pad(dir, north = 0, south = 0, east = 0, west = 0):
   return {
      'padx': (
         west  + 3 if ('W' in dir) else 0,
         east  + 3 if ('E' in dir) else 0),
      'pady': (
         north + 3 if ('N' in dir) else 0,
         south + 3 if ('S' in dir) else 0)}

#===============================================================================
class IntegerSelect:

   def __init__(self, tk_parent, text, init_value, valid_values, callback):
      self.value = init_value
      self.callback = callback
      # String variable associated with the combobox.
      self.string_var = tk.StringVar()
      self.string_var.set(str(init_value))
      self.string_var.trace_add('write', self.onUpdate)
      # Frame.
      self.frame = tk.Frame(tk_parent)
      # Label.
      self.label = tk.Label(self.frame, text = text)
      # Combobox.
      self.combo = ttk.Combobox(self.frame, textvariable = self.string_var, width = INTEGER_SELECT_WIDTH)
      self.combo['values'] = [str(v) for v in valid_values]
      self.combo.state(['readonly'])
      # Configure inner grid.
      self.label.grid(row = 0, column = 0, sticky = 'NE', **pad('E'))
      self.combo.grid(row = 0, column = 1, sticky = 'NE')

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def get(self):
      return self.value

   def onUpdate(self, *args):
      v = int(self.string_var.get())
      if self.value != v:
         self.value = v
         self.callback(v)

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
      self.label.grid(row = 0, column = 0, sticky = 'NE', **pad('E'))
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
class WaveListWidget:

   def __init__(self, tk_parent, min_count, max_count, callback):
      self.callback = callback
      self.min_count = min_count
      self.count = min_count
      self.index = 0 if (min_count > 0) else None
      # Frame.
      self.frame = ttk.LabelFrame(tk_parent, text = 'Waves', labelanchor = 'n')
      # Add/select buttons.
      self.item_btn = [ttk.Button(self.frame) for i in range(max_count)]
      # Delete button.
      self.delete_btn = ttk.Button(self.frame)
      # Configure buttons.
      self.configureButtons()
      # Configure inner grid.
      for ix,item in enumerate(self.item_btn):
         item.grid(row = ix, column = 0, sticky = 'NEW', **pad('NEW'))
      self.delete_btn.grid(row = max_count, column = 0, sticky = 'SEW', **pad('NSEW'))
      self.frame.rowconfigure(max_count, weight = 1)

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def createOnSelectFunc(self, index):
      return lambda: self.onSelect(index)

   def configureButtons(self):
      ix = 0
      # Buttons to select existing items.
      while ix < self.count:
         self.item_btn[ix].configure(
            text = '#{}'.format(ix+1),
            command = self.createOnSelectFunc(ix))
         self.item_btn[ix].state(['!disabled', 'pressed' if (ix == self.index) else '!pressed'])
         ix += 1
      # Button to add another item, followed by disabled buttons.
      while ix < len(self.item_btn):
         self.item_btn[ix].configure(
            text = 'Add',
            command = self.onAdd)
         self.item_btn[ix].state(['!disabled' if (ix == self.count) else 'disabled', '!pressed'])
         ix += 1
      # Button to delete last item.
      self.delete_btn.configure(
         text = 'Delete',
         command = self.onDelete)
      self.delete_btn.state(['!disabled' if (self.count > self.min_count) else 'disabled'])

   def onSelect(self, index):
      if self.index != index:
         self.index = index
         self.configureButtons()
         self.callback.onWaveSelect(self.index)
      else:
         self.configureButtons()

   def onAdd(self):
      self.count += 1
      # Select the newly added item.
      self.onSelect(self.count-1)

   def onDelete(self):
      self.count -= 1
      # Select the last item if the currently selected item is deleted.
      if self.index == self.count:
         self.onSelect(self.count-1 if (self.count > 0) else None)
      else:
         self.configureButtons()
      self.callback.onWaveDelete(self.count)

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
      self.custom_btn = ttk.Button(self.frame, text = 'Define', state = 'disabled', command = self.onCustomDefine)
      # Configure inner grid.
      for ix,item in enumerate(self.radio):
         item.grid(row = ix, column = 0, sticky = 'NW', **pad('EW'))
      ix = len(self.radio)
      self.custom_radio.grid(row = ix, column = 0, sticky = 'NW', **pad('EW'))
      self.custom_btn.grid(row = ix+1, column = 0, sticky = 'NEW', **pad('SEW', east = 20))

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def serialize(self):
      return self.value

   def deserialize(self, input):
      self.value = input
      self.string_var.set(self.value)
      self.custom_btn.configure(state = 'normal' if (self.value == 'Custom') else 'disabled')

   def onCustomDefine(self):
      pass

   def onUpdate(self, *args):
      s = self.string_var.get()
      if self.value != s:
         self.deserialize(s)
         self.callback()

#===============================================================================
class SoundWidget:

   def __init__(self, tk_parent, callback):
      self.callback = callback
      self.playing = False
      # Frame.
      self.frame = ttk.LabelFrame(tk_parent, text = 'Sound', labelanchor = 'n')
      # Sample frequency select.
      self.sample_freq = IntegerSelect(self.frame,
         text         = 'Sample freq [Hz]',
         init_value   = 44100,
         valid_values = (11025, 22050, 44100),
         callback     = lambda v: callback.onSoundChange())
      # Total time entry.
      self.time_entry = IntegerEntry(self.frame,
         text        = 'Total time [ms]',
         init_value  = 500,
         lower_limit = 10,
         upper_limit = 5000,
         callback    = callback.onTimeChange)
      # Play/stop button.
      self.playstop_btn = ttk.Button(self.frame, text = 'Play', command = self.onPlayStop)
      # Export button.
      self.export_btn = ttk.Button(self.frame, text = 'Export', command = callback.onExport)
      # Configure inner grid.
      self.sample_freq.grid (row = 0, column = 0, sticky = 'NE', **pad('NSEW'))
      self.time_entry.grid  (row = 1, column = 0, sticky = 'NE', **pad('SEW'))
      self.playstop_btn.grid(row = 2, column = 0, sticky = 'NE', **pad('SEW'))
      self.export_btn.grid  (row = 3, column = 0, sticky = 'NE', **pad('SEW'))

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def serialize(self):
      return {
         'Sample frequency [Hz]': self.sample_freq.get(),
         'Total time [ms]': self.time_entry.get()}

   def deserialize(self, input):
      self.sample_freq.set(input['Sample frequency [Hz]'])
      self.time_entry.set(input['Total time [ms]'])

   def isPlaying(self):
      return self.playing

   def onPlayStop(self):
      if not self.playing:
         self.playing = True
         self.playstop_btn.configure(text = 'Stop')
         self.callback.onPlay()
      else:
         self.playing = False
         self.playstop_btn.configure(text = 'Play')
         self.callback.onStop()

#===============================================================================
class WaveformEditor:

   def __init__(self):
      self.wnd = tk.Tk()
      self.wnd.title('Waveform Editor')
      # Wave generator thread.
      self.wavegen_thread = wavegen.Thread()
      # Wave list widget.
      self.wavelist_widget = WaveListWidget(self.wnd, 1, 4, self)
      # Waveform widget.
      self.waveform_widget = WaveformWidget(self.wnd, self.onSoundChange)
      # Sound widget.
      self.sound_widget = SoundWidget(self.wnd, self)
      # Axes.
      self.time_axis = axis.Time(self.sound_widget.serialize())
      self.frequency_axis = axis.Frequency(20, 20000)
      self.amplitude_axis = axis.Amplitude(60)
      # Frequency plot.
      self.frequency_plot = plot.Panel(self.wnd,
         width    = 400,
         height   = 200,
         x_axis   = self.time_axis,
         y_axis   = self.frequency_axis,
         callback = self.onSoundChange)
      # Amplitude plot.
      self.amplitude_plot = plot.Panel(self.wnd,
         width    = 400,
         height   = 200,
         x_axis   = self.time_axis,
         y_axis   = self.amplitude_axis,
         callback = self.onSoundChange)
      # Keep zoom level on both plots in sync.
      self.frequency_plot.installViewChangeCallback(lambda param: self.amplitude_plot.setView(param))
      self.amplitude_plot.installViewChangeCallback(lambda param: self.frequency_plot.setView(param))
      # Configure grid.
      self.wnd.columnconfigure(0, weight = 0)
      self.wnd.columnconfigure(1, weight = 1)
      self.wnd.columnconfigure(2, weight = 0)
      self.wnd.columnconfigure(3, weight = 0)
      self.wnd.rowconfigure   (0, weight = 1)
      self.wnd.rowconfigure   (1, weight = 1)
      self.wavelist_widget.grid(column = 0, row = 0, rowspan = 2, sticky = 'NSW', **pad('SEW'))
      self.frequency_plot.grid (column = 1, row = 0, sticky = 'NSEW')
      self.amplitude_plot.grid (column = 1, row = 1, sticky = 'NSEW')
      self.waveform_widget.grid(column = 2, row = 0, rowspan = 2, sticky = 'NE', **pad('SEW'))
      self.sound_widget.grid   (column = 3, row = 0, rowspan = 2, sticky = 'NE', **pad('SE'))
      # Stored waves.
      self.default_wave = self.serializeCurrentWave()
      self.wave_list = [self.default_wave]
      self.wave_index = 0

   def serializeCurrentWave(self):
      return {
         'Frequency axis': self.frequency_axis.serialize(),
         'Amplitude axis': self.amplitude_axis.serialize(),
         'Frequency curve': self.frequency_plot.serialize(),
         'Amplitude curve': self.amplitude_plot.serialize(),
         'Waveform': self.waveform_widget.serialize()}

   def deserializeCurrentWave(self, input_wave):
      self.frequency_axis.deserialize(input_wave['Frequency axis'])
      self.amplitude_axis.deserialize(input_wave['Amplitude axis'])
      self.frequency_plot.deserialize(input_wave['Frequency curve'])
      self.amplitude_plot.deserialize(input_wave['Amplitude curve'])
      self.waveform_widget.deserialize(input_wave['Waveform'])
      self.frequency_plot.updateGrid()
      self.amplitude_plot.updateGrid()

   def serialize(self):
      self.wave_list[self.wave_index] = self.serializeCurrentWave()
      return {
         'Waves': self.wave_list[:],
         'Sound': self.sound_widget.serialize()}

   def deserialize(self, input):
      self.sound_widget.deserialize(input['Sound'])
      self.time_axis.deserialize(input['Sound'])
      self.wave_list = input['Waves']
      self.wave_index = 0
      self.deserializeCurrentWave(self.wave_list[self.wave_index])

   def onWaveSelect(self, index):
      if self.wave_index != index:
         self.wave_list[self.wave_index] = self.serializeCurrentWave()
         self.wave_index = index
         new_wave = False
         while not (len(self.wave_list) > index):
            self.wave_list.append(self.default_wave)
            new_wave = True
         self.deserializeCurrentWave(self.wave_list[self.wave_index])
         if new_wave:
            self.onSoundChange()

   def onWaveDelete(self, index):
      del self.wave_list[index]
      self.onSoundChange()

   def onTimeChange(self, value):
      self.time_axis.set(value)
      self.frequency_plot.updateGrid()
      self.amplitude_plot.updateGrid()
      self.onSoundChange()

   def onSoundChange(self):
      if self.sound_widget.isPlaying():
         self.wavegen_thread.play(self.serialize())

   def onPlay(self):
      self.wavegen_thread.play(self.serialize())

   def onStop(self):
      self.wavegen_thread.stop()

   def onExport(self):
      self.wavegen_thread.prepare(self.serialize())
      path = tkfiledialog.asksaveasfilename(
         title = 'Export',
         defaultextension = '.wav',
         filetypes = (('Waveform audio format (*.wav)', '.wav'),))
      if path:
         self.wavegen_thread.write(path)
      else:
         self.wavegen_thread.drop()

   def run(self):
      self.wnd.mainloop()
      self.wavegen_thread.quit()
