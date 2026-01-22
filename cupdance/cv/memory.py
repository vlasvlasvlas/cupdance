import numpy as np

class MemoryEngine:
    def __init__(self, grid_size=16):
        self.grid_size = grid_size
        self.memory_grid = np.zeros((grid_size, grid_size), dtype=np.float32)
        
        # Default decay per quadrant (controlled by cups later)
        # 0.9 = long trails, 0.5 = short trails
        self.decays = [0.90, 0.90, 0.90, 0.90]

    def update(self, live_grid, cup_values):
        """
        Updates memory grid based on live input and cup values (which control decay).
        live_grid: 16x16 float 0..1
        cup_values: list of 4 floats 0..1 (vA, vB, vC, vD)
        """
        # Map cup values to decay rates
        # Cup value 0.0 -> Decay 0.80 (Shortish trails)
        # Cup value 1.0 -> Decay 0.99 (Infinite trails / Freeze)
        # We need to map cup_values to self.decays per quadrant
        
        for i in range(4):
            # linear mapping: 0.80 + 0.19 * v
            self.decays[i] = 0.80 + (0.19 * cup_values[i])

        # Create a decay mask matching the quadrants
        mid = self.grid_size // 2
        decay_map = np.ones((self.grid_size, self.grid_size), dtype=np.float32)
        
        # Q1 (Top Left) -> Cup A (idx 0)
        decay_map[0:mid, 0:mid] = self.decays[0]
        # Q2 (Top Right) -> Cup B (idx 1)
        decay_map[0:mid, mid:]  = self.decays[1]
        # Q3 (Bot Left) -> Cup C (idx 2)
        decay_map[mid:, 0:mid]  = self.decays[2]
        # Q4 (Bot Right) -> Cup D (idx 3)
        decay_map[mid:, mid:]   = self.decays[3]
        
        # Apply formula: Mem = Mem * Decay + Live * (1 - Decay)
        # Or Mem = Mem * Decay + Live (Additive)
        # Standard EMA style:
        self.memory_grid = (self.memory_grid * decay_map) + (live_grid * (1.0 - decay_map))
        
        # Alternative Interpretation:
        # "Trails" visual effect usually means: Mem = max(Live, Mem * Decay)
        # But specification said: memory[q] = memory[q]*decay + live[q]*(1-decay)
        # This acts like a low-pass filter (smoothing over time), not just visual trails.
        # This is good for "weight of the past".
        
        return self.memory_grid
