"""Unit tests for the SMD module firmware update (pylinkit/smd_dfu.py).

What these tests guarantee:
  - A file the bootloader would not boot is refused before anything is sent:
    the bootloader erases the application before it checks the image.
  - The transport comes from the image variant (_Uart/_Spi) unless given;
    a LinkIt v4.0.x, which takes both file ids over SPI, is sent SPI.
  - An image of the other variant is refused unless the switch is asked for:
    the module would then speak a transport the LinkIt does not.
  - A file refused by the LinkIt (wrong transport) is reported as such, with
    no wait for a DFU result.
  - Every failure tells the operator not to cut power, stay connected and
    resend; a timeout tells them to wait before resending.
"""
import struct

import pytest

from pylinkit import smd_dfu
from pylinkit.smd_dfu import SmdImage, SmdImageError

UART_BUILD = b'5019148_TxShtdwn_gui_basic_Pa_Uart,v11.1.0_e9373c5_0x6Tx,Oct 30 2026_22:50:02'
SPI_BUILD = b'61c2267_TxShtdwn_gui_basic_Pa_Spi,v11.1.0_e9373c5_0x6Tx,Oct 30 2026_20:37:12'


def image(build=UART_BUILD, sp=0x20008000, reset=0x0800A40D, size=4096):
    head = struct.pack('<II', sp, reset)
    body = head + b'\x00' * 64 + build + b'\x00'
    return body + b'\xff' * (size - len(body))


class FakeTracker:
    def __init__(self, accept=True, result=None, fw_version='v4.2.1'):
        self.accept = accept
        self.result = result if result is not None else {'status': 0, 'info': 'v1.0.0'}
        self.fw_version = fw_version
        self.sent = []

    def read(self, params):
        return {'FW_APP_VERSION': self.fw_version}

    def smd_firmware_update(self, data, mode, timeout=None):
        self.sent.append((mode, data))
        return self.accept

    def wait_smd_dfu_result(self, timeout):
        if self.result == 'timeout':
            raise TimeoutError()
        return self.result


def run(dev, data, mode=None, switch=False, answer=True):
    return smd_dfu.update(dev, data, mode, switch, lambda q: answer)


# --- the image -----------------------------------------------------------------

def test_variant_and_build_are_read_from_the_image():
    assert SmdImage(image(UART_BUILD)).variant == 'uart'
    img = SmdImage(image(SPI_BUILD, reset=0x0800B635))
    assert img.variant == 'spi'
    assert img.build == SPI_BUILD.decode()


@pytest.mark.parametrize('size', [smd_dfu.APP_MAX_SIZE + 1, 236576])
def test_a_full_image_is_refused(size):
    with pytest.raises(SmdImageError):
        SmdImage(image(size=size))


def test_the_largest_application_passes():
    assert SmdImage(image(size=smd_dfu.APP_MAX_SIZE)).size == smd_dfu.APP_MAX_SIZE


@pytest.mark.parametrize('sp', [0x1FFFFFFC, 0x20010004, 0x3A3A3A3A])
def test_a_stack_outside_ram_is_refused(sp):
    with pytest.raises(SmdImageError):
        SmdImage(image(sp=sp))


@pytest.mark.parametrize('reset', [0x07FFFFFF, 0x08032001, 0x0800A40C])
def test_a_reset_vector_outside_the_application_or_not_thumb_is_refused(reset):
    with pytest.raises(SmdImageError):
        SmdImage(image(reset=reset))


def test_bounds_are_inclusive():
    SmdImage(image(sp=0x20000000, reset=0x08000001))
    SmdImage(image(sp=0x20010000, reset=0x08031FFF))


def test_an_intel_hex_file_is_refused():
    with pytest.raises(SmdImageError):
        SmdImage(b':020000040800F2\n' + b':10000000' + b'00' * 16 + b'\n')


def test_uart_waits_longer_than_spi():
    assert smd_dfu.result_timeout(76472, 'uart') > 190 + 60
    assert smd_dfu.result_timeout(76472, 'spi') > 65 + 60
    assert smd_dfu.result_timeout(smd_dfu.APP_MAX_SIZE, 'uart') > smd_dfu.result_timeout(76472, 'uart')


@pytest.mark.parametrize('version,both', [('v4.0.0', True), ('4.0.3', True), ('v4.1.0', False),
                                          ('v4.2.0-250-gcfbc4702', False), ('', False), (None, False)])
def test_only_v4_0_takes_both_file_ids(version, both):
    assert smd_dfu.accepts_both_file_ids(version) is both


# --- the flow --------------------------------------------------------------------

