import re

def parse_mai2_data(hex_str):
    """
    Parse mai2 data format hex string to active zones
    """
    # Convert hex string to bytes
    hex_bytes = [int(x, 16) for x in hex_str.split()]
    if len(hex_bytes) != 9:
        raise ValueError("Invalid mai2 data length (expected 9 bytes)")
    
    # Verify start/end bytes
    if hex_bytes[0] != 0x28 or hex_bytes[8] != 0x29:
        raise ValueError("Invalid start/end bytes for mai2 format")
    
    # Zone mapping (byte_pos, bit_pos): zone_name
    zone_mapping = {
        # A区
        (7, 0): 'A1', (7, 1): 'A2', (7, 2): 'A3', (7, 3): 'A4',
        (7, 4): 'A5', (6, 0): 'A6', (6, 1): 'A7', (6, 2): 'A8',
        # B区
        (6, 3): 'B1', (6, 4): 'B2', (5, 0): 'B3', (5, 1): 'B4',
        (5, 2): 'B5', (5, 3): 'B6', (5, 4): 'B7', (4, 0): 'B8',
        # C区
        (4, 1): 'C1', (4, 2): 'C2',
        # D区
        (4, 3): 'D1', (4, 4): 'D2', (3, 0): 'D3', (3, 1): 'D4',
        (3, 2): 'D5', (3, 3): 'D6', (3, 4): 'D7', (2, 0): 'D8',
        # E区
        (2, 1): 'E1', (2, 2): 'E2', (2, 3): 'E3', (2, 4): 'E4',
        (1, 0): 'E5', (1, 1): 'E6', (1, 2): 'E7', (1, 3): 'E8',
    }
    
    active_zones = []
    for byte_pos in range(7, 0, -1):  # Only check bytes 1-7
        byte = hex_bytes[byte_pos]
        for bit_pos in range(0, 8, 1):
            if byte & (1 << bit_pos):
                zone = zone_mapping.get((byte_pos, bit_pos))
                if zone:
                    active_zones.append(zone)
    
    return f"mai2:{','.join(active_zones)}"

def parse_mai_data(hex_str):
    """
    Parse mai data format hex string to active zones
    """
    # Convert hex string to bytes
    hex_bytes = [int(x, 16) for x in hex_str.split()]
    if len(hex_bytes) != 14:
        raise ValueError("Invalid mai data length (expected 14 bytes)")
    
    # Verify start/end bytes
    if hex_bytes[0] != 0x28 or hex_bytes[13] != 0x29:
        raise ValueError("Invalid start/end bytes for mai format")
    
    # Zone mapping (byte_pos, bit_pos): zone_name
    zone_mapping = {
        # A区 (P1)
        (1, 0): 'A1', (1, 2): 'A2', (2, 0): 'A3', (2, 2): 'A4',
        (3, 0): 'A5', (3, 2): 'A6', (4, 0): 'A7', (4, 2): 'A8',
        # B区 (P1)
        (1, 1): 'B1', (1, 3): 'B2', (2, 1): 'B3', (2, 3): 'B4',
        (3, 1): 'B5', (3, 3): 'B6', (4, 1): 'B7', (4, 3): 'B8',
        # C区 (P1)
        (4, 4): 'C',
    }
    
    active_zones = []
    for byte_pos, bit_pos in zone_mapping:
        if hex_bytes[byte_pos] & (1 << bit_pos):
            active_zones.append(zone_mapping[(byte_pos, bit_pos)])
    
    return f"mai:{','.join(active_zones)}"

def main():
    print("Enter hex data (e.g., '28 4C 4C 4C 4C 40 40 40 40 40 40 40 40 29' or '28 01 01 01 01 01 01 01 29'):")
    while True:
        try:
            user_input = input().strip()
            if not re.match(r'^([0-9A-Fa-f]{2} )+[0-9A-Fa-f]{2}$', user_input):
                print("Invalid hex format. Please enter space-separated hex bytes.")
                continue
            
            # Determine format by length
            hex_bytes = user_input.split()
            if len(hex_bytes) == 9:
                result = parse_mai2_data(user_input)
            elif len(hex_bytes) == 14:
                result = parse_mai_data(user_input)
            else:
                print("Invalid data length. Must be 9 bytes (mai2) or 14 bytes (mai).")
                continue
            
            print(result)
            print("\nEnter next hex data or Ctrl+C to exit:")
            
        except ValueError as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == '__main__':
    main()
