"""SMD module firmware update (DFU) through the LinkIt: checks made before
anything is sent, and the texts the operator must read.

The module's bootloader erases the application at the start of the update.
On the bootloaders before v3.0.0 (all modules shipped before 2026-10-31), a
power cut or a reset between that erase and a passing verification leaves the
STM32WL on its ROM: only SWD brings it back, and an SPI update fails at 2 MHz.
v3.0.0 restarts in its bootloader after such a cut and follows 2 MHz. A host
reads that version only from inside the bootloader, so every module is treated
as the old one.
"""
import re
import struct

# bl_check_app_valid (Bootloader/Src/bl_main.c): what the bootloader accepts
# as an application. The image is checked here, before the erase.
APP_MAX_SIZE = 204800  # 0x32000, the "max" of GET_INFO
SP_MIN, SP_MAX = 0x20000000, 0x20010000
RESET_MIN, RESET_MAX = 0x08000000, 0x08032000

# Build string the SMD firmware carries, e.g.
# "5019148_TxShtdwn_gui_basic_Pa_Uart,v11.1.0_e9373c5_0x6Tx,Oct 30 2026_22:50:02"
_BUILD_RE = re.compile(rb'[0-9a-f]{7}_[A-Za-z0-9_]*_(Uart|Spi),v[\x20-\x7e]{0,60}')

BOOTLOADER_WARNING = (
    "Le bootloader du module efface son application au début de la mise à jour.\n"
    "  - Ne coupez pas l'alimentation et restez connecté jusqu'au résultat.\n"
    "  - En cas d'échec : n'envoyez aucune autre commande SMD, ne vous déconnectez\n"
    "    pas, renvoyez l'image tout de suite.")

SPI_WARNING = (
    "DFU SPI : les firmwares LinkIt v4.1.0 à v4.2.0 le font à 2 MHz, et il échoue au\n"
    "milieu de l'écriture sur un bootloader SMD d'avant la v3.0.0 (3 essais sur 3 au\n"
    "banc), module effacé.\n"
    "Les v4.0.6 à v4.0.9 et ceux d'après le correctif du 31/10/2026 le font à 125 kHz.\n"
    "Sur une LinkIt à 2 MHz, mettez d'abord à jour son firmware.")


class SmdImageError(ValueError):
    """The file is not an SMD application image: nothing must be sent."""


class SmdImage:
    def __init__(self, data):
        self.size = len(data)
        if self.size < 8:
            raise SmdImageError(f"{self.size} octets : trop court pour une image SMD")
        if self.size > APP_MAX_SIZE:
            raise SmdImageError(f"{self.size} octets, plus que les {APP_MAX_SIZE} de l'application "
                                "(un *_full.bin ou un .hex ?)")
        self.sp, self.reset = struct.unpack_from('<II', data, 0)
        if not SP_MIN <= self.sp <= SP_MAX:
            raise SmdImageError(f"pile initiale 0x{self.sp:08X} hors de la RAM du STM32WL")
        if not RESET_MIN <= self.reset <= RESET_MAX or not self.reset & 1:
            raise SmdImageError(f"vecteur reset 0x{self.reset:08X} hors de l'application")
        m = _BUILD_RE.search(data)
        self.build = m.group(0).decode('ascii') if m else None
        self.variant = m.group(1).decode('ascii').lower() if m else None


def result_timeout(size, mode):
    """Seconds to wait for the SMDDFU result once the file is on the LinkIt.
    Bench 2026-10-31, 75 KB: UART 9600 baud ~190 s, SPI 125 kHz ~65 s."""
    return 60 + size * (0.004 if mode == 'uart' else 0.002)


def accepts_both_file_ids(fw_version):
    """LinkIt v4.0.x takes file id 3 and 4 alike, over the transport it was
    built for (SPI only at the time). From v4.1.0 the wrong id is refused at
    OTA start."""
    return bool(re.match(r'v?4\.0\.', fw_version or ''))


def spi_dfu_at_125k(fw_version):
    """LinkIt v4.0.6 to v4.0.9 ran the whole SMD link at 125 kHz, and their SPI
    DFU worked; v4.1.0 moved the link to 2 MHz (linkit-v4-core 37f5d397). The
    fix of 2026-10-31, which drops to 125 kHz for the DFU, is in no release yet."""
    return bool(re.match(r'v?4\.0\.[6-9](?!\d)', fw_version or ''))


