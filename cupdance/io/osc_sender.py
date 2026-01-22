from pythonosc import udp_client

class OSCSender:
    def __init__(self, ip="127.0.0.1", port=8000):
        self.ip = ip
        self.port = port
        self.client = udp_client.SimpleUDPClient(ip, port)
        print(f"[OSC] Ready. Sending to {ip}:{port}")

    def send_frame(self, cup_values, quad_data, matches):
        """
        Sends all relevant frame data in a bundle (or sequence of messages).
        """
        # 1. Cups (Values 0..1)
        # /cup/1/value, /cup/2/value...
        self.client.send_message("/cups/A/value", cup_values[0])
        self.client.send_message("/cups/B/value", cup_values[1])
        self.client.send_message("/cups/C/value", cup_values[2])
        self.client.send_message("/cups/D/value", cup_values[3])

        # 2. Floor Quadrants (Density 0..1)
        # /floor/q1, /floor/q2...
        self.client.send_message("/floor/q1", float(quad_data.get('q1_density', 0)))
        self.client.send_message("/floor/q2", float(quad_data.get('q2_density', 0)))
        self.client.send_message("/floor/q3", float(quad_data.get('q3_density', 0)))
        self.client.send_message("/floor/q4", float(quad_data.get('q4_density', 0)))

        # 3. Matches (Triggers 0 or 1)
        # Only send active matches or send all? 
        # Sending all active matches as list? Or individual address?
        # Individual is easier to map in Ableton/Max.
        # Let's send only the important ones or all.
        
        # Optimization: Send "active match name" string? 
        # /match/name "AB"
        # And also /match/harmony_level (0=None, 1=Pair, 2=Triple, 3=Quad)
        
        active_list = [k for k, v in matches.items() if v]
        self.client.send_message("/matches/list", active_list if active_list else ["None"])
        
        self.client.send_message("/matches/ABCD", 1 if matches.get("ABCD") else 0)
        
        # Send harmony level
        level = 0
        if matches.get("ABCD"): level = 3
        elif any(len(k)==3 and v for k,v in matches.items()): level = 2
        elif any(len(k)==2 and v for k,v in matches.items()): level = 1
        
        self.client.send_message("/harmony/level", level)
