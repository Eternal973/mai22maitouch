import re

def hex_str_to_bytes(hex_str):
    """将空格分隔的十六进制字符串转换为bytes对象"""
    if not re.match(r'^([0-9A-Fa-f]{2} )*[0-9A-Fa-f]{2}$', hex_str.strip()):
        raise ValueError("Invalid hex format. Expected space-separated bytes (e.g. '28 01 00 02 29')")
    return bytes.fromhex(hex_str)

def bytes_to_hex_str(byte_data):
    """将bytes对象转换为带空格的十六进制字符串"""
    return ' '.join(f'{b:02X}' for b in byte_data)

def transform_touch_data(raw_data):
    """
    将mai2格式的触摸数据转换为mai格式
    输入: mai2格式的bytes (9字节，以b'\x28'开头，b'\x29'结尾)
    输出: mai格式的bytes (14字节，以b'\x28'开头，b'\x29'结尾)
    """
    if len(raw_data) != 9 or raw_data[0] != 0x28 or raw_data[8] != 0x29:
        raise ValueError("Invalid mai2 input data format")

    mai_data = [0x40] * 14
    mai_data[0] = 0x28
    mai_data[13] = 0x29

    zone_mapping = {
        'A1': (1, 0), 'A2': (1, 2), 'A3': (2, 0), 'A4': (2, 2),
        'A5': (3, 0), 'A6': (3, 2), 'A7': (4, 0), 'A8': (4, 2),
        'B1': (1, 1), 'B2': (1, 3), 'B3': (2, 1), 'B4': (2, 3),
        'B5': (3, 1), 'B6': (3, 3), 'B7': (4, 1), 'B8': (4, 3),
        'C1': (4, 4), 'C2': (4, 4)
    }

    mai2_zones = {
            # A区
            (1, 0): 'A1', (1, 1): 'A2', (1, 2): 'A3', (1, 3): 'A4',
            (1, 4): 'A5', (2, 0): 'A6', (2, 1): 'A7', (2, 2): 'A8',
            # B区
            (2, 3): 'B1', (2, 4): 'B2', (3, 0): 'B3', (3, 1): 'B4',
            (3, 2): 'B5', (3, 3): 'B6', (3, 4): 'B7', (4, 0): 'B8',
            # C区
            (4, 1): 'C1', (4, 2): 'C2'
    }

    for byte_pos in range(1, 8):
        byte = raw_data[byte_pos]
        for bit_pos in range(8):
            if byte & (1 << bit_pos):
                zone = mai2_zones.get((byte_pos, bit_pos))
                if zone in zone_mapping:
                    mai_byte, mai_bit = zone_mapping[zone]
                    mai_data[mai_byte] |= (1 << mai_bit)

    return bytes(mai_data)

def test_case(input_hex):
    """执行单个测试用例"""
    try:
        print(f"\n输入: {input_hex}")
        input_bytes = hex_str_to_bytes(input_hex)
        output_bytes = transform_touch_data(input_bytes)
        output_hex = bytes_to_hex_str(output_bytes)
        print(f"输出: {output_hex}")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == '__main__':
    print("MAI2到MAI格式转换测试")
    print("示例输入: 28 00 00 00 02 00 00 00 29 (只有C1触发)")
    while True:
        input_hex = input("\n请输入MAI2格式的十六进制数据: ").strip()
        if input_hex.lower() == 'q':
            break
        test_case(input_hex)
