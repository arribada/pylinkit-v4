"""AssistNow Offline almanac download from u-blox services.

Flow: GNSSI -> Build UBX frames -> ZTP register -> Download almanac
     With fallback to direct API if ZTP returns 403.
"""

import json
import logging
from pathlib import Path

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 30

CACHE_DIR = Path("~/.pylinkit").expanduser()
CACHE_FILE = CACHE_DIR / "assistnow_cache.json"

ZTP_URL = "https://api.thingstream.io/ztp/assistnow/credentials"
FALLBACK_URL = "https://offline-live1.services.u-blox.com/GetOfflineData.ashx"


# --- UBX frame building ---

def _ubx_checksum(data: bytes) -> tuple:
    ck_a, ck_b = 0, 0
    for byte in data:
        ck_a = (ck_a + byte) & 0xFF
        ck_b = (ck_b + ck_a) & 0xFF
    return ck_a, ck_b


def _build_ubx_frame(cls: int, msg_id: int, payload: bytes) -> bytes:
    length = len(payload)
    hdr = bytes([cls, msg_id, length & 0xFF, (length >> 8) & 0xFF])
    chk_data = hdr + payload
    ck_a, ck_b = _ubx_checksum(chk_data)
    return b'\xB5\x62' + chk_data + bytes([ck_a, ck_b])


def _build_ubx_sec_uniqid(unique_id: str) -> str:
    uid_bytes = bytes.fromhex(unique_id)
    uid = uid_bytes.ljust(max(5, len(uid_bytes)), b'\x00')
    payload = b'\x02\x00\x00\x00' + uid  # version=2, reserved=0,0,0
    frame = _build_ubx_frame(0x27, 0x03, payload)
    return frame.hex().upper()


def _build_ubx_mon_ver(sw_version: str, hw_version: str) -> str:
    sw = sw_version.encode('ascii')[:30].ljust(30, b'\x00')
    hw = hw_version.encode('ascii')[:10].ljust(10, b'\x00')
    frame = _build_ubx_frame(0x0A, 0x04, sw + hw)
    return frame.hex().upper()


# --- Cache ---

def _load_cache() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


# --- Download ---

def _download_with_chipcode(chipcode: str, service_url: str = FALLBACK_URL) -> bytes:
    """Download almanac using a chipcode."""
    logger.info("Downloading almanac with chipcode=%s from %s", chipcode, service_url)
    result = requests.get(service_url, params={
        "chipcode": chipcode,
        "gnss": "gps,glo,gal",
        "data": "uporb_1,ualm",
    }, timeout=HTTP_TIMEOUT)
    result.raise_for_status()
    logger.info("Almanac downloaded: %d bytes", len(result.content))
    return result.content


def _download_fallback(token: str) -> bytes:
    """Fallback: direct AssistNow Offline API without chipcode."""
    logger.info("Downloading almanac via fallback API (no chipcode)")
    resp = requests.get(FALLBACK_URL, params={
        "token": token,
        "gnss": "gps+glo+gal",
        "period": 4,
        "resolution": 1,
    }, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    logger.info("Fallback almanac downloaded: %d bytes", len(resp.content))
    return resp.content


def download_almanac(token: str, unique_id: str, sw_version: str, hw_version: str,
                     chipcode: str = None) -> tuple:
    """Download AssistNow Offline almanac data from u-blox.

    Flow:
        1. If chipcode provided (from device GNSS_TOKEN) -> download directly
        2. If that fails -> ZTP registration to get a new chipcode
        3. If ZTP returns 403 -> fallback direct API (no chipcode)
        4. If download with new chipcode fails -> fallback direct API

    Returns:
        Tuple of (almanac_bytes, chipcode). chipcode is None if fallback was used.
    """
    # 1. Try with existing chipcode (from device)
    if chipcode:
        try:
            return _download_with_chipcode(chipcode), chipcode
        except RequestException as e:
            logger.warning("Download with existing chipcode failed: %s", e)

    # 2. Try from local cache
    cache_key = f"{token}:{unique_id}"
    cache = _load_cache()

    if cache_key in cache:
        cached_chipcode = cache[cache_key]["chipcode"]
        if cached_chipcode != chipcode:  # skip if same as already-tried chipcode
            service_url = cache[cache_key]["serviceUrl"]
            logger.info("Trying cached chipcode %s", cached_chipcode)
            try:
                return _download_with_chipcode(cached_chipcode, service_url), cached_chipcode
            except RequestException as e:
                logger.warning("Download with cached chipcode failed: %s", e)

    # 3. ZTP registration
    uniq_id_hex = _build_ubx_sec_uniqid(unique_id)
    mon_ver_hex = _build_ubx_mon_ver(sw_version, hw_version)

    logger.info("ZTP registration...")
    try:
        resp = requests.post(ZTP_URL, json={
            "token": token,
            "messages": {
                "UBX-SEC-UNIQID": uniq_id_hex,
                "UBX-MON-VER": mon_ver_hex,
            }
        }, timeout=HTTP_TIMEOUT)

        if resp.status_code == 403:
            logger.warning("ZTP returned 403, using fallback API")
            return _download_fallback(token), None

        resp.raise_for_status()
        data = resp.json()
        new_chipcode = data["chipcode"]
        service_url = data["serviceUrl"]

        cache[cache_key] = {"chipcode": new_chipcode, "serviceUrl": service_url}
        _save_cache(cache)
        logger.info("ZTP OK, chipcode=%s", new_chipcode)

        # 4. Download with new chipcode
        try:
            return _download_with_chipcode(new_chipcode, service_url), new_chipcode
        except RequestException as e:
            logger.warning("Download with new chipcode failed: %s, using fallback", e)
            return _download_fallback(token), new_chipcode

    except RequestException as e:
        logger.warning("ZTP registration failed: %s, using fallback", e)
        return _download_fallback(token), None
