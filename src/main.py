
from src import axis, plot, wavegen

import json, re
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkfiledialog

PROGRAM_NAME       = 'Waveform Editor'

SAMPLING_RATES_HZ  = (8000, 11025, 16000, 22050, 32000, 44100, 48000)
MAX_WAVE_COUNT     = 8

MIN_TOTAL_TIME_MS  = 10
MAX_TOTAL_TIME_MS  = 10000
MIN_FREQUENCY_HZ   = 20
MAX_FREQUENCY_HZ   = 20000
AMPLITUDE_RANGE_DB = 60

# That gives roughly the same width for both.
INTEGER_SELECT_WIDTH = 5
INTEGER_ENTRY_WIDTH  = 5+3

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
class StringVariable:

   def __init__(self, init_value, callback):
      self.callback = callback
      self.callback_lock = False
      self.string_var = tk.StringVar()
      self.string_var.set(init_value)
      self.string_var.trace_add('write', self.onUpdate)

   def getTkVar(self):
      return self.string_var

   def get(self):
      return self.string_var.get()

   def set(self, value):
      # Do not trigger the callback when setting the variable explicitly.
      self.callback_lock = True
      self.string_var.set(value)
      self.callback_lock = False

   def onUpdate(self, *args):
      if not self.callback_lock:
         self.callback(self.string_var.get())

#===============================================================================
class IntegerSelect:

   def __init__(self, tk_parent, text, width, init_value, valid_values, callback):
      self.value = init_value
      self.valid_values = valid_values
      self.callback = callback
      # String variable associated with the combobox.
      self.string_var = StringVariable(str(init_value), self.onUpdate)
      # Frame.
      self.frame = tk.Frame(tk_parent)
      # Label.
      self.label = tk.Label(self.frame, text = text)
      # Combobox.
      self.combo = ttk.Combobox(self.frame, textvariable = self.string_var.getTkVar(), width = width)
      self.combo['values'] = [str(v) for v in valid_values]
      self.combo.state(['readonly'])
      # Configure inner grid.
      self.label.grid(row = 0, column = 0, sticky = 'NE', **pad('E'))
      self.combo.grid(row = 0, column = 1, sticky = 'NE')

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def configure(self, **kwargs):
      self.label.configure(**kwargs)
      self.combo.configure(**kwargs)

   def get(self):
      return self.value

   def set(self, value):
      if value in self.valid_values:
         self.value = value
         self.string_var.set(str(self.value))

   def onUpdate(self, value):
      v = int(value)
      if self.value != v:
         self.value = v
         self.callback(v)

