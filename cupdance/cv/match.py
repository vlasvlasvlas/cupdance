import time

class MatchEngine:
    def __init__(self, match_eps=0.05, hold_ms=400, cooldown_ms=5000):
        self.eps = match_eps
        self.hold_ms = hold_ms / 1000.0
        self.cooldown_ms = cooldown_ms / 1000.0
        
        # State
        self.active_matches = {
            "AB": False, "AC": False, "AD": False,
            "BC": False, "BD": False, "CD": False,
            "ABC": False, "ABD": False, "ACD": False, "BCD": False,
            "ABCD": False
        }
        
        # Timing for hold logic
        # Stores start_time of a potential match
        self.candidates = {} 
        
        # Cooldown for big events
        self.last_super_match_time = 0

    def check(self, v):
        """
        v: list of 4 floats [vA, vB, vC, vD]
        Returns: dict of active matches
        """
        curr_time = time.time()
        
        # Helper: are x and y close?
        def near(x, y):
            # Circular distance logic
            d = abs(x - y)
            if d > 0.5: d = 1.0 - d
            return d < self.eps
        
        # 1. Check Pairs
        pairs = [("AB",0,1), ("AC",0,2), ("AD",0,3), ("BC",1,2), ("BD",1,3), ("CD",2,3)]
        
        for name, i, j in pairs:
            if near(v[i], v[j]):
                self._handle_candidate(name, curr_time, True)
            else:
                self._handle_candidate(name, curr_time, False)

        # 2. Check Triples (only if pairs active? No, check logic directly)
        triples = [("ABC",0,1,2), ("ABD",0,1,3), ("ACD",0,2,3), ("BCD",1,2,3)]
        for name, i, j, k in triples:
            if near(v[i], v[j]) and near(v[j], v[k]): # Transitive close
                 self._handle_candidate(name, curr_time, True)
            else:
                 self._handle_candidate(name, curr_time, False)
                 
        # 3. Check Quad (ABCD)
        if (curr_time - self.last_super_match_time) > self.cooldown_ms:
            if near(v[0], v[1]) and near(v[1], v[2]) and near(v[2], v[3]):
                 is_match = self._handle_candidate("ABCD", curr_time, True)
                 if is_match:
                     self.last_super_match_time = curr_time
            else:
                 self._handle_candidate("ABCD", curr_time, False)
        else:
            # Cooldown active
            self.active_matches["ABCD"] = False

        return self.active_matches

    def _handle_candidate(self, name, curr_time, is_near):
        if is_near:
            if name not in self.candidates:
                # Start timer
                self.candidates[name] = curr_time
            elif (curr_time - self.candidates[name]) > self.hold_ms:
                # Held long enough -> Activate
                self.active_matches[name] = True
                return True
        else:
            # Not near -> Reset
            if name in self.candidates:
                del self.candidates[name]
            self.active_matches[name] = False
        return False
