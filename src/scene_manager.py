class Scene:
    def __init__(self, manager):
        self.manager = manager

    def tick(self, input_handler):
        """Called once per game tick (every 250ms). All game logic goes here."""
        pass

    def draw(self, screen):
        """Called every render frame (60fps). Only drawing, no logic."""
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

    def draw(self, screen):
        if self.current:
            self.current.draw(screen)
