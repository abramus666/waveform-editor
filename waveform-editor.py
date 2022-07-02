
import ctypes, math, threading, winsound

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkfiledialog

COLOR_BACKGROUND = '#ffffff'
COLOR_DEFAULT    = '#000000'
COLOR_GRID       = '#c0c0c0'
COLOR_HIGHLIGHT  = '#ff0000'
COLOR_CONTROL_PT = '#00ff00'
COLOR_CURVE_PT   = '#ffff00'

POINT_RADIUS_PX  = 5
SPAWN_DIST_REL   = 0.02
X_MARGIN_PX      = 40
Y_MARGIN_REL     = 0.25
MAX_GRID_DIST_PX = 25
TEXT_OFFSET_PX   = 5
POINTS_PER_CURVE = 100

#===============================================================================
class PlotGrid:

   def __init__(self, panel):
      self.panel = panel
      self.lines = []
      self.texts = []

   def calculateLines(self, p0, p1):
      step = p1 - p0
      cnt = 1
      while abs(step) > MAX_GRID_DIST_PX:
         step /= 2.0
         cnt *= 2
      return [round(p0 + i*step) for i in range(cnt)] + [p1]

   def draw(self):
      px0,py0 = self.panel.coords2pixels(0.0, 0.0)
      px1,py1 = self.panel.coords2pixels(1.0, 1.0)

      horiz_pixels = self.calculateLines(px0,px1)
      vert_pixels  = self.calculateLines(py0,py1)

      line_items = []
      line_items += [(px,py0,px,py1) for px in horiz_pixels]
      line_items += [(px0,py,px1,py) for py in vert_pixels]

      for ix in range(len(line_items)):
         if len(self.lines) <= ix:
            self.lines.append(self.panel.canvas.create_line(0,0,0,0, fill = COLOR_GRID))
         self.panel.canvas.coords(self.lines[ix], *line_items[ix])
         self.panel.canvas.tag_lower(self.lines[ix])
      while len(self.lines) > len(line_items):
         self.panel.canvas.delete(self.lines.pop())

      text_items = [
         (px1+TEXT_OFFSET_PX, py0, 'sw', self.panel.getXaxisUnit()),
         (px0, py1-TEXT_OFFSET_PX, 'sw', self.panel.getYaxisUnit())]

      convertToXaxisUnit = self.panel.createFuncToConvertToXaxisUnit()
      convertToYaxisUnit = self.panel.createFuncToConvertToYaxisUnit()

      for ix,px in enumerate(horiz_pixels):
         if ((ix % 2) == 0) or (ix == len(horiz_pixels)-1):
            value = convertToXaxisUnit(ix/(len(horiz_pixels)-1))
            item = (px, py0+TEXT_OFFSET_PX, 'n', str(round(value)))
            text_items.append(item)

      for ix,py in enumerate(vert_pixels):
         value = convertToYaxisUnit(ix/(len(vert_pixels)-1))
         item = (px0-TEXT_OFFSET_PX, py, 'e', str(round(value)))
         text_items.append(item)

      for ix in range(len(text_items)):
         px,py,anchr,txt = text_items[ix]
         if len(self.texts) <= ix:
            self.texts.append(self.panel.canvas.create_text(0,0, fill = COLOR_GRID))
         self.panel.canvas.coords(self.texts[ix], px, py)
         self.panel.canvas.itemconfig(self.texts[ix], anchor = anchr, text = txt)
         self.panel.canvas.tag_lower(self.texts[ix])
      while len(self.texts) > len(text_items):
         self.panel.canvas.delete(self.texts.pop())

#===============================================================================
class PlotPoint:

   def __init__(self, panel, color):
      self.panel = panel
      self.oval_id = panel.canvas.create_oval(0,0,0,0, fill = color, outline = COLOR_DEFAULT)
      panel.canvas.tag_bind(self.oval_id, '<Enter>',    lambda evt: panel.selectCurvePoint(self))
      panel.canvas.tag_bind(self.oval_id, '<Leave>',    lambda evt: panel.deselectCurvePoint())
      panel.canvas.tag_bind(self.oval_id, '<Button-1>', lambda evt: panel.lockCurvePoint(self))

   def setHighlight(self, value):
      self.panel.canvas.itemconfig(self.oval_id, outline = (COLOR_HIGHLIGHT if value else COLOR_DEFAULT))

   def refreshPosition(self):
      px,py = self.panel.coords2pixels(self.x, self.y)
      self.panel.canvas.coords(
         self.oval_id,
         px - POINT_RADIUS_PX,
         py - POINT_RADIUS_PX,
         px + POINT_RADIUS_PX,
         py + POINT_RADIUS_PX)