def test_a_bad_file_is_never_sent(capsys):
    dev = FakeTracker()
    assert run(dev, image(size=236576)) is False
    assert dev.sent == []
    assert "Rien n'a été envoyé" in capsys.readouterr().out


def test_the_mode_comes_from_the_image():
    dev = FakeTracker()
    assert run(dev, image(SPI_BUILD, reset=0x0800B635)) is True
    assert dev.sent[0][0] == 'spi'


def test_a_v4_0_linkit_is_sent_spi_and_a_uart_image_is_a_switch(capsys):
    dev = FakeTracker(fw_version='v4.0.0')
    assert run(dev, image(UART_BUILD)) is False
    assert dev.sent == []
    assert '--smdfw_switch_variant' in capsys.readouterr().out


def test_an_image_of_the_other_variant_is_refused(capsys):
    dev = FakeTracker()
    assert run(dev, image(UART_BUILD), mode='spi') is False
    assert dev.sent == []
    out = capsys.readouterr().out
    assert 'UART seulement' in out and '--smdfw_switch_variant' in out


def test_a_variant_switch_goes_when_asked():
    dev = FakeTracker()
    assert run(dev, image(UART_BUILD), mode='spi', switch=True) is True
    assert dev.sent[0][0] == 'spi'


def test_an_image_without_variant_needs_the_mode(capsys):
    dev = FakeTracker()
    assert run(dev, image(b'no build string here')) is False
    assert dev.sent == []
    assert run(dev, image(b'no build string here'), mode='uart') is True


def test_declining_sends_nothing():
    dev = FakeTracker()
    assert run(dev, image(), answer=False) is False
    assert dev.sent == []


def test_the_spi_warning_is_shown_for_spi_only(capsys):
    run(FakeTracker(), image(UART_BUILD))
    assert '2 MHz' not in capsys.readouterr().out
    run(FakeTracker(), image(SPI_BUILD, reset=0x0800B635))
    assert '2 MHz' in capsys.readouterr().out


@pytest.mark.parametrize('version,at_125k', [('v4.0.6', True), ('4.0.9', True), ('v4.0.5', False),
                                             ('v4.0.10', False), ('v4.1.0', False), ('v4.2.0', False),
                                             ('v4.2.0-250-g2d8194f', False), ('', False)])
def test_only_v4_0_6_to_9_ran_the_spi_dfu_at_125k(version, at_125k):
    assert smd_dfu.spi_dfu_at_125k(version) is at_125k


def test_no_spi_warning_on_a_linkit_whose_dfu_ran_at_125k(capsys):
    dev = FakeTracker(fw_version='v4.0.9')
    assert run(dev, image(SPI_BUILD, reset=0x0800B635), mode='spi')
    assert '2 MHz' not in capsys.readouterr().out
    run(FakeTracker(fw_version='v4.1.10'), image(SPI_BUILD, reset=0x0800B635), mode='spi')
    assert '2 MHz' in capsys.readouterr().out


def test_a_file_refused_by_the_linkit_points_to_the_other_transport(capsys):
    dev = FakeTracker(accept=False)
    assert run(dev, image(SPI_BUILD, reset=0x0800B635)) is False
    out = capsys.readouterr().out
    assert 'rien n\'a été transmis au module' in out and '--smdfw_mode uart' in out


def test_the_file_is_wrapped_with_the_stm32_crc():
    dev = FakeTracker()
    data = image()
    run(dev, data)
    size, crc = struct.unpack('>II', dev.sent[0][1][:8])
    assert size == len(data) and dev.sent[0][1][8:] == data


def test_a_failure_says_resend_without_cutting(capsys):
    dev = FakeTracker(result={'status': 1, 'info': 'DFU failed: error 1'})
    assert run(dev, image()) is False
    out = capsys.readouterr().out
    assert 'Ne coupez pas' in out and 'renvoyez la même image maintenant' in out


def test_error_9_hints_at_the_variant_and_still_says_resend(capsys):
    dev = FakeTracker(result={'status': 1, 'info': 'DFU failed: error 9'})
    run(dev, image())
    out = capsys.readouterr().out
    assert '_Uart/_Spi' in out and 'renvoyez la même image maintenant' in out


def test_a_timeout_says_wait_before_resending(capsys):
    dev = FakeTracker(result='timeout')
    assert run(dev, image()) is False
    assert 'Attendez encore 2 minutes' in capsys.readouterr().out


def test_success_shows_the_image_sent(capsys):
    assert run(FakeTracker(), image()) is True
    assert UART_BUILD.decode() in capsys.readouterr().out
