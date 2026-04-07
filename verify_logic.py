
import numpy as np
from geometry_brain import GeometryClassifier

def test_geometry_brain():
    print("Testing GeometryClassifier...")
    brain = GeometryClassifier()
    
    # scan for number of features expected
    # GeometryClassifier expects 1662 features
    
    # Test 1: Zeros (No Hand)
    zeros = np.zeros(1662)
    res = brain.predict(zeros)
    print(f"Test 1 (Zeros): {res} (Expected: 'No Hand' or similar)")
    
    # Test 2: Random Noise
    # This might trigger "..." or some random sign if lucky, but likely "..."
    noise = np.random.rand(1662)
    res_noise = brain.predict(noise)
    print(f"Test 2 (Random): {res_noise} (Expected: '...' or 'No Hand')")
    
    # Test 3: Constructed "YES" (Thumbs Up)
    # RH starts at 1599
    # We need to set RH landmarks to simulate thumbs up.
    # Thumbs up: Thumb tip ABOVE thumb IP. All other fingers CLOSED (Tip BELOW PIP).
    # Remember Y is down (0 is top). So Above means y_tip < y_ip.
    
    rh = np.zeros((21, 3))
    
    # Fill with some base values so it's not "No Hand"
    rh[:, :] = 0.5 
    
    # Thumb: Tip (4) < IP (3). E.g. Tip y=0.2, IP y=0.3
    rh[4] = [0.5, 0.2, 0.0]
    rh[3] = [0.5, 0.3, 0.0]
    
    # Index: Closed. Tip (8) > PIP (6). E.g. Tip y=0.6, PIP y=0.5
    rh[8] = [0.5, 0.6, 0.0]
    rh[6] = [0.5, 0.5, 0.0]
    
    # Middle: Closed
    rh[12] = [0.5, 0.6, 0.0]
    rh[10] = [0.5, 0.5, 0.0]
    
    # Ring: Closed
    rh[16] = [0.5, 0.6, 0.0]
    rh[14] = [0.5, 0.5, 0.0]
    
    # Pinky: Closed
    rh[20] = [0.5, 0.6, 0.0]
    rh[18] = [0.5, 0.5, 0.0]
    
    # Flatten and insert into full array
    full_landmarks = np.zeros(1662)
    rh_flat = rh.flatten()
    full_landmarks[1599:1599+63] = rh_flat
    
    res_yes = brain.predict(full_landmarks)
    print(f"Test 3 (Simulated YES): {res_yes} (Expected: 'YES')")

    # Test 4: Constructed "HELLO" (Open Palm)
    # All fingers Open. Tip < PIP.
    rh_hello = np.zeros((21, 3))
    rh_hello[:, :] = 0.5
    
    # All tips y=0.2, all pips y=0.5
    rh_hello[8] = [0.5, 0.2, 0.0]
    rh_hello[6] = [0.5, 0.5, 0.0]
    
    rh_hello[12] = [0.5, 0.2, 0.0]
    rh_hello[10] = [0.5, 0.5, 0.0]
    
    rh_hello[16] = [0.5, 0.2, 0.0]
    rh_hello[14] = [0.5, 0.5, 0.0]
    
    rh_hello[20] = [0.5, 0.2, 0.0]
    rh_hello[18] = [0.5, 0.5, 0.0]
    
    full_landmarks_hello = np.zeros(1662)
    full_landmarks_hello[1599:1599+63] = rh_hello.flatten()
    
    res_hello = brain.predict(full_landmarks_hello)
    print(f"Test 4 (Simulated HELLO): {res_hello} (Expected: 'HELLO')")

if __name__ == "__main__":
    test_geometry_brain()