#===============================================================================
class PlotControlPoint(PlotPoint):

   def __init__(self, panel):
      super().__init__(panel, COLOR_CONTROL_PT)

   def limitCoords(self, x, y):
      x = min(max(x, 0.0), 1.0)
      y = min(max(y, 0.0), 1.0)
      return (x,y)

   def refreshPosition(self):
      if self.left is not None:
         self.left.refreshPosition()
      if self.right is not None:
         self.right.refreshPosition()
      super().refreshPosition()

   def spawn(self, prev, next, x, y):
      self.x, self.y = self.limitCoords(x,y)
      self.prev = prev
      self.next = next
      self.left = None
      self.right = None
      if prev is not None:
         prev.next = self
         self.left = PlotCurvePoint(self.panel)
         self.left.spawn(self, self.x-SPAWN_DIST_REL, self.y)
      if next is not None:
         next.prev = self
         self.right = PlotCurvePoint(self.panel)
         self.right.spawn(self, self.x+SPAWN_DIST_REL, self.y)
      super().refreshPosition()

   def move(self, x, y):
      x,y = self.limitCoords(x,y)
      # First and last control points can only be moved along the Y axis.
      if (self.prev is None) or (self.next is None):
         x = self.x
      # Other control points are limited in the X axis to their neighbors.
      else:
         x = min(max(x, self.prev.x), self.next.x)
      dx = x - self.x
      dy = y - self.y
      self.x = x
      self.y = y
      if self.left is not None:
         self.left.move(self.left.x + dx, self.left.y + dy)
      if self.right is not None:
         self.right.move(self.right.x + dx, self.right.y + dy)
      super().refreshPosition()

#===============================================================================
class PlotCurvePoint(PlotPoint):

   def __init__(self, panel):
      super().__init__(panel, COLOR_CURVE_PT)

   def limitCoords(self, x, y):
      x = min(max(x, 0.0), 1.0)
      y = min(max(y, -Y_MARGIN_REL), 1.0+Y_MARGIN_REL)
      return (x,y)

   def spawn(self, parent, x, y):
      self.x, self.y = self.limitCoords(x,y)
      self.parent = parent
      self.refreshPosition()

   def move(self, x, y):
      x,y = self.limitCoords(x,y)
      # Curve points cannot cross the X value of their control point.
      if self is self.parent.left:
         x = min(x, self.parent.x)
      else:
         x = max(x, self.parent.x)
      self.x = x
      self.y = y
      self.refreshPosition()

