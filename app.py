import io
import re
import struct
import wave
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw

# =============================================================================
# CONFIGURACIÓN DE PÁGINA Y CSS DE ALTO CONTRASTE
# =============================================================================
st.set_page_config(
    page_title="NES Shooter Studio",
    page_icon="🕹️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #f8fafc !important; color: #0f172a !important; }
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 2px solid #cbd5e1 !important; }
    section[data-testid="stSidebar"] * { color: #0f172a !important; }
    h1, h2, h3, h4, p, label, span, div { color: #0f172a; }
    .studio-card {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-left: 5px solid #2563eb !important;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    button[data-baseweb="tab"] {
        background-color: #e2e8f0 !important;
        color: #0f172a !important;
        font-weight: 700 !important;
        border-radius: 6px 6px 0 0 !important;
        margin-right: 4px !important;
        padding: 10px 18px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] * {
        color: #ffffff !important;
    }
    input, textarea, select, [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #94a3b8 !important;
    }
    .stButton > button, .stDownloadButton > button {
        background-color: #2563eb !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 6px !important;
    }
    .stButton > button *, .stDownloadButton > button * {
        color: #ffffff !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background-color: #1d4ed8 !important;
    }
    .asm-viewer {
        background-color: #0f172a !important;
        color: #38bdf8 !important;
        font-family: 'Consolas', 'Courier New', monospace !important;
        font-size: 13.5px !important;
        padding: 14px !important;
        border-radius: 6px !important;
        white-space: pre !important;
        overflow-x: auto !important;
        line-height: 1.45 !important;
    }
    .tv-preview {
        background-color: #090d16 !important;
        color: #f8fafc !important;
        border: 4px solid #334155 !important;
        border-radius: 8px !important;
        padding: 16px !important;
        font-family: 'Consolas', 'Courier New', monospace !important;
        font-size: 14px !important;
        white-space: pre-wrap !important;
        line-height: 1.4 !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CONSTANTES DE HARDWARE NES (PALETA 2C02, MAPPERS, OPCODES 6502)
# =============================================================================
NES_MASTER_PALETTE = np.array([
    [84, 84, 84], [0, 30, 116], [8, 16, 144], [48, 0, 136],
    [68, 0, 100], [92, 0, 48], [84, 4, 0], [60, 24, 0],
    [32, 42, 0], [8, 58, 0], [0, 64, 0], [0, 60, 0],
    [0, 50, 60], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [152, 150, 152], [8, 76, 196], [48, 50, 236], [92, 30, 228],
    [136, 20, 176], [160, 20, 100], [152, 34, 32], [120, 60, 0],
    [84, 90, 0], [40, 114, 0], [8, 124, 0], [0, 118, 40],
    [0, 102, 120], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [236, 238, 236], [76, 154, 236], [120, 124, 236], [176, 98, 236],
    [228, 84, 236], [236, 88, 180], [236, 106, 100], [212, 136, 32],
    [160, 170, 0], [116, 196, 0], [76, 208, 32], [56, 204, 108],
    [56, 180, 204], [60, 60, 60], [0, 0, 0], [0, 0, 0],
    [236, 238, 236], [168, 204, 236], [188, 188, 236], [212, 178, 236],
    [236, 174, 236], [236, 174, 212], [236, 180, 176], [228, 196, 144],
    [204, 210, 120], [180, 222, 120], [168, 226, 144], [152, 226, 180],
    [160, 214, 228], [160, 162, 160], [0, 0, 0], [0, 0, 0]
], dtype=np.uint8)

MAPPER_NAMES = {
    0: "NROM (Estándar 16-32KB PRG)",
    1: "MMC1 (SxROM - Nintendo)",
    2: "UxROM (PRG Switch + CHR-RAM, ej. Castlevania / Contra)",
    3: "CNROM (Cambio de bancos CHR)",
    4: "MMC3 (TxROM - Contador IRQ)",
    7: "AxROM (Single-Screen)",
    9: "MMC2 (PxROM)",
    24: "VRC6 (Konami)",
    66: "GxROM",
}

OPCODES_6502 = {
    0x00: ("BRK", "imp", 1), 0x01: ("ORA", "indx", 2), 0x05: ("ORA", "zp", 2), 0x06: ("ASL", "zp", 2),
    0x08: ("PHP", "imp", 1), 0x09: ("ORA", "imm", 2), 0x0A: ("ASL", "acc", 1), 0x0D: ("ORA", "abs", 3),
    0x0E: ("ASL", "abs", 3), 0x10: ("BPL", "rel", 2), 0x11: ("ORA", "indy", 2), 0x15: ("ORA", "zpx", 2),
    0x16: ("ASL", "zpx", 2), 0x18: ("CLC", "imp", 1), 0x19: ("ORA", "absy", 3), 0x1D: ("ORA", "absx", 3),
    0x1E: ("ASL", "absx", 3), 0x20: ("JSR", "abs", 3), 0x21: ("AND", "indx", 2), 0x24: ("BIT", "zp", 2),
    0x25: ("AND", "zp", 2), 0x26: ("ROL", "zp", 2), 0x28: ("PLP", "imp", 1), 0x29: ("AND", "imm", 2),
    0x2A: ("ROL", "acc", 1), 0x2C: ("BIT", "abs", 3), 0x2D: ("AND", "abs", 3), 0x2E: ("ROL", "abs", 3),
    0x30: ("BMI", "rel", 2), 0x31: ("AND", "indy", 2), 0x35: ("AND", "zpx", 2), 0x36: ("ROL", "zpx", 2),
    0x38: ("SEC", "imp", 1), 0x39: ("AND", "absy", 3), 0x3D: ("AND", "absx", 3), 0x3E: ("ROL", "absx", 3),
    0x40: ("RTI", "imp", 1), 0x41: ("EOR", "indx", 2), 0x45: ("EOR", "zp", 2), 0x46: ("LSR", "zp", 2),
    0x48: ("PHA", "imp", 1), 0x49: ("EOR", "imm", 2), 0x4A: ("LSR", "acc", 1), 0x4C: ("JMP", "abs", 3),
    0x4D: ("EOR", "abs", 3), 0x4E: ("LSR", "abs", 3), 0x50: ("BVC", "rel", 2), 0x51: ("EOR", "indy", 2),
    0x55: ("EOR", "zpx", 2), 0x56: ("LSR", "zpx", 2), 0x58: ("CLI", "imp", 1), 0x59: ("EOR", "absy", 3),
    0x5D: ("EOR", "absx", 3), 0x5E: ("LSR", "absx", 3), 0x60: ("RTS", "imp", 1), 0x61: ("ADC", "indx", 2),
    0x65: ("ADC", "zp", 2), 0x66: ("ROR", "zp", 2), 0x68: ("PLA", "imp", 1), 0x69: ("ADC", "imm", 2),
    0x6A: ("ROR", "acc", 1), 0x6C: ("JMP", "ind", 3), 0x6D: ("ADC", "abs", 3), 0x6E: ("ROR", "abs", 3),
    0x70: ("BVS", "rel", 2), 0x71: ("ADC", "indy", 2), 0x75: ("ADC", "zpx", 2), 0x76: ("ROR", "zpx", 2),
    0x78: ("SEI", "imp", 1), 0x79: ("ADC", "absy", 3), 0x7D: ("ADC", "absx", 3), 0x7E: ("ROR", "absx", 3),
    0x81: ("STA", "indx", 2), 0x84: ("STY", "zp", 2), 0x85: ("STA", "zp", 2), 0x86: ("STX", "zp", 2),
    0x88: ("DEY", "imp", 1), 0x8A: ("TXA", "imp", 1), 0x8C: ("STY", "abs", 3), 0x8D: ("STA", "abs", 3),
    0x8E: ("STX", "abs", 3), 0x90: ("BCC", "rel", 2), 0x91: ("STA", "indy", 2), 0x94: ("STY", "zpx", 2),
    0x95: ("STA", "zpx", 2), 0x96: ("STX", "zpy", 2), 0x98: ("TYA", "imp", 1), 0x99: ("STA", "absy", 3),
    0x9A: ("TXS", "imp", 1), 0x9D: ("STA", "absx", 3), 0xA0: ("LDY", "imm", 2), 0xA1: ("LDA", "indx", 2),
    0xA2: ("LDX", "imm", 2), 0xA4: ("LDY", "zp", 2), 0xA5: ("LDA", "zp", 2), 0xA6: ("LDX", "zp", 2),
    0xA8: ("TAY", "imp", 1), 0xA9: ("LDA", "imm", 2), 0xAA: ("TAX", "imp", 1), 0xAC: ("LDY", "abs", 3),
    0xAD: ("LDA", "abs", 3), 0xAE: ("LDX", "abs", 3), 0xB0: ("BCS", "rel", 2), 0xB1: ("LDA", "indy", 2),
    0xB4: ("LDY", "zpx", 2), 0xB5: ("LDA", "zpx", 2), 0xB6: ("LDX", "zpy", 2), 0xB8: ("CLV", "imp", 1),
    0xB9: ("LDA", "absy", 3), 0xBA: ("TSX", "imp", 1), 0xBC: ("LDY", "absx", 3), 0xBD: ("LDA", "absx", 3),
    0xBE: ("LDX", "absy", 3), 0xC0: ("CPY", "imm", 2), 0xC1: ("CMP", "indx", 2), 0xC4: ("CPY", "zp", 2),
    0xC5: ("CMP", "zp", 2), 0xC6: ("DEC", "zp", 2), 0xC8: ("INY", "imp", 1), 0xC9: ("CMP", "imm", 2),
    0xCA: ("DEX", "imp", 1), 0xCC: ("CPY", "abs", 3), 0xCD: ("CMP", "abs", 3), 0xCE: ("DEC", "abs", 3),
    0xD0: ("BNE", "rel", 2), 0xD1: ("CMP", "indy", 2), 0xD5: ("CMP", "zpx", 2), 0xD6: ("DEC", "zpx", 2),
    0xD8: ("CLD", "imp", 1), 0xD9: ("CMP", "absy", 3), 0xDD: ("CMP", "absx", 3), 0xDE: ("DEC", "absx", 3),
    0xE0: ("CPX", "imm", 2), 0xE1: ("SBC", "indx", 2), 0xE4: ("CPX", "zp", 2), 0xE5: ("SBC", "zp", 2),
    0xE6: ("INC", "zp", 2), 0xE8: ("INX", "imp", 1), 0xE9: ("SBC", "imm", 2), 0xEA: ("NOP", "imp", 1),
    0xEC: ("CPX", "abs", 3), 0xED: ("SBC", "abs", 3), 0xEE: ("INC", "abs", 3), 0xF0: ("BEQ", "rel", 2),
    0xF1: ("SBC", "indy", 2), 0xF5: ("SBC", "zpx", 2), 0xF6: ("INC", "zpx", 2), 0xF8: ("SED", "imp", 1),
    0xF9: ("SBC", "absy", 3), 0xFD: ("SBC", "absx", 3), 0xFE: ("INC", "absx", 3),
}

NOTE_NAMES = [
    "Silencio (---)", "E-3", "G-3", "A-3", "B-3", "C-4", "D-4", "D#4", "E-4",
    "F#4", "G-4", "G#4", "A-4", "B-4", "C-5", "C#5", "D-5", "E-5",
    "F-5", "F#5", "G-5", "G#5", "A-5", "B-5"
]
NOTE_TO_IDX = {n: i for i, n in enumerate(NOTE_NAMES)}
DRUM_NAMES = ["Silencio (---)", "Bombo (DUM)", "Caja (CLAP)", "Platillo (TS)"]
DRUM_TO_IDX = {n: i for i, n in enumerate(DRUM_NAMES)}

DEFAULT_NOTE_LO = [0x00,0xA6,0x3A,0xFB,0xC4,0xAB,0x7C,0x67,0x52,0x2D,0x1C,0xFD,0xE1,0xD5,0xBD,0xB3,0xA9,0x96,0x8E,0x7E,0x70,0x6A,0x5E,0x54]
DEFAULT_NOTE_HI = [0x00,0x02,0x02,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]


def nes_rgb(idx):
    return tuple(int(x) for x in NES_MASTER_PALETTE[idx & 0x3F])


def rgb_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


# =============================================================================
# ESTADO DE LA SESIÓN
# =============================================================================
def init_state():
    if "initialized" in st.session_state:
        return
    st.session_state.initialized = True
    st.session_state.has_nes = False
    st.session_state.has_asm = False
    st.session_state.nes_name = ""
    st.session_state.asm_name = ""
    st.session_state.asm_text = ""

    st.session_state.header = bytearray()
    st.session_state.prg_data = bytearray()
    st.session_state.chr_data = bytearray()
    st.session_state.chr_source_info = ""
    st.session_state.palette = [
        0x0F, 0x00, 0x0C, 0x18, 0x0F, 0x01, 0x02, 0x12,
        0x0F, 0x16, 0x27, 0x38, 0x0F, 0x30, 0x00, 0x10,
        0x0F, 0x2C, 0x38, 0x11, 0x0F, 0x0C, 0x24, 0x38,
        0x0F, 0x2A, 0x38, 0x30, 0x0F, 0x30, 0x16, 0x27
    ]

    st.session_state.rom_texts = []
    st.session_state.asm_strings = []
    st.session_state.asm_tables = {}
    st.session_state.songs = {}
    st.session_state.note_lo = list(DEFAULT_NOTE_LO)
    st.session_state.note_hi = list(DEFAULT_NOTE_HI)


# =============================================================================
# EXTRACTOR DE GRÁFICOS CHR-RAM Y DESCOMPRESOR KONAMI RLE (EJ. CASTLEVANIA)
# =============================================================================
def extract_chr_ram_from_prg(prg: bytearray) -> tuple[bytearray, str]:
    n = len(prg)
    rle_chunks = bytearray()
    i = 0

    while i < n - 32 and len(rle_chunks) < 65536:
        out = bytearray()
        pos = i
        valid = True
        steps = 0
        while pos < n and len(out) < 8192 and steps < 1200:
            cmd = prg[pos]
            pos += 1
            steps += 1
            if cmd == 0xFF:
                break
            elif cmd & 0x80:
                cnt = cmd & 0x7F
                if pos >= n or cnt == 0:
                    valid = False
                    break
                out.extend([prg[pos]] * cnt)
                pos += 1
            else:
                cnt = cmd & 0x7F
                if pos + cnt > n or cnt == 0:
                    valid = False
                    break
                out.extend(prg[pos:pos + cnt])
                pos += cnt

        if valid and len(out) >= 512 and (len(out) % 16 == 0) and pos <= n and prg[pos - 1] == 0xFF:
            non_trivial = sum(1 for b in out if b not in (0x00, 0xFF))
            if non_trivial > len(out) // 6:
                rle_chunks.extend(out)
                i = pos
                continue
        i += 32

    if len(rle_chunks) >= 4096:
        pad = (8192 - (len(rle_chunks) % 8192)) % 8192
        rle_chunks.extend(b"\x00" * pad)
        return rle_chunks, f"CHR-RAM Descomprimido (Konami RLE + PRG: {len(rle_chunks)//8192} bancos de 8KB)"

    extracted = bytearray()
    for b_ofs in range(0, len(prg), 8192):
        chunk = prg[b_ofs:b_ofs + 8192]
        if len(chunk) == 8192:
            extracted.extend(chunk)
    return extracted[:65536], f"CHR-RAM Mapeado desde Bancos PRG ({len(extracted)//8192} bancos)"


# =============================================================================
# ESCÁNER UNIVERSAL DE TEXTOS (SOPORTA PPU PRINT, ASCII Y TABLAS DESPLAZADAS)
# =============================================================================
def extract_all_rom_texts(prg: bytearray):
    entries = []
    used_ranges = []
    num_banks = max(1, len(prg) // 16384)

    def ofs_to_addr_str(ofs):
        b_id = ofs // 16384
        cpu_a = (0xC000 + (ofs & 0x3FFF)) if (num_banks == 1 or b_id == num_banks - 1) else (0x8000 + (ofs & 0x3FFF))
        return f"B{b_id}:${cpu_a:04X}" if num_banks > 1 else f"${cpu_a:04X}"

    # 1. Macros PPU_PRINT: (A9 XX 8D 07 20){2,}
    ppu_pat = re.compile(rb"(?:\xA9[\x20-\x7E]\x8D\x07\x20){2,}")
    for m in ppu_pat.finditer(bytes(prg)):
        raw = m.group(0)
        txt = "".join(chr(raw[i + 1]) for i in range(0, len(raw), 5))
        s = m.start()
        entries.append({
            "ID": f"PPU_{len(entries):02d}",
            "Tipo": "Macro PRINT (PPU $2007)",
            "Direccion": ofs_to_addr_str(s),
            "Texto": txt,
            "Max_Chars": len(txt),
            "_offset": s,
            "_mode": "ppu",
            "_shift": 0,
        })
        used_ranges.append((s, m.end()))

    # 2. Cadenas ASCII estándar en cualquier banco PRG
    ascii_pat = re.compile(rb"[\x20-\x7E]{5,}")
    for m in ascii_pat.finditer(bytes(prg)):
        s, e = m.start(), m.end()
        if any(not (e <= us or s >= ue) for us, ue in used_ranges):
            continue
        raw = m.group(0)
        letters = sum(1 for b in raw if (65 <= b <= 90) or (97 <= b <= 122))
        if letters < 4:
            continue
        txt_full = raw.decode("ascii", errors="ignore")
        weird = sum(1 for c in txt_full if c in "{}[]|~`^\\@$%&*+=<>?;:")
        if weird > len(txt_full) // 5:
            continue

        if len(txt_full) >= 52 and len(txt_full) % 26 == 0:
            for idx_l in range(len(txt_full) // 26):
                sub_ofs = s + idx_l * 26
                entries.append({
                    "ID": f"HISTORIA_L{idx_l:02d}",
                    "Tipo": "Línea de Historia (26 cols)",
                    "Direccion": ofs_to_addr_str(sub_ofs),
                    "Texto": txt_full[idx_l * 26:(idx_l + 1) * 26],
                    "Max_Chars": 26,
                    "_offset": sub_ofs,
                    "_mode": "raw",
                    "_shift": 0,
                })
        else:
            entries.append({
                "ID": f"TXT_{len(entries):02d}",
                "Tipo": "Cadena ASCII (.byte)",
                "Direccion": ofs_to_addr_str(s),
                "Texto": txt_full[:64],
                "Max_Chars": min(64, len(txt_full)),
                "_offset": s,
                "_mode": "raw",
                "_shift": 0,
            })
        used_ranges.append((s, e))

    # 3. Escáner de Textos Codificados por Tabla (ej. Castlevania, Konami, Nintendo)
    # Todas las palabras clave tienen al menos 5 letras para garantizar >= 4 diferencias
    common_words = [
        b"SCORE", b"STAGE", b"PLAYER", b"START", b"GAME ",
        b"OVER ", b"KONAMI", b"CASTLE", b"VAMPIRE", b"PRODUCE",
        b"DIRECT", b"THANK", b"PLAYING", b"HERO "
    ]
    prg_arr = np.frombuffer(prg, dtype=np.uint8).astype(np.int16)
    diffs = np.diff(prg_arr)
    n_diffs = len(diffs)

    for word in common_words:
        w_diffs = np.diff(np.frombuffer(word, dtype=np.uint8).astype(np.int16))
        k = len(w_diffs)
        if k < 4 or n_diffs < k:
            continue

        cond = np.ones(n_diffs - k + 1, dtype=bool)
        for j in range(k):
            cond &= (diffs[j:n_diffs - k + 1 + j] == w_diffs[j])

        matches = np.where(cond)[0]
        for pos in matches[:10]:
            pos = int(pos)
            if any(us <= pos < ue for us, ue in used_ranges):
                continue
            shift = int(prg[pos]) - word[0]
            if shift == 0:
                continue

            start_p = pos
            while start_p > 0 and 32 <= (int(prg[start_p - 1]) - shift) <= 122 and (pos - start_p) < 40:
                start_p -= 1
            end_p = pos + len(word)
            while end_p < len(prg) and 32 <= (int(prg[end_p]) - shift) <= 122 and (end_p - start_p) < 64:
                end_p += 1

            if end_p - start_p >= 5:
                decoded = "".join(chr(max(32, min(126, int(b) - shift))) for b in prg[start_p:end_p])
                entries.append({
                    "ID": f"TBL_{len(entries):02d}",
                    "Tipo": f"Tabla NES (Shift {shift:+d})",
                    "Direccion": ofs_to_addr_str(start_p),
                    "Texto": decoded,
                    "Max_Chars": end_p - start_p,
                    "_offset": start_p,
                    "_mode": "shifted",
                    "_shift": shift,
                })
                used_ranges.append((start_p, end_p))

    return entries[:120]


# =============================================================================
# ESCÁNER UNIVERSAL DE CANCIONES CHIPTUNE EN ROM (.NES)
# =============================================================================
def extract_all_rom_songs(prg: bytearray):
    songs = {}
    num_banks = max(1, len(prg) // 16384)

    # 1. Detector para SHOOTER v1.13 / Homebrew con tabla de notas de 24 elementos
    for m in re.finditer(rb"[\xBD\xB9](..)\x8D[\x02\x06\x0A]\x40", bytes(prg), re.DOTALL):
        addr = m.group(1)[0] | (m.group(1)[1] << 8)
        ofs = addr - (0xC000 if len(prg) == 16384 else 0x8000)
        if 0 <= ofs <= len(prg) - 48 and prg[ofs] == 0x00 and prg[ofs + 1] in (0xA6, 0x57, 0xFB):
            st.session_state.note_lo = list(prg[ofs:ofs + 24])
            st.session_state.note_hi = list(prg[ofs + 24:ofs + 48])
            p_end = ofs + 48

            if p_end + 36 + 768 + 16 <= len(prg):
                s_order = list(prg[p_end:p_end + 36])
                if all(0 <= x <= 15 for x in s_order) and len(set(s_order)) >= 4:
                    b_mel = p_end + 36
                    b_harm = b_mel + 256
                    b_bass = b_harm + 256
                    b_drum = b_bass + 256
                    songs["1. Tema Principal (Italo-Disco Completo)"] = {
                        "tempo": 6,
                        "song_order": s_order,
                        "mel": list(prg[b_mel:b_mel + 256]),
                        "harm": list(prg[b_harm:b_harm + 256]),
                        "bass": list(prg[b_bass:b_bass + 256]),
                        "drum": list(prg[b_drum:b_drum + 16]),
                        "offsets": {"mel": b_mel, "harm": b_harm, "bass": b_bass, "drum": b_drum, "order": p_end},
                    }
                    s_ofs = b_drum + 16
                    if s_ofs + 112 <= len(prg):
                        songs["2. Tema de Historia (10s Synth-Pop)"] = {
                            "tempo": 12,
                            "mel": list(prg[s_ofs:s_ofs + 32]),
                            "harm": list(prg[s_ofs + 32:s_ofs + 64]),
                            "bass": list(prg[s_ofs + 64:s_ofs + 96]),
                            "drum": list(prg[s_ofs + 96:s_ofs + 112]),
                            "offsets": {"mel": s_ofs, "harm": s_ofs + 32, "bass": s_ofs + 64, "drum": s_ofs + 96},
                        }
                    sel_ofs = s_ofs + 112
                    if sel_ofs + 112 <= len(prg):
                        songs["3. Tema Selección de Nave"] = {
                            "tempo": 7,
                            "mel": list(prg[sel_ofs:sel_ofs + 32]),
                            "harm": list(prg[sel_ofs + 32:sel_ofs + 64]),
                            "bass": list(prg[sel_ofs + 64:sel_ofs + 96]),
                            "drum": list(prg[sel_ofs + 96:sel_ofs + 112]),
                            "offsets": {"mel": sel_ofs, "harm": sel_ofs + 32, "bass": sel_ofs + 64, "drum": sel_ofs + 96},
                        }
                    go_ofs = sel_ofs + 112
                    if go_ofs + 8 <= len(prg):
                        songs["4. Tonada de Game Over"] = {
                            "tempo": 10,
                            "mel": list(prg[go_ofs:go_ofs + 8]),
                            "harm": [0] * 8,
                            "bass": list(prg[go_ofs:go_ofs + 8]),
                            "drum": [0] * 8,
                            "offsets": {"mel": go_ofs},
                        }
            break

    # 2. Detector de Jingles directos en $4002 (funciona con shooter.nes original y shooterv1.13.nes)
    for m in re.finditer(rb"\xBD(..)\x8D\x02\x40", bytes(prg), re.DOTALL):
        j_addr = m.group(1)[0] | (m.group(1)[1] << 8)
        j_ofs = j_addr - (0xC000 if len(prg) == 16384 else 0x8000)
        if 0 <= j_ofs <= len(prg) - 6:
            periods = list(prg[j_ofs:j_ofs + 6])
            if all(0x20 <= p <= 0xF5 for p in periods):
                songs[f"Jingle Código Secreto / Pausa (${j_addr:04X})"] = {
                    "tempo": 6,
                    "raw_periods": periods,
                    "mel": [8, 11, 13, 16, 18, 20],
                    "harm": [0] * 6,
                    "bass": [0] * 6,
                    "drum": [0] * 6,
                    "offsets": {"raw_periods": j_ofs},
                }
                break

    # 3. Detector Universal para ROMs comerciales (Castlevania, Konami, Capcom, Nintendo)
    if not songs:
        for b_idx in range(num_banks):
            b_start = b_idx * 16384
            bank = prg[b_start:b_start + 16384]
            ptr_pos = 0
            while ptr_pos < len(bank) - 32 and len(songs) < 16:
                ptrs = [bank[ptr_pos + k * 2] | (bank[ptr_pos + k * 2 + 1] << 8) for k in range(8)]
                if all(0x8000 <= p <= 0xBFFF for p in ptrs) and len(set(ptrs)) >= 5:
                    valid_streams = 0
                    for p in ptrs[:6]:
                        rel = p - 0x8000
                        if 0 <= rel < len(bank) - 32:
                            stream = bank[rel:rel + 32]
                            if any(0x10 <= x <= 0x7F for x in stream):
                                valid_streams += 1
                    if valid_streams >= 5:
                        for s_i in range(14):
                            if ptr_pos + s_i * 2 + 2 > len(bank) or len(songs) >= 16:
                                break
                            p_val = bank[ptr_pos + s_i * 2] | (bank[ptr_pos + s_i * 2 + 1] << 8)
                            if not (0x8000 <= p_val <= 0xBFFF):
                                break
                            rel = p_val - 0x8000
                            if 0 <= rel < len(bank) - 48:
                                raw_stm = bank[rel:rel + 64]
                                mel_steps, harm_steps, bass_steps = [], [], []
                                for b_val in raw_stm:
                                    if b_val == 0xFF:
                                        break
                                    if b_val < 0x80:
                                        note_n = ((b_val & 0x3F) % 22) + 1 if (b_val & 0x3F) > 0 else 0
                                        mel_steps.append(note_n)
                                        harm_steps.append(max(0, note_n - 5) if note_n > 5 else 0)
                                        bass_steps.append(((note_n - 1) % 10) + 1 if note_n > 0 else 0)
                                if len(mel_steps) >= 8:
                                    pad_len = max(16, min(64, (len(mel_steps) // 16 + 1) * 16))
                                    mel_steps = (mel_steps + [0] * pad_len)[:pad_len]
                                    harm_steps = (harm_steps + [0] * pad_len)[:pad_len]
                                    bass_steps = (bass_steps + [0] * pad_len)[:pad_len]
                                    songs[f"Pista #{len(songs)+1:02d} (Banco {b_idx} @ ${p_val:04X})"] = {
                                        "tempo": 6,
                                        "mel": mel_steps,
                                        "harm": harm_steps,
                                        "bass": bass_steps,
                                        "drum": [1, 0, 3, 0, 2, 0, 3, 0, 1, 0, 3, 0, 2, 0, 3, 3],
                                        "offsets": {},
                                    }
                        ptr_pos += 32
                        continue
                ptr_pos += 2

    return songs


# =============================================================================
# CARGADORES PRINCIPALES DE ARCHIVOS (.NES Y .S)
# =============================================================================
def analyze_nes_file(data: bytearray, filename: str):
    if len(data) < 16 or data[:4] != b"NES\x1a":
        st.error("❌ El archivo seleccionado no tiene una cabecera iNES válida ('NES\\x1A').")
        return

    st.session_state.has_nes = True
    st.session_state.nes_name = filename
    st.session_state.header = data[:16]

    prg_banks = data[4]
    chr_banks = data[5]
    has_trainer = bool(data[6] & 0x04)
    offset = 16 + (512 if has_trainer else 0)
    prg_size = prg_banks * 16384
    chr_size = chr_banks * 8192

    st.session_state.prg_data = bytearray(data[offset:offset + prg_size])
    prg = st.session_state.prg_data

    if chr_size > 0 and len(data) >= offset + prg_size + chr_size:
        st.session_state.chr_data = bytearray(data[offset + prg_size:offset + prg_size + chr_size])
        st.session_state.chr_source_info = f"CHR-ROM Dedicado ({chr_banks} bancos de 8 KB)"
    else:
        chr_extracted, info_str = extract_chr_ram_from_prg(prg)
        st.session_state.chr_data = chr_extracted
        st.session_state.chr_source_info = info_str

    for i in range(len(prg) - 32):
        if prg[i] == 0x0F and prg[i + 4] == 0x0F and prg[i + 8] == 0x0F and prg[i + 12] == 0x0F:
            cand = list(prg[i:i + 32])
            if all(b <= 0x3F for b in cand) and len(set(cand)) >= 6:
                st.session_state.palette = cand
                break

    st.session_state.rom_texts = extract_all_rom_texts(prg)
    st.session_state.songs = extract_all_rom_songs(prg)


def analyze_asm_file(text: str, filename: str):
    st.session_state.has_asm = True
    st.session_state.asm_name = filename
    st.session_state.asm_text = text

    strings = []
    for m in re.finditer(r'(PRINT\s+\$[0-9A-Fa-f]+,\s*"|[A-Za-z0-9_]+:\s*\.byte\s+"|\.asciiz\s+")([^"]*)(")', text):
        strings.append({
            "Identificador": m.group(1).strip().rstrip('"'),
            "Texto": m.group(2),
            "Caracteres": len(m.group(2)),
            "_raw_prefix": m.group(1)
        })
    st.session_state.asm_strings = strings

    tables = {}
    for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*):\s*\n?((?:\s*\.byte\s+[^\n]+\n?)+)", text, re.MULTILINE):
        lbl = m.group(1)
        body = m.group(2)
        if '"' in body:
            continue
        vals = []
        for tok in re.findall(r"\$[0-9A-Fa-f]+|\b\d+\b", body):
            vals.append(int(tok[1:], 16) if tok.startswith("$") else int(tok))
        if vals:
            tables[lbl] = vals
    st.session_state.asm_tables = tables

    if "palette" in tables and len(tables["palette"]) >= 32:
        st.session_state.palette = tables["palette"][:32]
    if "note_lo" in tables and "note_hi" in tables:
        st.session_state.note_lo = tables["note_lo"]
        st.session_state.note_hi = tables["note_hi"]

    songs = {}
    if "bgm_mel" in tables:
        songs["1. Tema Principal (Archivo .s)"] = {
            "tempo": 6,
            "song_order": tables.get("song_order", list(range(16))),
            "mel": tables.get("bgm_mel", [0] * 64),
            "harm": tables.get("bgm_harm", [0] * 64),
            "bass": tables.get("bgm_bass", [0] * 64),
            "drum": tables.get("bgm_drum", [0] * 16),
            "labels": ("bgm_mel", "bgm_harm", "bgm_bass", "bgm_drum"),
        }
    if "susp_mel" in tables:
        songs["2. Tema de Historia (Archivo .s)"] = {
            "tempo": 12,
            "mel": tables.get("susp_mel", [0] * 32),
            "harm": tables.get("susp_pad", [0] * 32),
            "bass": tables.get("susp_bass", [0] * 32),
            "drum": tables.get("susp_drum", [0] * 16),
            "labels": ("susp_mel", "susp_pad", "susp_bass", "susp_drum"),
        }
    if "sel_mel" in tables:
        songs["3. Tema Selección de Nave (Archivo .s)"] = {
            "tempo": 7,
            "mel": tables.get("sel_mel", [0] * 32),
            "harm": tables.get("sel_pad", [0] * 32),
            "bass": tables.get("sel_bass", [0] * 32),
            "drum": tables.get("sel_drum", [0] * 16),
            "labels": ("sel_mel", "sel_pad", "sel_bass", "sel_drum"),
        }
    if "go_notes" in tables:
        songs["4. Tonada de Game Over (Archivo .s)"] = {
            "tempo": 10,
            "mel": tables["go_notes"],
            "harm": [0] * len(tables["go_notes"]),
            "bass": list(tables["go_notes"]),
            "drum": [0] * 8,
            "labels": ("go_notes", None, None, None),
        }
    if "jng_notes" in tables:
        songs["5. Jingle Código Konami (Archivo .s)"] = {
            "tempo": 5,
            "raw_periods": tables["jng_notes"],
            "mel": [8, 11, 13, 16, 18, 20],
            "harm": [0] * 6,
            "bass": [0] * 6,
            "drum": [0] * 6,
            "labels": (None, None, None, None),
        }

    st.session_state.songs = songs


# =============================================================================
# RENDERIZADO ULTRARRÁPIDO VECTORIZADO CON NUMPY
# =============================================================================
def get_tile_matrix(bank_idx: int, table_idx: int, tile_id: int):
    offset = (bank_idx * 8192) + (table_idx * 4096) + (tile_id * 16)
    chr_d = st.session_state.chr_data
    if offset + 16 > len(chr_d):
        return [[0] * 8 for _ in range(8)]
    raw = np.frombuffer(chr_d[offset:offset + 16], dtype=np.uint8)
    bp0 = np.unpackbits(raw[:8]).reshape(8, 8)
    bp1 = np.unpackbits(raw[8:16]).reshape(8, 8)
    return (bp0 | (bp1 << 1)).tolist()


def set_tile_matrix(bank_idx: int, table_idx: int, tile_id: int, mat):
    offset = (bank_idx * 8192) + (table_idx * 4096) + (tile_id * 16)
    if offset + 16 > len(st.session_state.chr_data):
        return
    arr = np.array(mat, dtype=np.uint8) & 3
    bp0 = np.packbits(arr & 1, axis=1).flatten()
    bp1 = np.packbits((arr >> 1) & 1, axis=1).flatten()
    st.session_state.chr_data[offset:offset + 8] = bytearray(bp0)
    st.session_state.chr_data[offset + 8:offset + 16] = bytearray(bp1)


def render_chr_sheet_fast(bank_idx: int, table_idx: int, pal_group: int, selected_tile: int):
    offset = (bank_idx * 8192) + (table_idx * 4096)
    chr_d = st.session_state.chr_data
    chunk = chr_d[offset:offset + 4096]
    if len(chunk) < 4096:
        chunk = chunk + bytearray(4096 - len(chunk))

    raw = np.frombuffer(chunk, dtype=np.uint8).reshape(256, 2, 8)
    bits = np.unpackbits(raw, axis=2).reshape(256, 2, 8, 8)
    pixels = bits[:, 0, :, :] | (bits[:, 1, :, :] << 1)
    grid = pixels.reshape(16, 16, 8, 8).transpose(0, 2, 1, 3).reshape(128, 128)

    sub_pal = np.array([NES_MASTER_PALETTE[st.session_state.palette[pal_group * 4 + c] & 0x3F] for c in range(4)], dtype=np.uint8)
    rgb_img = sub_pal[grid]
    img = Image.fromarray(rgb_img, "RGB").resize((384, 384), Image.NEAREST)

    draw = ImageDraw.Draw(img)
    sx = (selected_tile % 16) * 24
    sy = (selected_tile // 16) * 24
    draw.rectangle([sx, sy, sx + 23, sy + 23], outline=(37, 99, 235), width=3)
    return img


def render_metasprite(bank_idx: int, table_idx: int, tl: int, tr: int, bl: int, br: int, mirror_right: bool, pal_group: int):
    sub_pal = [nes_rgb(st.session_state.palette[pal_group * 4 + c]) for c in range(4)]
    img = Image.new("RGB", (16, 16), sub_pal[0])
    px = img.load()
    quads = [(0, 0, tl, False), (8, 0, tr, mirror_right), (0, 8, bl, False), (8, 8, br, mirror_right)]
    for qx, qy, t_id, fl in quads:
        mat = get_tile_matrix(bank_idx, table_idx, t_id)
        for y in range(8):
            for x in range(8):
                sx = (7 - x) if fl else x
                px[qx + x, qy + y] = sub_pal[mat[y][sx]]
    return img.resize((160, 160), Image.NEAREST)


# =============================================================================
# SINTETIZADOR 2A03 ULTRARRÁPIDO CON NUMPY
# =============================================================================
def synthesize_song_wav_fast(song_dict: dict) -> bytes:
    sample_rate = 22050
    step_frames = int(song_dict.get("tempo", 6))
    samples_per_step = int(sample_rate * (step_frames / 60.0))

    n_lo = st.session_state.note_lo
    n_hi = st.session_state.note_hi

    if "raw_periods" in song_dict:
        periods = song_dict["raw_periods"]
        chunks = []
        t = np.arange(samples_per_step, dtype=np.float32) / sample_rate
        for p in periods:
            freq = 1789773.0 / (16.0 * (p + 1))
            wave_p1 = np.where((t * freq) % 1.0 < 0.5, 0.35, -0.35)
            chunks.append(wave_p1)
        audio = np.concatenate(chunks) if chunks else np.zeros(sample_rate, dtype=np.float32)
        pcm = np.clip(audio * 30000, -32767, 32767).astype(np.int16).tobytes()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)
        return buf.getvalue()

    if "song_order" in song_dict and len(song_dict["mel"]) >= 256:
        mel, harm, bass = [], [], []
        for pat in song_dict["song_order"]:
            p_ofs = (pat & 0x0F) * 16
            mel.extend(song_dict["mel"][p_ofs:p_ofs + 16])
            harm.extend(song_dict["harm"][p_ofs:p_ofs + 16])
            bass.extend(song_dict["bass"][p_ofs:p_ofs + 16])
    else:
        mel = song_dict["mel"]
        harm = song_dict["harm"]
        bass = song_dict["bass"]

    drum = song_dict["drum"]

    def note_freq(n_idx, is_triangle=False):
        if n_idx <= 0 or n_idx >= len(n_lo):
            return 0.0
        period = (n_hi[n_idx] << 8) | n_lo[n_idx]
        if period <= 0:
            return 0.0
        div = 32.0 if is_triangle else 16.0
        return 1789773.0 / (div * (period + 1))

    t = np.arange(samples_per_step, dtype=np.float32) / sample_rate
    env = np.maximum(0.30, 1.0 - (np.arange(samples_per_step, dtype=np.float32) / samples_per_step) * 0.60)
    half_idx = samples_per_step // 2
    step_env_mel = np.ones(samples_per_step, dtype=np.float32)
    step_env_mel[half_idx:] = 0.68

    kick_len = min(samples_per_step, int(sample_rate * 0.045))
    snare_len = min(samples_per_step, int(sample_rate * 0.045))
    hat_len = min(samples_per_step, int(sample_rate * 0.020))
    rng = np.random.default_rng(1985)
    noise_arr = rng.choice([-1.0, 1.0], size=samples_per_step).astype(np.float32)

    chunks = []
    for s in range(len(mel)):
        m_note = mel[s]
        h_note = harm[s] if s < len(harm) else 0
        b_note = bass[s] if s < len(bass) else 0
        d_hit = drum[s % len(drum)] if drum else 0

        sig = np.zeros(samples_per_step, dtype=np.float32)

        if m_note > 0:
            f1 = note_freq(m_note, False)
            sig += np.where((t * f1) % 1.0 < 0.25, 0.24, -0.24) * step_env_mel
            if h_note > 0:
                f2 = note_freq(h_note, False)
                sig += np.where((t * f2) % 1.0 < 0.50, 0.12, -0.12) * env
        elif h_note > 0:
            fh = note_freq(h_note, False)
            sig += np.where((t * fh) % 1.0 < 0.50, 0.18, -0.18) * env

        if b_note > 0:
            ft = note_freq(b_note, True)
            ph = (t * ft) % 1.0
            tri = np.where(ph < 0.5, 4.0 * ph - 1.0, 3.0 - 4.0 * ph)
            sig += tri * 0.30

        if d_hit == 1:
            kt = t[:kick_len]
            k_env = np.linspace(1.0, 0.0, kick_len, dtype=np.float32)
            sig[:kick_len] += np.sin(2.0 * np.pi * (115.0 - kt * 1200.0) * kt) * 0.38 * k_env
        elif d_hit == 2:
            s_env = np.linspace(1.0, 0.0, snare_len, dtype=np.float32)
            sig[:snare_len] += noise_arr[:snare_len] * 0.24 * s_env
        elif d_hit == 3:
            h_env = np.linspace(1.0, 0.0, hat_len, dtype=np.float32)
            sig[:hat_len] += noise_arr[:hat_len] * 0.14 * h_env

        chunks.append(sig)

    full_audio = np.concatenate(chunks) if chunks else np.zeros(sample_rate, dtype=np.float32)
    pcm = np.clip(full_audio * 30000.0, -32767, 32767).astype(np.int16).tobytes()

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def disassemble_6502(prg_bytes: bytes, bank_idx: int, start_offset: int, num_lines: int = 40):
    bank_size = 16384
    base_rom = bank_idx * bank_size
    num_b = max(1, len(prg_bytes) // 16384)
    cpu_base = 0xC000 if (num_b == 1 or bank_idx == num_b - 1) else 0x8000
    pc = start_offset
    lines = []

    for _ in range(num_lines):
        rom_pos = base_rom + pc
        if rom_pos >= len(prg_bytes) or pc >= bank_size:
            break
        op = prg_bytes[rom_pos]
        cpu_addr = cpu_base + pc
        mnem, mode, size = OPCODES_6502.get(op, (".BYTE", "raw", 1))
        raw_chunk = prg_bytes[rom_pos:min(len(prg_bytes), rom_pos + size)]
        hex_str = " ".join(f"{b:02X}" for b in raw_chunk)

        if mode == "raw" or len(raw_chunk) < size:
            operand, size = f"${op:02X}", 1
        elif mode == "imp":
            operand = ""
        elif mode == "acc":
            operand = "A"
        elif mode == "imm":
            operand = f"#${raw_chunk[1]:02X}"
        elif mode == "zp":
            operand = f"${raw_chunk[1]:02X}"
        elif mode == "zpx":
            operand = f"${raw_chunk[1]:02X},X"
        elif mode == "zpy":
            operand = f"${raw_chunk[1]:02X},Y"
        elif mode == "indx":
            operand = f"(${raw_chunk[1]:02X},X)"
        elif mode == "indy":
            operand = f"(${raw_chunk[1]:02X}),Y"
        elif mode == "abs":
            operand = f"${raw_chunk[1] | (raw_chunk[2] << 8):04X}"
        elif mode == "absx":
            operand = f"${raw_chunk[1] | (raw_chunk[2] << 8):04X},X"
        elif mode == "absy":
            operand = f"${raw_chunk[1] | (raw_chunk[2] << 8):04X},Y"
        elif mode == "ind":
            operand = f"(${raw_chunk[1] | (raw_chunk[2] << 8):04X})"
        elif mode == "rel":
            signed_ofs = raw_chunk[1] - 256 if raw_chunk[1] >= 128 else raw_chunk[1]
            operand = f"${(cpu_addr + 2 + signed_ofs) & 0xFFFF:04X}"
        else:
            operand = ""

        lines.append(f"${cpu_addr:04X}   {hex_str:<8s}   {mnem:<4s} {operand}")
        pc += size
    return "\n".join(lines)


def build_updated_nes() -> bytes:
    hdr = bytearray(st.session_state.header)
    prg = st.session_state.prg_data
    chr_d = st.session_state.chr_data
    if len(hdr) >= 6 and hdr[5] > 0:
        return bytes(hdr + prg + chr_d)
    return bytes(hdr + prg)


def build_updated_asm() -> bytes:
    text = st.session_state.asm_text
    for item in st.session_state.asm_strings:
        pref_esc = re.escape(item["_raw_prefix"])
        new_txt = item["Texto"]
        text = re.sub(rf'({pref_esc})[^"]*(")', rf'\g<1>{new_txt}\g<2>', text, count=1)

    st.session_state.asm_tables["palette"] = st.session_state.palette
    for s_data in st.session_state.songs.values():
        lbls = s_data.get("labels")
        if lbls:
            if lbls[0]:
                st.session_state.asm_tables[lbls[0]] = s_data["mel"]
            if lbls[1]:
                st.session_state.asm_tables[lbls[1]] = s_data["harm"]
            if lbls[2]:
                st.session_state.asm_tables[lbls[2]] = s_data["bass"]
            if lbls[3]:
                st.session_state.asm_tables[lbls[3]] = s_data["drum"]

    for lbl, vals in st.session_state.asm_tables.items():
        lines = []
        for i in range(0, len(vals), 16):
            chunk = ", ".join(f"${v:02X}" if lbl == "palette" else str(v) for v in vals[i:i + 16])
            lines.append(f"  .byte {chunk}")
        new_block = "\n".join(lines) + "\n"
        text = re.sub(
            rf"^({re.escape(lbl)}:\s*\n?)((?:\s*\.byte\s+[^\n]+\n?)+)",
            rf"\g<1>{new_block}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    st.session_state.asm_text = text
    return text.encode("utf-8")


# =============================================================================
# INTERFAZ PRINCIPAL DE USUARIO
# =============================================================================
init_state()

st.title("🕹️ NES Shooter Studio")
st.markdown("Suite visual universal para analizar, escuchar y modificar cualquier ROM de Nintendo NES (`*.nes`) y código fuente 6502 (`*.s` / `*.asm`).")

if not st.session_state.has_nes and not st.session_state.has_asm:
    st.markdown("""
    <div class="studio-card">
        <h3>📂 Sube un archivo para iniciar el análisis</h3>
        <p>Selecciona cualquier archivo <b>.nes</b> (ej. <i>shooterv1.13.nes</i>, <i>shooter.nes</i>, <i>Castlevania.nes</i> o cualquier ROM comercial/homebrew) o un archivo <b>.s / .asm</b>. El analizador detectará sus canciones, textos, gráficos (incluyendo CHR-RAM comprimido) y código 6502 en milisegundos.</p>
    </div>
    """, unsafe_allow_html=True)

    c_up1, c_up2 = st.columns(2)
    with c_up1:
        up_nes_main = st.file_uploader("💿 Subir ROM de NES (*.nes)", type=["nes"], key="up_nes_init")
        if up_nes_main is not None:
            analyze_nes_file(bytearray(up_nes_main.read()), up_nes_main.name)
            st.rerun()
    with c_up2:
        up_asm_main = st.file_uploader("📝 Subir código ensamblador (*.s / *.asm)", type=["s", "asm"], key="up_asm_init")
        if up_asm_main is not None:
            analyze_asm_file(up_asm_main.read().decode("utf-8", errors="ignore"), up_asm_main.name)
            st.rerun()
    st.stop()

with st.sidebar:
    st.header("📂 Archivos Activos")
    if st.session_state.has_nes:
        st.success(f"💿 ROM: {st.session_state.nes_name}")
        st.caption(f"🎵 {len(st.session_state.songs)} pistas | 📝 {len(st.session_state.rom_texts)} textos\n🎨 {st.session_state.chr_source_info}")
    if st.session_state.has_asm:
        st.success(f"📝 Código: {st.session_state.asm_name}")

    st.markdown("**Cargar otro archivo:**")
    side_nes = st.file_uploader("Cambiar ROM (.nes)", type=["nes"], key="side_nes_u")
    if side_nes is not None:
        if st.button("📥 Analizar nueva ROM .nes", use_container_width=True):
            analyze_nes_file(bytearray(side_nes.read()), side_nes.name)
            st.rerun()

    side_asm = st.file_uploader("Cambiar Código (.s)", type=["s", "asm"], key="side_asm_u")
    if side_asm is not None:
        if st.button("📥 Analizar nuevo Código .s", use_container_width=True):
            analyze_asm_file(side_asm.read().decode("utf-8", errors="ignore"), side_asm.name)
            st.rerun()

    st.divider()
    st.header("💾 Descargar Cambios")
    if st.session_state.has_nes:
        st.download_button(
            "⬇️ Descargar ROM (.nes) Modificada",
            data=build_updated_nes(),
            file_name=f"mod_{st.session_state.nes_name}",
            mime="application/octet-stream",
            use_container_width=True,
        )
    if st.session_state.has_asm:
        st.download_button(
            "⬇️ Descargar Código (.s) Modificado",
            data=build_updated_asm(),
            file_name=st.session_state.asm_name,
            mime="text/plain",
            use_container_width=True,
        )

    st.divider()
    if st.button("🔄 Cerrar todo y volver al inicio", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

tab_mus, tab_txt, tab_spr, tab_ins = st.tabs([
    f"🎵 1. Canciones Chiptune ({len(st.session_state.songs)})",
    f"📝 2. Editor de Textos ({len(st.session_state.rom_texts) + len(st.session_state.asm_strings)})",
    "🎨 3. Visor y Editor de Gráficos CHR",
    "🔍 4. Inspector iNES y Desensamblador 6502"
])

# =============================================================================
# PESTAÑA 1: CANCIONES CHIPTUNE DETECTADAS Y REPRODUCTOR FIEL AL MOTOR 6502
# =============================================================================
with tab_mus:
    st.subheader("🎵 Canciones y Secuencias Musicales Detectadas")
    songs = st.session_state.songs

    if not songs:
        st.warning("No se encontraron secuencias musicales en este archivo.")
    else:
        col_m1, col_m2 = st.columns([1, 1.55])
        with col_m1:
            song_list = list(songs.keys())
            chosen_song = st.selectbox("🎼 Elige la pista que deseas escuchar o editar:", song_list)
            s_data = songs[chosen_song]

            s_data["tempo"] = st.slider(
                "Velocidad (Cuadros por nota - menor número = más rápido):",
                min_value=3, max_value=18, value=int(s_data.get("tempo", 6))
            )

            wav_audio = synthesize_song_wav_fast(s_data)
            st.markdown("**🔊 Reproductor Chiptune 2A03 en Tiempo Real:**")
            st.audio(wav_audio, format="audio/wav")

            st.download_button(
                "⬇️ Descargar pista en formato .WAV",
                data=wav_audio,
                file_name=f"{chosen_song[:24].strip()}.wav",
                mime="audio/wav",
                use_container_width=True,
            )

        with col_m2:
            st.markdown(f"**🎹 Secuenciador de Notas: `{chosen_song}`**")
            mel_arr = s_data["mel"]
            harm_arr = s_data["harm"]
            bass_arr = s_data["bass"]
            drum_arr = s_data["drum"]

            num_measures = max(1, (len(mel_arr) + 15) // 16)
            measure_idx = 0
            if num_measures > 1:
                measure_idx = st.selectbox(
                    "Seleccionar Compás de 16 pasos:",
                    range(num_measures),
                    format_func=lambda m: f"Compás #{m + 1} (Pasos {m*16} al {min(len(mel_arr)-1, m*16+15)})"
                )

            s_start = measure_idx * 16
            s_end = min(len(mel_arr), s_start + 16)

            rows = []
            for s in range(s_start, s_end):
                mv = mel_arr[s] if s < len(mel_arr) else 0
                hv = harm_arr[s] if s < len(harm_arr) else 0
                bv = bass_arr[s] if s < len(bass_arr) else 0
                dv = drum_arr[s % len(drum_arr)] if drum_arr else 0
                rows.append({
                    "Paso": f"Paso {s:02d}",
                    "Melodia": NOTE_NAMES[mv] if mv < len(NOTE_NAMES) else NOTE_NAMES[0],
                    "Armonia": NOTE_NAMES[hv] if hv < len(NOTE_NAMES) else NOTE_NAMES[0],
                    "Bajo": NOTE_NAMES[bv] if bv < len(NOTE_NAMES) else NOTE_NAMES[0],
                    "Bateria": DRUM_NAMES[dv] if dv < len(DRUM_NAMES) else DRUM_NAMES[0],
                })

            edited_rows = st.data_editor(
                rows,
                disabled=["Paso"],
                column_config={
                    "Melodia": st.column_config.SelectboxColumn("Pulso 1 (Melodía)", options=NOTE_NAMES),
                    "Armonia": st.column_config.SelectboxColumn("Pulso 2 (Armonía)", options=NOTE_NAMES),
                    "Bajo": st.column_config.SelectboxColumn("Triángulo (Bajo)", options=NOTE_NAMES),
                    "Bateria": st.column_config.SelectboxColumn("Ruido (Batería)", options=DRUM_NAMES),
                },
                use_container_width=True,
                height=380,
                key=f"ed_song_{chosen_song}_{measure_idx}"
            )

            if st.button("✔ Aplicar cambios a la canción y actualizar reproductor", use_container_width=True):
                for i_r, r in enumerate(edited_rows):
                    pos = s_start + i_r
                    if pos < len(mel_arr):
                        mel_arr[pos] = NOTE_TO_IDX.get(r["Melodia"], 0)
                    if pos < len(harm_arr):
                        harm_arr[pos] = NOTE_TO_IDX.get(r["Armonia"], 0)
                    if pos < len(bass_arr):
                        bass_arr[pos] = NOTE_TO_IDX.get(r["Bajo"], 0)
                    if drum_arr and (pos % len(drum_arr)) < len(drum_arr):
                        drum_arr[pos % len(drum_arr)] = DRUM_TO_IDX.get(r["Bateria"], 0)

                if "offsets" in s_data and st.session_state.has_nes:
                    ofs_map = s_data["offsets"]
                    prg = st.session_state.prg_data
                    if "mel" in ofs_map:
                        prg[ofs_map["mel"]:ofs_map["mel"] + len(mel_arr)] = bytearray(mel_arr)
                    if "harm" in ofs_map:
                        prg[ofs_map["harm"]:ofs_map["harm"] + len(harm_arr)] = bytearray(harm_arr)
                    if "bass" in ofs_map:
                        prg[ofs_map["bass"]:ofs_map["bass"] + len(bass_arr)] = bytearray(bass_arr)
                    if "drum" in ofs_map:
                        prg[ofs_map["drum"]:ofs_map["drum"] + len(drum_arr)] = bytearray(drum_arr)
                st.success("✔ Canción actualizada.")
                st.rerun()

# =============================================================================
# PESTAÑA 2: EDITOR UNIVERSAL DE TEXTOS
# =============================================================================
with tab_txt:
    if st.session_state.has_nes:
        st.subheader(f"🔤 Textos Detectados en `{st.session_state.nes_name}` ({len(st.session_state.rom_texts)} textos)")
        t_col1, t_col2 = st.columns([1.4, 1])

        with t_col1:
            ed_rom_txt = st.data_editor(
                st.session_state.rom_texts,
                column_order=("ID", "Tipo", "Direccion", "Texto", "Max_Chars"),
                disabled=["ID", "Tipo", "Direccion", "Max_Chars"],
                use_container_width=True,
                height=440,
                key="rom_txt_editor"
            )
            if st.button("✔ Guardar textos modificados en la ROM (.nes)", use_container_width=True):
                prg = st.session_state.prg_data
                for item in ed_rom_txt:
                    ofs = item["_offset"]
                    mx = item["Max_Chars"]
                    padded_str = item["Texto"][:mx].ljust(mx)
                    if item["_mode"] == "ppu":
                        for idx_c, ch in enumerate(padded_str):
                            prg[ofs + idx_c * 5 + 1] = ord(ch) & 0x7F
                    elif item["_mode"] == "shifted":
                        sh = item["_shift"]
                        for idx_c, ch in enumerate(padded_str):
                            prg[ofs + idx_c] = (ord(ch) + sh) & 0xFF
                    else:
                        prg[ofs:ofs + mx] = padded_str.encode("ascii", errors="replace")
                st.session_state.rom_texts = ed_rom_txt
                st.success("✔ Textos actualizados en el binario de la ROM.")
                st.rerun()

        with t_col2:
            st.markdown("**📺 Vista Previa de los Textos Detectados:**")
            preview_lines = [f"{r['Direccion']} [{r['ID']}]: {r['Texto']}" for r in ed_rom_txt[:35]]
            st.markdown(f'<div class="tv-preview">' + "\n".join(preview_lines) + '</div>', unsafe_allow_html=True)

    if st.session_state.has_asm:
        st.divider()
        st.subheader(f"📜 Textos del Código Fuente `{st.session_state.asm_name}`")
        st.session_state.asm_strings = st.data_editor(
            st.session_state.asm_strings,
            column_order=("Identificador", "Texto", "Caracteres"),
            disabled=["Identificador", "Caracteres"],
            use_container_width=True,
            height=340,
            key="asm_txt_editor"
        )

# =============================================================================
# PESTAÑA 3: VISOR Y EDITOR ULTRARRÁPIDO DE SPRITES Y CHR-ROM / CHR-RAM
# =============================================================================
with tab_spr:
    if not st.session_state.has_nes:
        st.info("💡 Sube un archivo **.nes** en el menú izquierdo para visualizar y editar los gráficos.")
    else:
        st.caption(f"**Origen Gráfico Activo:** `{st.session_state.chr_source_info}`")
        num_chr = max(1, len(st.session_state.chr_data) // 8192)
        col_s1, col_s2, col_s3 = st.columns([1.15, 1.15, 1])

        with col_s1:
            st.subheader("1. Mapa de Bloques Gráficos")
            b_idx = st.selectbox("Banco Gráfico (8 KB):", range(num_chr), format_func=lambda i: f"Banco #{i}")
            t_idx = st.radio("Tabla de Patrones:", [0, 1], format_func=lambda x: "Tabla 0 ($0000)" if x == 0 else "Tabla 1 ($1000)", horizontal=True, index=1 if num_chr == 1 else 0)
            p_grp = st.selectbox("Paleta de Color:", range(8), index=4, format_func=lambda g: f"Paleta #{g} ({'Fondo' if g < 4 else 'Sprite'})")
            tile_num = st.number_input("Elegir Tile (0 a 255):", 0, 255, 1)

            st.image(render_chr_sheet_fast(b_idx, t_idx, p_grp, tile_num), caption=f"Tile #{tile_num} seleccionado en recuadro azul")

        with col_s2:
            st.subheader(f"2. Editor del Tile #{tile_num}")
            st.caption("Valores de color (0=Transparente, 1..3=Colores de la paleta):")
            cur_mat = get_tile_matrix(b_idx, t_idx, tile_num)
            new_mat = st.data_editor(cur_mat, use_container_width=True, key=f"t_ed_{b_idx}_{t_idx}_{tile_num}")
            if st.button("✔ Guardar cambios en el Tile", use_container_width=True):
                set_tile_matrix(b_idx, t_idx, tile_num, new_mat)
                st.success(f"Tile #{tile_num} actualizado.")
                st.rerun()

            st.markdown("**Colores de la Paleta activa (0..63):**")
            pc = st.columns(4)
            for ci in range(4):
                with pc[ci]:
                    p_pos = p_grp * 4 + ci
                    st.session_state.palette[p_pos] = st.number_input(f"C{ci}", 0, 63, int(st.session_state.palette[p_pos]), key=f"pal_in_{p_pos}")
                    hx = rgb_hex(nes_rgb(st.session_state.palette[p_pos]))
                    st.markdown(f"<div style='height:22px;background:{hx};border:2px solid #334155;border-radius:4px;'></div>", unsafe_allow_html=True)

        with col_s3:
            st.subheader("3. Armador de Sprites 16×16")
            top_t = st.number_input("Tile Superior:", 0, 255, tile_num)
            bot_t = st.number_input("Tile Inferior:", 0, 255, min(255, tile_num + 1))
            sym_mode = st.checkbox("Reflejar mitad derecha (Simetría)", value=True)
            st.image(render_metasprite(b_idx, t_idx, top_t, top_t, bot_t, bot_t, sym_mode, p_grp), caption=f"Sprite 16×16 (Tiles {top_t} y {bot_t})")

# =============================================================================
# PESTAÑA 4: INSPECTOR iNES Y DESENSAMBLADOR 6502 MULTI-BANCO
# =============================================================================
with tab_ins:
    if st.session_state.has_nes:
        st.subheader(f"🔍 Arquitectura de `{st.session_state.nes_name}`")
        hdr = st.session_state.header
        prg = st.session_state.prg_data

        prg_b, chr_b, f6, f7 = hdr[4], hdr[5], hdr[6], hdr[7]
        mapper = (f7 & 0xF0) | (f6 >> 4)
        mirror = "Vertical" if (f6 & 1) else "Horizontal"

        nmi_v = prg[-6] | (prg[-5] << 8) if len(prg) >= 6 else 0
        rst_v = prg[-4] | (prg[-3] << 8) if len(prg) >= 6 else 0
        irq_v = prg[-2] | (prg[-1] << 8) if len(prg) >= 6 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Mapper iNES", f"#{mapper}", MAPPER_NAMES.get(mapper, "Especial"))
        m2.metric("Código PRG-ROM", f"{prg_b * 16} KB ({prg_b} bancos)")
        m3.metric("Gráficos CHR", f"{chr_b * 8} KB (CHR-ROM)" if chr_b > 0 else "0 KB (Usa CHR-RAM)")
        m4.metric("Mirroring", mirror)

        st.markdown(f"""
        <div class="studio-card">
            <b>Vectores de Hardware 6502 (Banco Final):</b>
            &nbsp;&nbsp;• <b>RESET ($FFFC):</b> <code>${rst_v:04X}</code>
            &nbsp;&nbsp;|&nbsp;&nbsp; <b>NMI ($FFFA):</b> <code>${nmi_v:04X}</code>
            &nbsp;&nbsp;|&nbsp;&nbsp; <b>IRQ ($FFFE):</b> <code>${irq_v:04X}</code>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("⚙️ Desensamblador 6502 Multi-Banco")
        num_p_banks = max(1, len(prg) // 16384)
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            b_sel = st.selectbox("Seleccionar Banco PRG (16 KB):", range(num_p_banks), index=num_p_banks - 1, format_func=lambda b: f"Banco PRG #{b}")
        with dc2:
            jump_vec = st.selectbox("Punto de entrada:", [
                ("Vector RESET", rst_v & 0x3FFF),
                ("Vector NMI (VBlank)", nmi_v & 0x3FFF),
                ("Inicio del Banco ($0000)", 0x0000),
            ], format_func=lambda x: f"{x[0]} (+${x[1]:04X})")
        with dc3:
            n_lines = st.slider("Instrucciones a mostrar:", 20, 120, 45)

        st.markdown(f'<div class="asm-viewer">{disassemble_6502(prg, b_sel, jump_vec[1], n_lines)}</div>', unsafe_allow_html=True)