FAILURE_ADVICE = (
    "Le module est peut-être resté dans son bootloader, sans application.\n"
    "  Ne coupez pas l'alimentation, ne vous déconnectez pas, n'envoyez aucune\n"
    "  autre commande SMD : renvoyez la même image maintenant.")


def update(dev, data, mode, switch_variant, confirm, ota_timeout=None):
    """Check the image, pick the transport, send it, wait for the result.
    ``mode``: 'uart', 'spi' or None (from the image). ``confirm(question)``
    returns True to go on. Returns True only when the LinkIt reports success."""
    from .utils import create_smd_wrapped_file, stm32_crc32

    try:
        image = SmdImage(data)
    except SmdImageError as e:
        print(f"SMD DFU REFUSÉ : ce fichier n'est pas une image d'application SMD ({e}).")
        print("  Rien n'a été envoyé. Prenez le *_dfu.bin du firmware SMD.")
        return False
    print(f"SMD firmware : {image.size} octets, CRC32 STM32 0x{stm32_crc32(data):08X}")
    print(f"  build : {image.build or 'inconnu'}")

    try:
        fw = dev.read(['FW_APP_VERSION']).get('FW_APP_VERSION', '')
    except Exception:
        fw = ''
    if mode is None:
        if image.variant is None:
            print("SMD DFU REFUSÉ : l'image ne dit pas si elle est UART ou SPI.")
            print("  Précisez --smdfw_mode, celui du firmware LinkIt. Rien n'a été envoyé.")
            return False
        mode = image.variant
        if accepts_both_file_ids(fw):
            mode = 'spi'
    print(f"SMD DFU mode : {mode.upper()} (file_id {3 if mode == 'uart' else 4})")

    if image.variant is not None and image.variant != mode:
        print(f"Cette image fait parler le module en {image.variant.upper()} seulement, et la LinkIt "
              f"lui parle en {mode.upper()} :")
        print(f"  après la mise à jour, il faudra un firmware LinkIt compilé pour "
              f"{image.variant.upper()}, sinon la LinkIt ne joindra plus le module.")
        if not switch_variant:
            print("SMD DFU REFUSÉ : ajoutez --smdfw_switch_variant si c'est voulu. Rien n'a été envoyé.")
            return False

    print(BOOTLOADER_WARNING)
    if mode == 'spi' and not spi_dfu_at_125k(fw):
        print(SPI_WARNING)
    if not confirm("Lancer la mise à jour du module SMD ? [o/N] : "):
        print("Mise à jour SMD annulée, rien n'a été envoyé.")
        return False

    if not dev.smd_firmware_update(create_smd_wrapped_file(data), mode=mode, timeout=ota_timeout):
        print("SMD DFU REFUSÉ par la LinkIt : rien n'a été transmis au module.")
        print(f"  Son firmware est sans doute compilé pour l'autre transport : essayez "
              f"--smdfw_mode {'spi' if mode == 'uart' else 'uart'} avec une image de cette variante.")
        return False

    wait_s = result_timeout(image.size, mode)
    print(f"Mise à jour du module en cours (jusqu'à {wait_s / 60:.0f} min) : "
          "ne coupez pas l'alimentation, restez connecté.")
    try:
        result = dev.wait_smd_dfu_result(timeout=wait_s)
    except TimeoutError:
        print(f"SMD DFU : pas de résultat après {wait_s:.0f} s.")
        print("  Attendez encore 2 minutes sans couper ni renvoyer. Si rien n'arrive,")
        print("  renvoyez l'image sans vous déconnecter.")
        return False
    if result['status'] == 0:
        print(f"SMD DFU SUCCESS : module {result['info'] or '(version non lue)'}, image {image.build or ''}")
        return True
    print(f"SMD DFU FAILED : {result['info']}")
    if result['info'].endswith('error 9'):
        # Entry failed: nothing erased by THIS attempt, but a module left erased
        # by an earlier one fails the same way.
        print("  Erreur 9 : le module n'a pas répondu à l'entrée en mise à jour. Si c'est le premier")
        print("  essai, son application parle-t-elle le transport de la LinkIt (_Uart/_Spi) ?")
    print(FAILURE_ADVICE)
    return False