#===============================================================================
class PlotPanel:

   def __init__(self, parent, row, column, width, height):
      self.parent = parent
      self.width = width
      self.height = height
      # Frame.
      self.frame = ttk.Frame(parent.wnd)
      self.frame.grid(row = row, column = column, sticky = 'NSEW')
      self.frame.columnconfigure(0, weight = 1)
      self.frame.rowconfigure(0, weight = 1)
      # Canvas.
      self.canvas = tk.Canvas(self.frame, width = width, height = height, background = COLOR_BACKGROUND)
      self.canvas.grid(sticky = 'NSEW')
      self.canvas.bind('<Configure>', self.onResize)
      self.canvas.bind('<Button-1>', self.onMousePress)
      self.canvas.bind('<ButtonRelease-1>', self.onMouseRelease)
      self.canvas.bind('<B1-Motion>', self.onMouseMotion)
      # Control points.
      head = PlotControlPoint(self)
      tail = PlotControlPoint(self)
      head.spawn(None, tail, 0.0, 0.5)
      tail.spawn(head, None, 1.0, 0.5)
      self.control_points = head
      self.select_point = None
      self.locked_point = None
      # Curve lines.
      self.curve_lines = []
      self.drawCurveLines()
      # Grid.
      self.setupXaxis()
      self.setupYaxis()
      self.grid = PlotGrid(self)
      self.grid.draw()

   #----------------------------------------------------------------------------

   def coords2pixels(self, x, y):
      px = round(x * (self.width - 2*X_MARGIN_PX) + X_MARGIN_PX)
      py = round((1.0 - (y + Y_MARGIN_REL) / (1.0 + 2.0*Y_MARGIN_REL)) * self.height)
      return (px,py)

   def pixels2coords(self, px, py):
      x = (px - X_MARGIN_PX) / (self.width - 2*X_MARGIN_PX)
      y = (1.0 - (py / self.height)) * (1.0 + 2.0*Y_MARGIN_REL) - Y_MARGIN_REL
      return (x,y)

   #----------------------------------------------------------------------------

   def onResize(self, event):
      self.width = event.width
      self.height = event.height
      self.grid.draw()
      self.drawCurveLines()
      point = self.control_points
      while point is not None:
         point.refreshPosition()
         point = point.next

   def onMousePress(self, event):
      if (self.select_point is None) and (self.locked_point is None):
         self.addCurvePoint(*self.pixels2coords(event.x, event.y))
         self.parent.onCurveChange()
         self.drawCurveLines()

   def onMouseRelease(self, event):
      if self.locked_point is not None:
         self.parent.onCurveChange()
      self.unlockCurvePoint()

   def onMouseMotion(self, event):
      if self.locked_point is not None:
         self.locked_point.move(*self.pixels2coords(event.x, event.y))
         self.drawCurveLines()

   #----------------------------------------------------------------------------

   def addCurvePoint(self, x, y):
      new_point = PlotControlPoint(self)
      cur_point = self.control_points
      # Note that there are always at least two control points in the list.
      while True:
         cur_point = cur_point.next
         if (x < cur_point.x) or (cur_point.next is None):
            new_point.spawn(cur_point.prev, cur_point, x, y)
            break

   def selectCurvePoint(self, point):
      if point is not None:
         point.setHighlight(True)
      self.select_point = point

   def deselectCurvePoint(self):
      if (self.select_point is not None) and (self.locked_point is None):
         self.select_point.setHighlight(False)
      self.select_point = None

   def lockCurvePoint(self, point):
      self.locked_point = point

   def unlockCurvePoint(self):
      if (self.locked_point is not None) and (self.select_point is None):
         self.locked_point.setHighlight(False)
      self.locked_point = None

   #----------------------------------------------------------------------------

   def drawCurveLines(self):
      ix = 0
      for pt1,pt2,pt3,pt4 in self.getCurves():
         px1,py1 = self.coords2pixels(pt1.x, pt1.y)
         px2,py2 = self.coords2pixels(pt2.x, pt2.y)
         px3,py3 = self.coords2pixels(pt3.x, pt3.y)
         px4,py4 = self.coords2pixels(pt4.x, pt4.y)
         # Create a new line object if necessary.
         if len(self.curve_lines) <= ix:
            self.curve_lines.append(self.canvas.create_line(0,0,0,0, smooth = 'bezier', fill = COLOR_DEFAULT))
         # Setup coordinates.
         self.canvas.coords(self.curve_lines[ix], px1, py1, px2, py2, px3, py3, px4, py4)
         # Move curve lines below all points but above grid.
         self.canvas.tag_lower(self.curve_lines[ix], self.control_points.oval_id)
         ix += 1
      # Remove redundant line objects.
      while len(self.curve_lines) > ix:
         self.canvas.delete(self.curve_lines.pop())

   #----------------------------------------------------------------------------

   def getCurves(self):
      pt1 = self.control_points
      while pt1.next is not None:
         pt2 = pt1.right
         pt3 = pt1.next.left
         pt4 = pt1.next
         yield (pt1, pt2, pt3, pt4)
         pt1 = pt4

   def setupXaxis(self, total_time_ms = 1000):
      self.total_time_ms = total_time_ms

   def getXaxisUnit(self):
      return '[ms]'

   # Convert from X axis unit (time in milliseconds) to range [0,1].
   def createFuncToConvertFromXaxisUnit(self):
      total_time_ms = self.total_time_ms
      return lambda t: (t / total_time_ms)

   # Convert from range [0,1] to X axis unit (time in milliseconds).
   def createFuncToConvertToXaxisUnit(self):
      total_time_ms = self.total_time_ms
      return lambda x: (x * total_time_ms)

#===============================================================================
class FrequencyPlotPanel(PlotPanel):

   def setupYaxis(self, min_freq_hz = 50, max_freq_hz = 12000):
      self.min_freq_hz = min_freq_hz
      self.max_freq_hz = max_freq_hz

   def getYaxisUnit(self):
      return '[Hz]'

   # Convert from range [0,1] to Y axis unit (frequency in Hz).
   def createFuncToConvertToYaxisUnit(self):
      min_freq_hz = self.min_freq_hz
      max_freq_hz = self.max_freq_hz
      return lambda y: (10.0**((1.0 - y) * math.log10(min_freq_hz / max_freq_hz)) * max_freq_hz)

#===============================================================================
class AmplitudePlotPanel(PlotPanel):

   def setupYaxis(self, amplitude_range_db = 50):
      self.amplitude_range_db = amplitude_range_db

   def getYaxisUnit(self):
      return '[dB]'

   # Convert from range [0,1] to Y axis unit (amplitude in dB).
   def createFuncToConvertToYaxisUnit(self):
      amplitude_range_db = self.amplitude_range_db
      return lambda y: ((y - 1.0) * self.amplitude_range_db)

