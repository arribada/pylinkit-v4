import configparser
import struct
import binascii
import zipfile


class OrderedRawConfigParser(configparser.RawConfigParser):
    def write(self, fp):
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for key in sorted( self._sections[section] ): 
                if key != "__name__":
                    fp.write("%s = %s\n" %
                             (key, str( self._sections[section][ key ] ).replace('\n', '\n\t')))    
            fp.write("\n")    


def extract_params_from_config_file(file):
    cfg = OrderedRawConfigParser()
    cfg.optionxform = lambda option: option
    with open(file) as f:
        cfg.read_string(f.read())
        return cfg['PARAM']


def stm32_crc32(data):
    """CRC-32/MPEG-2 (STM32 hardware CRC compatible).
    Polynomial: 0x04C11DB7 (MSB-first, non-reflected)
    Initial value: 0xFFFFFFFF, no final XOR, no reflection.
    Used by STM32WL bootloader for firmware verification."""
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc


def create_wrapped_file_with_crc32(bin_data):
    return struct.pack('>II', len(bin_data), binascii.crc32(bin_data)) + bin_data


def create_smd_wrapped_file(bin_data):
    """Wrap SMD firmware binary with size + STM32 CRC32 header.
    The nRF uses this header to know the firmware size and verify
    integrity after the DFU transfer to the SMD module."""
    crc = stm32_crc32(bin_data)
    return struct.pack('>II', len(bin_data), crc) + bin_data


def extract_firmware_file_from_dfu(file):
    zf = zipfile.ZipFile(file, mode='r')
    files = zf.namelist()

    # Try to find a legitimate firmware file
    fw_file = None
    for i in files:
        if '.bin' in i:
            fw_file = i
            print('Using firmware file {} from DFU zip archive'.format(fw_file))
            break
    if not fw_file:
        print('Could not find a valid firmware image file in ZIP archive')
        raise Exception('Invalid DFU file')

    # Extract firmware file data
    bin_data = zf.read(fw_file)

    # First 4 bytes are the image size
    # Next 4 bytes is a CRC32 computed over image data
    # Image data then follows
    return create_wrapped_file_with_crc32(bin_data)
