import time
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.graphics import Color, Rectangle, StencilPush, StencilUse, StencilUnUse, StencilPop, Ellipse
from kivy.core.window import Window
from kivy.properties import ObjectProperty

RADIUS = 100
DELETION_LAG_SEC = 10
DISAPPEAR_MODE = "Disappear Mode"
PHOTO_MODE = "Photo Mode"

class RotatedCamera(Camera):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            PushMatrix()
            self.rotate_instruction = Rotate(origin=self.center)

        with self.canvas.after:
            PopMatrix()

        # Update the rotation origin when the widget's position or size changes
        self.bind(center=self.update_canvas_instructions)

    def update_canvas_instructions(self, *args):
        """
        Updates the origin of the canvas rotation.
        """
        self.rotate_instruction.origin = self.center

class CameraMaskApp(App):
    mode = DISAPPEAR_MODE
    def build(self):
        # The root widget will be a FloatLayout
        root = FloatLayout()

        # Add a Camera widget to the layout
        self.camera = RotatedCamera(
            play=True, resolution=(3000, 3000), size_hint=(1,1), index=1,
            allow_stretch=True, keep_ratio=False)
        root.add_widget(self.camera)

        # Create a MaskingWidget to sit on top of the camera
        self.mask_widget = MaskingWidget(app = self)
        root.add_widget(self.mask_widget)

        # Bind the mouse position for revealing the camera view
        Window.bind(mouse_pos=self.mask_widget.on_mouse_pos)

        Clock.schedule_interval(self.mask_widget.update_canvas, 1.0 / 300.0)

        button = Button(
            text=self.mode,
            size_hint=(None, None), # Disable automatic sizing
            size=(300, 100),         # Set a fixed size (width, height)
            pos_hint={'right': 1, 'top': 1} # Position at the top right
        )
        button.bind(on_press=self.toggle_mode)
        root.add_widget(button)

        return root

    def get_mode(self):
        return self.mode

    def toggle_mode(self, instance):
        if self.mode == DISAPPEAR_MODE:
            self.mode = PHOTO_MODE
        else:
            self.mode = DISAPPEAR_MODE
        instance.text = self.mode

        self.mask_widget.clear_canvas()


class MaskingWidget(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.clear_canvas()
        self.app = app

        self.bind(pos=self.update_canvas, size=self.update_canvas)
        self.update_canvas()

    def get_mode(self):
        return self.app.get_mode()

    def on_mouse_pos(self, window, pos):
        # Update the mouse position relative to the widget
        self.mouse_x = pos[0] - self.pos[0] - RADIUS/2
        self.mouse_y = pos[1] - self.pos[1] - RADIUS/2

    def clear_canvas(self):
        self.mouse_x = 0
        self.mouse_y = 0

        self.previous_touch_timestamps = []
        self.previous_mouse_x = []
        self.previous_mouse_y = []
        self.is_currently_touched = False

    def update_canvas(self, *args):
        self.canvas.clear()
        with self.canvas:
            # --- PHASE 1: Draw the mask ---
            # StencilPush creates a new stencil layer
            StencilPush()

            # Draw the black mask over the entire widget area
            Color(0, 0, 0, 1)  # Black color
            Rectangle(pos=self.pos, size=self.size)

            # Draw the transparent "hole" for the camera view
            Color(0, 0, 0, 0)  # Transparent color
            if self.mouse_x and self.mouse_y:
                current_time = time.time()
                first_viable_index = None
                if len(self.previous_mouse_x) and len(self.previous_mouse_y):
                    for i in range(0, len(self.previous_mouse_x)):
                        if self.get_mode() == DISAPPEAR_MODE and current_time - self.previous_touch_timestamps[i] > DELETION_LAG_SEC:
                            continue
                        if not first_viable_index:
                            first_viable_index = i
                        Ellipse(pos=(self.previous_mouse_x[i], self.previous_mouse_y[i]),
                                size=(RADIUS, RADIUS)) # Adjust hole size
                if not len(self.previous_mouse_x) or self.mouse_x != self.previous_mouse_x[-1] or self.mouse_y != self.previous_mouse_y[-1]:
                    self.previous_touch_timestamps.append(current_time)
                    self.previous_mouse_x.append(self.mouse_x)
                    self.previous_mouse_y.append(self.mouse_y)

            # --- PHASE 2: Apply the stencil to the background ---
            # StencilUse uses the mask created in Phase 1
            StencilUse()

            # The background should be drawn here, but the camera is a separate widget.
            # We must draw a solid color to cover the camera area where the mask is solid.
            Color(0, 0, 0, 1)  # Draw a solid black color to hide the camera view
            Rectangle(pos=self.pos, size=self.size)

            # --- PHASE 3: Clean up the stencil ---
            StencilUnUse()

            # Redraw the transparent hole to clean up the stencil buffer.
            #Ellipse(pos=(self.mouse_x , self.mouse_y), size=(500, 500))

            # --- PHASE 4: Remove the stencil layer ---
            StencilPop()

if __name__ == '__main__':
    CameraMaskApp().run()

