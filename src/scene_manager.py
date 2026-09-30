class Scene:
    def __init__(self, manager):
        self.manager = manager

    def tick(self, input_handler):
        """Called once per game tick (every 250ms). All game logic goes here."""
        pass

    def draw(self, screen, alpha=1.0):
        """Called every render frame (60fps). Only drawing, no logic.

        alpha is how far we are between the last completed game tick and
        the next one (0..1) — entities use it to interpolate their
        rendered position for smooth motion despite the slower tick rate.
        """
        pass

    def on_enter(self):
        pass

    def on_exit(self):
        pass


class SceneManager:
    def __init__(self):
        self._stack = []

    @property
    def current(self):
        return self._stack[-1] if self._stack else None

    def push(self, scene):
        if self.current:
            self.current.on_exit()
        self._stack.append(scene)
        scene.on_enter()

    def replace(self, scene):
        if self.current:
            self.current.on_exit()
            self._stack.pop()
        self._stack.append(scene)
        scene.on_enter()

    def pop(self):
        if self.current:
            self.current.on_exit()
            self._stack.pop()
        if self.current:
            self.current.on_enter()

    def tick(self, input_handler):
        if self.current:
            self.current.tick(input_handler)

    def draw(self, screen, alpha=1.0):
        if self.current:
            self.current.draw(screen, alpha)