#===============================================================================
class IntegerEntry:

   def __init__(self, tk_parent, text, width, init_value, lower_limit, upper_limit, callback):
      self.value = init_value
      self.lower_limit = lower_limit
      self.upper_limit = upper_limit
      self.callback = callback
      self.max_digits = len(str(upper_limit))
      # String variable associated with the entry.
      self.string_var = StringVariable(str(init_value), self.onUpdate)
      # Frame.
      self.frame = tk.Frame(tk_parent)
      # Label.
      self.label = tk.Label(self.frame, text = text)
      # Entry.
      self.entry = ttk.Entry(self.frame, textvariable = self.string_var.getTkVar(), width = width)
      self.entry.bind('<Return>', self.onCommit)
      self.entry.bind('<FocusOut>', self.onCommit)
      # Configure inner grid.
      self.label.grid(row = 0, column = 0, sticky = 'NE', **pad('E'))
      self.entry.grid(row = 0, column = 1, sticky = 'NE')

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def configure(self, **kwargs):
      self.label.configure(**kwargs)
      self.entry.configure(**kwargs)

   def get(self):
      return self.value

   def set(self, value):
      # Apply limits.
      self.value = min(max(int(value), self.lower_limit), self.upper_limit)
      self.string_var.set(str(self.value))

   def onUpdate(self, value):
      # Prevent user from entering non-digit characters.
      if len(value) > 0 and not value.isdigit():
         value = re.sub(r'[^\d]+', '', s)
      # Prevent user from entering too many digits.
      if len(value) > self.max_digits:
         value = value[:self.max_digits]
      self.string_var.set(value)

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
      # Frame.
      self.frame = ttk.LabelFrame(tk_parent, text = 'Waves', labelanchor = 'n')
      # Add/select buttons.
      self.item_btn = [ttk.Button(self.frame) for i in range(max_count)]
      # Delete button.
      self.delete_btn = ttk.Button(self.frame)
      # Set item count and configure buttons appropriately.
      self.setCount(min_count)
      # Configure inner grid.
      for ix,item in enumerate(self.item_btn):
         item.grid(row = ix, column = 0, sticky = 'NEW', **pad('NEW'))
      self.delete_btn.grid(row = max_count, column = 0, sticky = 'SEW', **pad('NSEW'))
      self.frame.rowconfigure(max_count, weight = 1)

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def setCount(self, count):
      self.count = count
      self.index = 0 if (self.min_count > 0) else None
      self.configureButtons()

   def createOnSelectFunc(self, index):
      return lambda: self.onSelect(index)

   def configureButtons(self):
      ix = 0
      # Buttons to select existing items.
      while ix < self.count:
         self.item_btn[ix].configure(
            text = ('[ #{} ]' if (ix == self.index) else '#{}').format(ix+1),
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
      self.index = index
      self.configureButtons()
      self.callback.onWaveSelect(self.index)

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
      waveform_types = ('Sine', 'Square', 'Triangle', 'Sawtooth', 'Noise', 'Custom')
      self.callback = callback
      # String variable associated with the radio button.
      self.string_var = StringVariable(waveform_types[0], self.onUpdate)
      # Frame.
      self.frame = ttk.LabelFrame(tk_parent, text = 'Waveform', labelanchor = 'n')
      # Waveform selection.
      self.radio = [
         ttk.Radiobutton(self.frame, text = v, variable = self.string_var.getTkVar(), value = v)
         for v in waveform_types]
      # Custom waveform button.
      self.custom_btn = ttk.Button(self.frame,
         text    = 'Define',
         state   = 'disabled',
         command = self.onCustomDefine)
      # Phase shift.
      self.phase_shift = IntegerEntry(self.frame,
         text        = 'Phase [°]',
         width       = 5,
         init_value  = 0,
         lower_limit = 0,
         upper_limit = 359,
         callback    = self.onUpdate)
      # Save initial value.
      self.value = self.determineValue()
      # Configure inner grid.
      for ix,item in enumerate(self.radio):
         item.grid(row = ix, column = 0, sticky = 'NW', **pad('EW'))
      ix = len(self.radio)
      self.custom_btn.grid (row = ix,   column = 0, sticky = 'NW', **pad('EW', west = 18))
      self.phase_shift.grid(row = ix+1, column = 0, sticky = 'NE', **pad('NSEW', north = 10))

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def serialize(self):
      return self.value

   def deserialize(self, input):
      self.value = input
      self.string_var.set(self.value['Type'])
      self.phase_shift.set(self.value.get('Phase [deg]', 0))
      self.configureElements()

   def configureElements(self):
      self.custom_btn.configure(state = 'normal' if (self.value['Type'] == 'Custom') else 'disabled')
      self.phase_shift.configure(state = 'normal' if (self.value['Type'] != 'Noise') else 'disabled')

   def determineValue(self):
      return {
         'Type': self.string_var.get(),
         'Phase [deg]': self.phase_shift.get()}

   def onCustomDefine(self):
      # TODO: Custom waveform (also morph between two waveforms).
      pass

   def onUpdate(self, value):
      v = self.determineValue()
      if self.value != v:
         self.value = v
         self.configureElements()
         self.callback()

#===============================================================================
class ZoomWidget:

   def __init__(self, tk_parent):
      zoom_modes = ('X axis', 'Y axis')
      # String variable associated with the radio button.
      self.string_var = StringVariable(zoom_modes[0], self.onUpdate)
      # Frame.
      self.frame = ttk.LabelFrame(tk_parent, text = 'Zoom', labelanchor = 'n')
      # Zoom mode selection.
      self.radio = [
         ttk.Radiobutton(self.frame, text = v, variable = self.string_var.getTkVar(), value = v)
         for v in zoom_modes]
      # Save initial value.
      self.value = self.string_var.get()
      # Configure inner grid.
      for ix,item in enumerate(self.radio):
         item.grid(row = ix, column = 0, sticky = 'NW', **pad('EW'))

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def getZoomMode(self):
      return self.value

   def onUpdate(self, value):
      self.value = value

#===============================================================================
class FileWidget:

   def __init__(self, tk_parent, callback):
      self.callback = callback
      # Frame.
      self.frame = ttk.LabelFrame(tk_parent, text = 'File', labelanchor = 'n')
      # Open/save buttons.
      self.open_btn = ttk.Button(self.frame, text = 'Open', command = callback.onOpen)
      self.save_btn = ttk.Button(self.frame, text = 'Save', command = callback.onSave)
      # Configure inner grid.
      self.open_btn.grid(row = 0, column = 0, sticky = 'NE', **pad('NSEW'))
      self.save_btn.grid(row = 1, column = 0, sticky = 'NE', **pad('SEW'))

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

#===============================================================================
class SoundWidget:

   def __init__(self, tk_parent, callback):
      self.callback = callback
      self.playing = False
      # Frame.
      self.frame = ttk.LabelFrame(tk_parent, text = 'Sound', labelanchor = 'n')
      # Sampling rate select.
      self.sampling_rate = IntegerSelect(self.frame,
         text         = 'Sampling rate [Hz]',
         width        = INTEGER_SELECT_WIDTH,
         init_value   = SAMPLING_RATES_HZ[-1],
         valid_values = SAMPLING_RATES_HZ,
         callback     = self.onSamplingRateChange)
      # Total time entry.
      self.total_time = IntegerEntry(self.frame,
         text        = 'Total time [ms]',
         width       = INTEGER_ENTRY_WIDTH,
         init_value  = 500,
         lower_limit = MIN_TOTAL_TIME_MS,
         upper_limit = MAX_TOTAL_TIME_MS,
         callback    = self.onTotalTimeChange)
      # Axes.
      self.time_axis = axis.Time(self.total_time.get())
      self.frequency_axis = axis.Frequency(MIN_FREQUENCY_HZ, MAX_FREQUENCY_HZ)
      self.amplitude_axis = axis.Amplitude(AMPLITUDE_RANGE_DB)
      # Play/stop button.
      self.playstop_btn = ttk.Button(self.frame, text = 'Play', command = self.onPlayStop)
      # Export button.
      self.export_btn = ttk.Button(self.frame, text = 'Export', command = callback.onExport)
      # Configure inner grid.
      self.sampling_rate.grid(row = 0, column = 0, sticky = 'NE', **pad('NSEW'))
      self.total_time.grid   (row = 1, column = 0, sticky = 'NE', **pad('SEW'))
      self.playstop_btn.grid (row = 2, column = 0, sticky = 'NE', **pad('SEW'))
      self.export_btn.grid   (row = 3, column = 0, sticky = 'NE', **pad('SEW'))

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def serialize(self):
      return {
         'Sampling rate [Hz]': self.sampling_rate.get(),
         'Time axis': self.time_axis.serialize(),
         'Frequency axis': self.frequency_axis.serialize(),
         'Amplitude axis': self.amplitude_axis.serialize()}

   def deserialize(self, input):
      self.sampling_rate.set(input['Sampling rate [Hz]'])
      self.time_axis.deserialize(input['Time axis'])
      self.frequency_axis.deserialize(input['Frequency axis'])
      self.amplitude_axis.deserialize(input['Amplitude axis'])
      # Keep in sync with the time axis.
      self.total_time.set(round(self.time_axis.convertTo(1.0)))

   def isPlaying(self):
      return self.playing

   def onSamplingRateChange(self, value):
      self.callback.onSoundChange()

   def onTotalTimeChange(self, value):
      # Keep in sync with the time entry.
      self.time_axis.set(value)
      self.callback.onSoundChange()

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
      self.wnd.title(PROGRAM_NAME)
      # Wave generator thread.
      self.wavegen_thread = wavegen.Thread()
      # Column frames.
      self.column_frames = [tk.Frame(self.wnd) for i in range(4)]
      # Wave list widget.
      self.wavelist_widget = WaveListWidget(self.column_frames[0], 1, MAX_WAVE_COUNT, self)
      # Waveform widget.
      self.waveform_widget = WaveformWidget(self.column_frames[2], self.onWaveformChange)
      # Zoom widget.
      self.zoom_widget = ZoomWidget(self.column_frames[3])
      # File widget.
      self.file_widget = FileWidget(self.column_frames[3], self)
      # Sound widget.
      self.sound_widget = SoundWidget(self.column_frames[3], self)
      # Frequency plot.
      self.frequency_plot = plot.Panel(self.column_frames[1],
         width       = 400,
         height      = 200,
         x_axis      = self.sound_widget.time_axis,
         y_axis      = self.sound_widget.frequency_axis,
         zoom_widget = self.zoom_widget,
         callback    = self.onSoundChange)
      # Amplitude plot.
      self.amplitude_plot = plot.Panel(self.column_frames[1],
         width       = 400,
         height      = 200,
         x_axis      = self.sound_widget.time_axis,
         y_axis      = self.sound_widget.amplitude_axis,
         zoom_widget = self.zoom_widget,
         callback    = self.onSoundChange)
      # Keep zoom level of the X axis on both plots in sync.
      self.frequency_plot.registerViewChangeCallback(
         lambda x_range, y_range: self.amplitude_plot.setView(x_range, None))
      self.amplitude_plot.registerViewChangeCallback(
         lambda x_range, y_range: self.frequency_plot.setView(x_range, None))
      # Configure grid.
      self.configureGrid()
      # Stored waves.
      self.default_wave = self.serializeCurrentWave()
      self.wave_list = [self.default_wave]
      self.wave_index = 0
      # TODO: Add some kind of marker to indicate whether played sound is up-to-date.
      # TODO: Undo/redo.

   def configureGrid(self):
      # Only column #2 (containing plots) gets wider on resize.
      self.wnd.columnconfigure(0, weight = 0)
      self.wnd.columnconfigure(1, weight = 1)
      self.wnd.columnconfigure(2, weight = 0)
      self.wnd.columnconfigure(3, weight = 0)
      self.wnd.rowconfigure   (0, weight = 1)
      # Column frames.
      self.column_frames[0].grid(column = 0, row = 0, sticky = 'NSW')
      self.column_frames[1].grid(column = 1, row = 0, sticky = 'NSEW')
      self.column_frames[2].grid(column = 2, row = 0, sticky = 'NSE')
      self.column_frames[3].grid(column = 3, row = 0, sticky = 'NSE')
      # Column #1.
      self.column_frames[0].rowconfigure   (0, weight = 1)
      # Column #2.
      self.column_frames[1].columnconfigure(0, weight = 1)
      self.column_frames[1].rowconfigure   (0, weight = 1)
      self.column_frames[1].rowconfigure   (1, weight = 1)
      # Column #3.
      self.column_frames[2].columnconfigure(0, weight = 1)
      # Column #4.
      self.column_frames[3].columnconfigure(0, weight = 1)
      # Column #1 widgets.
      self.wavelist_widget.grid(column = 0, row = 0, sticky = 'NSEW', **pad('SEW'))
      # Column #2 widgets.
      self.frequency_plot.grid (column = 0, row = 0, sticky = 'NSEW')
      self.amplitude_plot.grid (column = 0, row = 1, sticky = 'NSEW')
      # Column #3 widgets.
      self.waveform_widget.grid(column = 0, row = 0, sticky = 'NEW', **pad('SEW'))
      # Column #4 widgets.
      self.zoom_widget.grid    (column = 0, row = 0, sticky = 'NSEW', **pad('SE'))
      self.file_widget.grid    (column = 1, row = 0, sticky = 'NSEW', **pad('SE'))
      self.sound_widget.grid   (column = 0, row = 1, columnspan = 2, sticky = 'NEW', **pad('SE'))

   def serializeCurrentWave(self):
      return {
         'Frequency': self.frequency_plot.serialize(),
         'Amplitude': self.amplitude_plot.serialize(),
         'Waveform': self.waveform_widget.serialize()}

   def deserializeCurrentWave(self, input_wave):
      self.frequency_plot.deserialize(input_wave['Frequency'])
      self.amplitude_plot.deserialize(input_wave['Amplitude'])
      self.waveform_widget.deserialize(input_wave['Waveform'])
      self.configurePlots()

   def serialize(self):
      self.wave_list[self.wave_index] = self.serializeCurrentWave()
      return {
         'Waves': self.wave_list[:],
         'Sound': self.sound_widget.serialize()}

   def deserialize(self, input):
      self.sound_widget.deserialize(input['Sound'])
      self.wavelist_widget.setCount(len(input['Waves']))
      self.wave_list = input['Waves']
      self.wave_index = 0
      self.deserializeCurrentWave(self.wave_list[self.wave_index])

   def configurePlots(self):
      if self.waveform_widget.serialize()['Type'] == 'Noise':
         self.frequency_plot.configure(state = 'disabled')
      else:
         self.frequency_plot.configure(state = 'normal')

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

   def onWaveformChange(self):
      self.configurePlots()
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

   def onOpen(self):
      path = tkfiledialog.askopenfilename(
         title = 'Open',
         defaultextension = '.json',
         filetypes = (('{} format (*.json)'.format(PROGRAM_NAME), '.json'),))
      if path:
         with open(path, 'r') as f:
            self.deserialize(json.load(f))
         self.onSoundChange()

   def onSave(self):
      path = tkfiledialog.asksaveasfilename(
         title = 'Save',
         defaultextension = '.json',
         filetypes = (('{} format (*.json)'.format(PROGRAM_NAME), '.json'),))
      if path:
         # TODO: Strip redundant elements on save (frequency and phase for noise).
         with open(path, 'w') as f:
            json.dump(self.serialize(), f)

   def run(self):
      self.wnd.mainloop()
      self.wavegen_thread.quit()
