
import tkinter as tk
import tkinter.ttk as ttk

COLOR_BACKGROUND    = '#ffffff'
COLOR_DEFAULT       = '#000000'
COLOR_GRID          = '#c0c0c0'
COLOR_HIGHLIGHT     = '#ff0000'
COLOR_CONTROL_POINT = '#00ff00'
COLOR_CURVE_POINT   = '#ffff00'

# "_PX" values specify number of pixels.
# "_REL" values specify fraction of the working area (excluding margins).

POINT_RADIUS_PX     = 5
X_MARGIN_PX         = 40
Y_MARGIN_REL        = 0.25
GRID_MIN_STEP_PX    = 15
GRID_TEXT_OFFSET_PX = 5

SPAWN_MIN_DIST_REL  = 0.02
ZOOM_MULTIPLIER     = 1.2
ZOOM_MAX            = 100.0

#===============================================================================
class Grid:

   def __init__(self, plot):
      self.plot = plot
      self.lines = []
      self.texts = []

   def drawLineItems(self, line_items):
      for ix in range(len(line_items)):
         # Create a new line object if necessary.
         if len(self.lines) <= ix:
            self.lines.append(self.plot.canvas.create_line(0,0,0,0, fill = COLOR_GRID))
         # Set coordinates and move to the bottom.
         self.plot.canvas.coords(self.lines[ix], *line_items[ix])
         self.plot.canvas.tag_lower(self.lines[ix])
      # Delete redundant line objects.
      while len(self.lines) > len(line_items):
         self.plot.canvas.delete(self.lines.pop())

   def drawTextItems(self, text_items):
      for ix in range(len(text_items)):
         px,py,anchr,txt = text_items[ix]
         # Create a new text object if necessary.
         if len(self.texts) <= ix:
            self.texts.append(self.plot.canvas.create_text(0,0, fill = COLOR_GRID))
         # Set coordinates, anchor, text, and move to the bottom.
         self.plot.canvas.coords(self.texts[ix], px, py)
         self.plot.canvas.itemconfig(self.texts[ix], anchor = anchr, text = txt)
         self.plot.canvas.tag_lower(self.texts[ix])
      # Delete redundant text objects.
      while len(self.texts) > len(text_items):
         self.plot.canvas.delete(self.texts.pop())

   def determinePrecision(self, delta):
      fract_digits = 0
      while delta < 1.0:
         delta *= 10.0
         fract_digits += 1
      return fract_digits

   def value2string(self, value, fract_digits):
      return '{:.{precision}f}'.format(value, precision = fract_digits)

   def draw(self):
      line_items = []
      text_items = []
      # Determine the number of positions to display on X and Y axes
      # based on lengths (in pixels) of those axes.
      horiz_count = max(self.plot.getPixelWidth()  // GRID_MIN_STEP_PX, 3)
      vert_count  = max(self.plot.getPixelHeight() // GRID_MIN_STEP_PX, 3)
      # Always use odd numbers of positions to have a center line.
      if (horiz_count % 2) == 0:
         horiz_count -= 1
      if (vert_count % 2) == 0:
         vert_count -= 1
      # Get X and Y axes.
      x_axis = self.plot.getXaxis()
      y_axis = self.plot.getYaxis()
      # Get ranges for coordinates on X and Y axes.
      x0,x1 = self.plot.getXcoordsRange()
      y0,y1 = self.plot.getYcoordsRange()
      # Calculate coordinates for all positions on X and Y axes.
      x_coords = [x0 + (x1-x0) * (i/(horiz_count-1)) for i in range(horiz_count)]
      y_coords = [y0 + (y1-y0) * (i/(vert_count-1))  for i in range(vert_count)]
      # Create line items for all horizontal and vertical lines of the grid.
      line_items += [self.plot.coords2pixels(x,y0) + self.plot.coords2pixels(x,y1) for x in x_coords]
      line_items += [self.plot.coords2pixels(x0,y) + self.plot.coords2pixels(x1,y) for y in y_coords]
      # Create text item for unit of the X axis.
      if x_axis.getUnit() is not None:
         px1,py0 = self.plot.coords2pixels(x1,y0)
         item = (px1+GRID_TEXT_OFFSET_PX, py0, 'sw', x_axis.getUnit())
         text_items.append(item)
      # Create text item for unit of the Y axis.
      if y_axis.getUnit() is not None:
         px0,py1 = self.plot.coords2pixels(x0,y1)
         item = (px0, py1-GRID_TEXT_OFFSET_PX, 'sw', y_axis.getUnit())
         text_items.append(item)
      # Calculate values for all positions on X and Y axes.
      x_values = [x_axis.convertTo(x) for x in x_coords]
      y_values = [y_axis.convertTo(y) for y in y_coords]
      # Determine representation precision based on differences between consecutive values.
      x_prec = self.determinePrecision(x_values[1] - x_values[0])
      y_prec = self.determinePrecision(y_values[1] - y_values[0])
      # Determine how many positions to skip on the X axis
      # based on the length of string representing the second to last value.
      x_mod = (len(self.value2string(x_values[-2], x_prec)) + 4) // 3
      # Create text items for values on the X axis.
      for ix in range(len(x_coords)):
         if (ix % x_mod) == 0:
            px,py = self.plot.coords2pixels(x_coords[ix], y0)
            item = (px, py+GRID_TEXT_OFFSET_PX, 'n', self.value2string(x_values[ix], x_prec))
            text_items.append(item)
      # Create text items for values on the Y axis.
      for ix in range(len(y_coords)):
         px,py = self.plot.coords2pixels(x0, y_coords[ix])
         item = (px-GRID_TEXT_OFFSET_PX, py, 'e', self.value2string(y_values[ix], y_prec))
         text_items.append(item)
      # Draw the prepared line and text items.
      self.drawLineItems(line_items)
      self.drawTextItems(text_items)

#===============================================================================
class Point:

   def __init__(self, plot, color):
      self.plot = plot
      self.oval_id = plot.canvas.create_oval(0,0,0,0, fill = color, outline = COLOR_DEFAULT)
      plot.canvas.tag_bind(self.oval_id, '<Enter>', lambda evt: plot.selectPoint(self))
      plot.canvas.tag_bind(self.oval_id, '<Leave>', lambda evt: plot.deselectPoint())

   def delete(self):
      self.plot.canvas.delete(self.oval_id)

   def setHighlight(self, value):
      self.plot.canvas.itemconfig(self.oval_id, outline = (COLOR_HIGHLIGHT if value else COLOR_DEFAULT))

   def refreshPosition(self):
      px,py = self.plot.coords2pixels(self.x, self.y)
      self.plot.canvas.coords(
         self.oval_id,
         px - POINT_RADIUS_PX,
         py - POINT_RADIUS_PX,
         px + POINT_RADIUS_PX,
         py + POINT_RADIUS_PX)

   def serialize(self):
      return (self.x, self.y)

   def deserialize(self, input):
      self.x = input[0]
      self.y = input[1]
      self.refreshPosition()

#===============================================================================
class ControlPoint(Point):

   def __init__(self, plot):
      super().__init__(plot, COLOR_CONTROL_POINT)

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
         self.left = CurvePoint(self.plot)
         self.left.spawn(self, self.x-SPAWN_MIN_DIST_REL, self.y)
      if next is not None:
         next.prev = self
         self.right = CurvePoint(self.plot)
         self.right.spawn(self, self.x+SPAWN_MIN_DIST_REL, self.y)
      super().refreshPosition()

   def delete(self):
      if self.prev is not None:
         self.prev.next = self.next
      if self.next is not None:
         self.next.prev = self.prev
      if self.left is not None:
         self.left.delete()
      if self.right is not None:
         self.right.delete()
      super().delete()
      self.prev = None
      self.next = None
      self.left = None
      self.right = None

   def moveTo(self, x, y):
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
         self.left.moveTo(self.left.x + dx, self.left.y + dy)
      if self.right is not None:
         self.right.moveTo(self.right.x + dx, self.right.y + dy)
      super().refreshPosition()

   def serialize(self):
      return (
         self.left.serialize() if (self.left is not None) else None,
         super().serialize(),
         self.right.serialize() if (self.right is not None) else None)

   def deserialize(self, input):
      if self.left is not None:
         self.left.deserialize(input[0])
      super().deserialize(input[1])
      if self.right is not None:
         self.right.deserialize(input[2])

#===============================================================================
class CurvePoint(Point):

   def __init__(self, plot):
      super().__init__(plot, COLOR_CURVE_POINT)

   def limitCoords(self, x, y):
      x = min(max(x, 0.0), 1.0)
      y = min(max(y, -Y_MARGIN_REL), 1.0+Y_MARGIN_REL)
      return (x,y)

   def spawn(self, parent, x, y):
      self.x, self.y = self.limitCoords(x,y)
      self.parent = parent
      self.refreshPosition()

   def moveTo(self, x, y):
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
class Panel:

   def __init__(self, tk_parent, width, height, x_axis, y_axis, callback):
      self.width  = width
      self.height = height
      self.x_axis = x_axis
      self.y_axis = y_axis
      self.on_curve_change = callback
      self.on_view_change = None
      self.mouse_pos = None
      # Parameters to allow zooming.
      self.x_range = [0.0, 1.0]
      self.y_range = [0.0, 1.0]
      self.zoom_mode = 'X'
      # Frame.
      self.frame = ttk.Frame(tk_parent)
      self.frame.columnconfigure(0, weight = 1)
      self.frame.rowconfigure(0, weight = 1)
      # Canvas.
      self.canvas = tk.Canvas(self.frame, width = width, height = height, background = COLOR_BACKGROUND)
      self.canvas.grid(sticky = 'NSEW')
      self.canvas.bind('<Configure>', self.onResize)
      self.canvas.bind('<Button-3>', self.onMouse3Press)
      self.canvas.bind('<Button-1>', self.onMouse1Press)
      self.canvas.bind('<ButtonRelease-1>', self.onMouse1Release)
      self.canvas.bind('<B1-Motion>', self.onMouse1Motion)
      self.canvas.bind('<MouseWheel>', self.onMouseWheel)
      # Control points.
      head = ControlPoint(self)
      tail = ControlPoint(self)
      head.spawn(None, tail, 0.0, 0.5)
      tail.spawn(head, None, 1.0, 0.5)
      self.control_points = head
      self.selected_point = None
      self.grabbed_point = None
      # Curve lines.
      self.curve_lines = []
      self.drawCurveLines()
      # Grid.
      self.plot_grid = Grid(self)
      self.plot_grid.draw()
      # Callbacks to update grid.
      self.x_axis.registerCallback(self.plot_grid.draw)
      self.y_axis.registerCallback(self.plot_grid.draw)
      # Context menu.
      self.createMenu(tk_parent)

   #----------------------------------------------------------------------------

   def getPixelWidth(self):
      return (self.width - 2*X_MARGIN_PX)

   def getPixelHeight(self):
      return round(self.height / (1.0 + 2.0*Y_MARGIN_REL))

   def getXcoordsRange(self):
      return tuple(self.x_range)

   def getYcoordsRange(self):
      return tuple(self.y_range)

   def coords2pixels(self, x, y):
      # X/Y axis: From x/y_range to [0,1].
      x = (x - self.x_range[0]) / (self.x_range[1] - self.x_range[0])
      y = (y - self.y_range[0]) / (self.y_range[1] - self.y_range[0])
      # X axis: From [0,1] to pixels.
      px = round(x * (self.width - 2*X_MARGIN_PX) + X_MARGIN_PX)
      # Y axis: From [0,1] to pixels.
      py = round((1.0 - (y + Y_MARGIN_REL) / (1.0 + 2.0*Y_MARGIN_REL)) * self.height)
      return (px,py)

   def pixels2coords(self, px, py):
      # X axis: From pixels to [0,1].
      x = (px - X_MARGIN_PX) / (self.width - 2*X_MARGIN_PX)
      # Y axis: From pixels to [0,1].
      y = (1.0 - (py / self.height)) * (1.0 + 2.0*Y_MARGIN_REL) - Y_MARGIN_REL
      # X/Y axis: From [0,1] to x/y_range.
      x = x * (self.x_range[1] - self.x_range[0]) + self.x_range[0]
      y = y * (self.y_range[1] - self.y_range[0]) + self.y_range[0]
      return (x,y)

   def calculateViewZoom(self, coord, range, multiplier):
      new_range = range[:]
      new_zoom = multiplier / (new_range[1] - new_range[0])
      if new_zoom <= ZOOM_MAX:
         # Clip coordinate to the currently visible range.
         coord = min(max(coord, new_range[0]), new_range[1])
         # Zoom in if multiplier > 1, zoom out if multiplier < 1.
         new_range[0] += (coord - new_range[0]) * (1.0 - 1.0 / multiplier)
         new_range[1] -= (new_range[1] - coord) * (1.0 - 1.0 / multiplier)
         # This only applies to zoom out.
         d = new_range[1] - new_range[0]
         if d > 1.0:
            new_range = (0.0, 1.0)
         elif new_range[0] < 0.0:
            new_range = (0.0, d)
         elif new_range[1] > 1.0:
            new_range = (1.0-d, 1.0)
      return new_range

   def calculateViewMove(self, coord_change, range):
      new_range = range[:]
      new_range[0] -= coord_change
      new_range[1] -= coord_change
      d = new_range[1] - new_range[0]
      if new_range[0] < 0.0:
         new_range = (0.0, d)
      if new_range[1] > 1.0:
         new_range = (1.0-d, 1.0)
      return new_range

   #----------------------------------------------------------------------------

   def createMenu(self, tk_parent):
      self.cmd_coords = None
      self.cmd_point = None
      self.cmd_menu = tk.Menu(tk_parent, tearoff = 0)
      self.cmd_menu.add_command(
         label = 'Add point',
         command = lambda: self.addControlPoint(*self.cmd_coords))
      self.cmd_menu.add_command(
         label = 'Delete point',
         command = lambda: self.deleteControlPoint(self.cmd_point))

   def showMenu(self, event, point):
      self.cmd_coords = self.pixels2coords(event.x, event.y)
      self.cmd_point = point
      # Enable the option to add a point when clicking on an empty space.
      self.cmd_menu.entryconfig(0,
         state = 'normal' if (point is None) else 'disabled')
      # Enable the option to delete a point when clicking on a deletable point.
      self.cmd_menu.entryconfig(1,
         state = 'normal' if self.isDeletable(point) else 'disabled')
      # Show context menu.
      self.cmd_menu.post(event.x_root, event.y_root)

   #----------------------------------------------------------------------------

   def onResize(self, event):
      self.width = event.width
      self.height = event.height
      self.refreshPositions()

   def onMouse3Press(self, event):
      self.showMenu(event, self.selected_point)

   def onMouse1Press(self, event):
      self.grabPoint(self.selected_point)
      self.mouse_pos = (event.x, event.y)

   def onMouse1Release(self, event):
      if self.grabbed_point is not None:
         self.on_curve_change()
      self.ungrabPoint()

   def onMouse1Motion(self, event):
      if self.grabbed_point is not None:
         self.grabbed_point.moveTo(*self.pixels2coords(event.x, event.y))
         self.drawCurveLines()
      else:
         x0,y0 = self.pixels2coords(self.mouse_pos[0], self.mouse_pos[1])
         x1,y1 = self.pixels2coords(event.x, event.y)
         x_range = self.calculateViewMove(x1 - x0, self.x_range)
         y_range = self.calculateViewMove(y1 - y0, self.y_range)
         # Update view, and notify of the change.
         self.setView(x_range, y_range)
         self.on_view_change(x_range, y_range)
      # Update saved maouse position.
      self.mouse_pos = (event.x, event.y)

   def onMouseWheel(self, event):
      x,y = self.pixels2coords(event.x, event.y)
      if event.delta > 0:
         multiplier = ZOOM_MULTIPLIER
      else:
         multiplier = 1.0 / ZOOM_MULTIPLIER
      # Calculate zoom.
      x_range = self.x_range
      y_range = self.y_range
      if 'X' in self.zoom_mode:
         x_range = self.calculateViewZoom(x, x_range, multiplier)
      if 'Y' in self.zoom_mode:
         y_range = self.calculateViewZoom(y, y_range, multiplier)
      # Update view, and notify of the change.
      self.setView(x_range, y_range)
      self.on_view_change(x_range, y_range)

   #----------------------------------------------------------------------------

   def selectPoint(self, point):
      if point is not None:
         point.setHighlight(True)
      self.selected_point = point

   def deselectPoint(self):
      if (self.selected_point is not None) and (self.grabbed_point is None):
         self.selected_point.setHighlight(False)
      self.selected_point = None

   def grabPoint(self, point):
      self.grabbed_point = point

   def ungrabPoint(self):
      if (self.grabbed_point is not None) and (self.selected_point is None):
         self.grabbed_point.setHighlight(False)
      self.grabbed_point = None

   #----------------------------------------------------------------------------

   def addControlPoint(self, x, y):
      new_point = ControlPoint(self)
      cur_point = self.control_points
      # Note that there are always at least two control points in the list.
      while True:
         cur_point = cur_point.next
         if (x < cur_point.x) or (cur_point.next is None):
            new_point.spawn(cur_point.prev, cur_point, x, y)
            break
      # Re-draw curve, and notify of the change.
      self.drawCurveLines()
      self.on_curve_change()

   def deleteControlPoint(self, point):
      point.delete()
      self.on_curve_change()
      self.drawCurveLines()

   def isDeletable(self, point_to_check):
      cur_point = self.control_points
      # Note that there are always at least two control points in the list.
      while True:
         cur_point = cur_point.next
         if cur_point.next is None:
            return False
         if cur_point is point_to_check:
            return True

   #----------------------------------------------------------------------------

   def drawCurveLines(self):
      curve = self.serialize()
      for ix in range(len(curve)-1):
         px1,py1 = self.coords2pixels(*curve[ix][1])
         px2,py2 = self.coords2pixels(*curve[ix][2])
         px3,py3 = self.coords2pixels(*curve[ix+1][0])
         px4,py4 = self.coords2pixels(*curve[ix+1][1])
         # Create a new line object if necessary.
         if len(self.curve_lines) <= ix:
            self.curve_lines.append(self.canvas.create_line(0,0,0,0, smooth = 'bezier', fill = COLOR_DEFAULT))
         # Setup coordinates.
         self.canvas.coords(self.curve_lines[ix], px1, py1, px2, py2, px3, py3, px4, py4)
         # Move curve lines below all points but above grid.
         self.canvas.tag_lower(self.curve_lines[ix], self.control_points.oval_id)
      # Remove redundant line objects.
      while len(self.curve_lines) > len(curve)-1:
         self.canvas.delete(self.curve_lines.pop())

   def refreshPositions(self):
      self.plot_grid.draw()
      self.drawCurveLines()
      point = self.control_points
      while point is not None:
         point.refreshPosition()
         point = point.next

   #----------------------------------------------------------------------------

   def grid(self, **kwargs):
      self.frame.grid(**kwargs)

   def registerViewChangeCallback(self, callback):
      self.on_view_change = callback

   def setView(self, x_range, y_range):
      if x_range is not None:
         self.x_range = list(x_range)
      if y_range is not None:
         self.y_range = list(y_range)
      self.refreshPositions()

   def getXaxis(self):
      return self.x_axis

   def getYaxis(self):
      return self.y_axis

   def serialize(self):
      out = []
      pt = self.control_points
      while pt is not None:
         out.append(pt.serialize())
         pt = pt.next
      return tuple(out)

   def deserialize(self, input):
      cur_point = self.control_points
      # Deserialize all points except the last one (which needs to remain last).
      for item in input[:-1]:
         # This is the last existing point, we need to add a new one before it.
         if cur_point.next is None:
            new_point = ControlPoint(self)
            new_point.spawn(cur_point.prev, cur_point, 0, 0)
            new_point.deserialize(item)
         else:
            cur_point.deserialize(item)
            cur_point = cur_point.next
      # Remove redundant existing points.
      while cur_point.next is not None:
         cur_point = cur_point.next
         cur_point.prev.delete()
      # Deserialize the last point.
      cur_point.deserialize(input[-1])
      # Re-draw curve.
      self.drawCurveLines()
