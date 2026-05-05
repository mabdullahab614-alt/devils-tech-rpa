"""Jewelry-grade alloy densities (g/cm3) for mass calculations."""

KARAT_DENSITY_MAP = {
    "24K": 19.32,
    "22K": 17.70,  # default — Pakistan / Lahore regional standard
    "21K": 16.50,
    "18K": 15.58,
    "14K": 13.07,
}


def get_density(karat="22K"):
    karat = karat.upper()
    if karat not in KARAT_DENSITY_MAP:
        raise ValueError(
            "unknown karat '{}' — supported: {}".format(
                karat, sorted(KARAT_DENSITY_MAP)
            )
        )
    return KARAT_DENSITY_MAP[karat]
