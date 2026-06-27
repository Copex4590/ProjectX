from engines.base_engine import BaseEngine


class CameraEngine(BaseEngine):

    def __init__(self):

        super().__init__("Camera")

    def on_start(self):

        print("Camera Engine started.")

    def on_stop(self):

        print("Camera Engine stopped.")
