ALLE_PARTITIES = [
    "boot_a", "boot_b", "init_boot_a", "init_boot_b",
    "vendor_boot_a", "vendor_boot_b", "dtbo_a", "dtbo_b",
    "vbmeta_a", "vbmeta_b", "vbmeta_system_a", "vbmeta_system_b",
    "vbmeta_vendor_a", "vbmeta_vendor_b",
    "lk_a", "lk_b", "tee_a", "tee_b", "gz_a", "gz_b",
    "scp_a", "scp_b", "sspm_a", "sspm_b", "spmfw_a", "spmfw_b",
    "seccfg", "proinfo", "nvram", "nvdata", "nvcfg",
    "protect1", "protect2", "frp", "persist", "metadata",
    "md_udc", "md1img_a", "md1img_b", "boot_para", "logo",
    "otp", "para", "sec1", "expdb", "flashinfo", "ITEMS",
    "cam_vpu1_a", "cam_vpu1_b", "cam_vpu2_a", "cam_vpu2_b",
    "cam_vpu3_a", "cam_vpu3_b", "super", "userdata",
]

PRELOADER = "preloader_boot1"

UNIEK = [
    "proinfo", "nvram", "nvdata", "nvcfg",
    "protect1", "protect2", "seccfg", "persist",
    "md1img_a", "md1img_b", "md_udc",
]

ESIM_WAARSCHUWING = (
    "Het eSIM-profiel zit in de eUICC van de modem, niet op een partitie die deze "
    "installer schrijft. Zolang je de NV-/modempartities niet terugflasht met die "
    "van een ANDER toestel, blijft je provider werken."
)

SCHRIJFT_BIJ_INSTALL = ["boot_a", "para", "userdata"]

def classificeer(naam):
    if naam in UNIEK:
        return "uniek"
    if naam in SCHRIJFT_BIJ_INSTALL:
        return "wordt-geschreven"
    return "standaard"
