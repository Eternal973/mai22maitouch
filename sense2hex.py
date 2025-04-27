import re

def generate_mai2_data(active_zones):
    """
    Generate mai2 data format based on active zones.
    """
    # Initialize data packet
    data = [0] * 9
    data[0] = 0x28  # Start byte '('
    data[8] = 0x29  # End byte ')'

    # Zone-to-byte/bit mapping
    zone_mapping = {
        # A区
        'A1': (7, 0), 'A2': (7, 1), 'A3': (7, 2), 'A4': (7, 3),
        'A5': (7, 4), 'A6': (6, 0), 'A7': (6, 1), 'A8': (6, 2),
        # B区
        'B1': (6, 3), 'B2': (6, 4), 'B3': (5, 0), 'B4': (5, 1),
        'B5': (5, 2), 'B6': (5, 3), 'B7': (5, 4), 'B8': (4, 0),
        # C区
        'C1': (4, 1), 'C2': (4, 2),
        # D区
        'D1': (4, 3), 'D2': (4, 4), 'D3': (3, 0), 'D4': (3, 1),
        'D5': (3, 2), 'D6': (3, 3), 'D7': (3, 4), 'D8': (2, 0),
        # E区
        'E1': (2, 1), 'E2': (2, 2), 'E3': (2, 3), 'E4': (2, 4),
        'E5': (1, 0), 'E6': (1, 1), 'E7': (1, 2), 'E8': (1, 3),
    }

    # Activate zones
    for zone in active_zones:
        if zone in zone_mapping:
            byte_pos, bit_pos = zone_mapping[zone]
            data[byte_pos] |= (1 << bit_pos)

    return bytes(data)


def generate_mai_data(active_zones):
    """
    Generate mai data format based on active zones.
    """
    # Initialize data packet
    data = [0x40] * 14
    data[0] = 0x28  # Start byte '('
    data[13] = 0x29  # End byte ')'

    # Zone-to-byte/bit mapping for P1
    zone_mapping = {
        # A区
        'A1': (1, 0), 'A2': (1, 2), 'A3': (2, 0), 'A4': (2, 2),
        'A5': (3, 0), 'A6': (3, 2), 'A7': (4, 0), 'A8': (4, 2),
        # B区
        'B1': (1, 1), 'B2': (1, 3), 'B3': (2, 1), 'B4': (2, 3),
        'B5': (3, 1), 'B6': (3, 3), 'B7': (4, 1), 'B8': (4, 3),
        # C区 (merged into a single bit)
        'C': (4, 4),
    }

    # Activate zones
    for zone in active_zones:
        if zone in zone_mapping:
            byte_pos, bit_pos = zone_mapping[zone]
            data[byte_pos] |= (1 << bit_pos)

    return bytes(data)


def format_output(data):
    """
    Format the output as ASCII string and hex string.
    """
    ascii_output = ''.join(chr(byte) if 32 <= byte <= 126 else '.' for byte in data)
    hex_output = ' '.join(f'{byte:02X}' for byte in data)
    return ascii_output, hex_output


def main():
    print("Enter your command (e.g., 'mai2:A1,A8,B1,B3,C1,D8,E2,E5' or 'mai:A1,A7,B2,B3,C'):")
    while True:
        user_input = input().strip()
        if user_input.startswith('mai2:'):
            # Handle mai2 input
            input_data = user_input[5:]  # Remove 'mai2:'
            active_zones = re.findall(r'[A-E]\d+', input_data)
            serial_data = generate_mai2_data(active_zones)
        elif user_input.startswith('mai:'):
            # Handle mai input
            input_data = user_input[4:]  # Remove 'mai:'
            active_zones = re.findall(r'[A-E]\d*', input_data)
            active_zones = [z if z != 'C' else 'C' for z in active_zones]  # Normalize 'C'
            serial_data = generate_mai_data(active_zones)
        else:
            print("Invalid input format. Please try again.")
            continue

        # Format and display output
        ascii_output, hex_output = format_output(serial_data)
        print(f"ASCII Output: {ascii_output}")
        print(f"Hex Output: {hex_output}")

        print("\nEnter your next command or Ctrl+C to exit:")


if __name__ == '__main__':
    main()