#===============================================================================
class Curve:

   def __init__(self, panel):
      self.curves = list(panel.getCurves())
      self.convertFromXaxisUnit = panel.createFuncToConvertFromXaxisUnit()
      self.convertToXaxisUnit = panel.createFuncToConvertToXaxisUnit()
      self.convertToYaxisUnit = panel.createFuncToConvertToYaxisUnit()

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

   def getMaxX(self):
      return self.convertToXaxisUnit(1.0)

   def getY(self, x):
      # Convert from X axis unit to range [0,1].
      x = self.convertFromXaxisUnit(x)
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
      return self.convertToYaxisUnit(y)

#===============================================================================
class Wave:

   def __init__(self, frequency_curve, amplitude_curve, sample_freq_hz):
      self.frequency_curve = frequency_curve
      self.amplitude_curve = amplitude_curve
      self.sample_freq_hz = round(sample_freq_hz)
      self.total_time_ms = frequency_curve.getMaxX()
      self.num_samples = round(sample_freq_hz * (self.total_time_ms / 1000.0))

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
      sine_wave_x = 0.0
      samples = [0.0 for i in range(self.num_samples)]
      for i in range(self.num_samples):
         # Calculate current time, frequency, and amplitude.
         t_ms = self.total_time_ms * (i / (self.num_samples - 1))
         frequency_hz = self.frequency_curve.getY(t_ms)
         amplitude_db = self.amplitude_curve.getY(t_ms)
         # Convert from dB to relative amplitude in range [0,1].
         # 20 dB change corresponds to a change in relative amplitude by a factor of 10.
         amplitude = 10.0**(amplitude_db / 20.0)
         # Calculate sine.
         sine_wave_y = math.sin(sine_wave_x)
         sine_wave_x += 2.0*math.pi * (frequency_hz / self.sample_freq_hz)
         if sine_wave_x >= 2.0*math.pi:
            sine_wave_x -= 2.0*math.pi
         # Scale sine value by amplitude.
         samples[i] = (sine_wave_y * amplitude)
      return samples

#===============================================================================
class WavGenCommPort:

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

def wavGenThread(input_port):
   PlaySound = ctypes.windll.winmm.PlaySound
   prep_wave = None
   while True:
      cmd = input_port.get()
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

#===============================================================================
if __name__ == '__main__':

   class Application:

      def __init__(self):
         self.wnd = tk.Tk()
         self.wnd.title('Waveform Editor')
         self.wnd.columnconfigure(0, weight = 1)
         self.wnd.columnconfigure(1, weight = 0)
         self.wnd.rowconfigure(0, weight = 1)
         self.wnd.rowconfigure(1, weight = 1)
         self.frequency_panel = FrequencyPlotPanel(self, 0, 0, 600, 300)
         self.amplitude_panel = AmplitudePlotPanel(self, 1, 0, 600, 300)
         # Toolbox frame.
         self.toolbox = ttk.Frame(self.wnd)
         self.toolbox.grid(row = 0, column = 1, rowspan = 2, sticky = 'N')
         self.toolbox.columnconfigure(0, weight = 0)
         self.toolbox.rowconfigure(0, weight = 0)
         self.toolbox.rowconfigure(1, weight = 0)
         # Play button.
         self.play = ttk.Button(self.toolbox, text = 'Play', command = self.onPlay)
         self.play.grid(row = 0, column = 0, sticky = 'N', padx = 5, pady = 5)
         self.playing = False
         # Save button.
         self.save = ttk.Button(self.toolbox, text = 'Save', command = self.onSave)
         self.save.grid(row = 1, column = 0, sticky = 'N', padx = 5, pady = (0,5))

         self.wavgen_port = WavGenCommPort()
         self.wavgen_thread = threading.Thread(target = wavGenThread, args = (self.wavgen_port,))
         self.wavgen_thread.start()

      def getWaveGenParams(self):
         return (Curve(self.frequency_panel), Curve(self.amplitude_panel), 44100)

      def onCurveChange(self):
         if self.playing:
            self.wavgen_port.set(('PLAY', self.getWaveGenParams()))

      def onPlay(self):
         if not self.playing:
            self.playing = True
            self.play.configure(text = 'Stop')
            self.wavgen_port.set(('PLAY', self.getWaveGenParams()))
         else:
            self.playing = False
            self.play.configure(text = 'Play')
            self.wavgen_port.set(('STOP',))

      def onSave(self):
         self.wavgen_port.set(('PREPARE', self.getWaveGenParams()))
         path = tkfiledialog.asksaveasfilename(
            title = 'Save',
            defaultextension = '.wav',
            filetypes = (('Waveform audio format (*.wav)', '.wav'),))
         if path:
            self.wavgen_port.set(('WRITE', path))
         else:
            self.wavgen_port.set(('DROP',))

      def run(self):
         self.wnd.mainloop()
         self.wavgen_port.set(('QUIT',))

   app = Application()
   app.run()
