from engines.base_engine import BaseEngine


class HybridEngine(BaseEngine):

    def __init__(self):

        super().__init__("RTL Hybrid")

    def on_start(self):

        print("RTL Hybrid Engine started.")

    def on_stop(self):

        print("RTL Hybrid Engine stopped.")
