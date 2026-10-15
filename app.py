import io
import math
import os
import re
import struct
import wave
import streamlit as st
from PIL import Image, ImageDraw

# =============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILO VISUAL
# =============================================================================
st.set_page_config(
    page_title="NES Shooter Studio",
    page_icon="🕹️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0e0e18; color: #e8e8f0; }
    section[data-testid="stSidebar"] { background-color: #151525; border-right: 1px solid #2c2c44; }
    h1, h2, h3 { font-family: 'Courier New', Courier, monospace !important; color: #00e5ff !important; }
    .retro-card {
        background: #181828; border: 1px solid #ff6d00; border-radius: 8px;
        padding: 14px; margin-bottom: 12px;
    }
    .code-box {
        background: #07070c; border: 1px solid #00e5ff; border-radius: 6px;
        padding: 12px; font-family: 'Courier New', monospace; color: #00e676;
        white-space: pre; overflow-x: auto; font-size: 13px; line-height: 1.4;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# TABLAS DE HARDWARE NES (PALETA 2C02, MAPPERS, OPCODES 6502 Y NOTAS 2A03)
# =============================================================================
NES_MASTER_PALETTE = [
    (84, 84, 84), (0, 30, 116), (8, 16, 144), (48, 0, 136),
    (68, 0, 100), (92, 0, 48), (84, 4, 0), (60, 24, 0),
    (32, 42, 0), (8, 58, 0), (0, 64, 0), (0, 60, 0),
    (0, 50, 60), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (152, 150, 152), (8, 76, 196), (48, 50, 236), (92, 30, 228),
    (136, 20, 176), (160, 20, 100), (152, 34, 32), (120, 60, 0),
    (84, 90, 0), (40, 114, 0), (8, 124, 0), (0, 118, 40),
    (0, 102, 120), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (236, 238, 236), (76, 154, 236), (120, 124, 236), (176, 98, 236),
    (228, 84, 236), (236, 88, 180), (236, 106, 100), (212, 136, 32),
    (160, 170, 0), (116, 196, 0), (76, 208, 32), (56, 204, 108),
    (56, 180, 204), (60, 60, 60), (0, 0, 0), (0, 0, 0),
    (236, 238, 236), (168, 204, 236), (188, 188, 236), (212, 178, 236),
    (236, 174, 236), (236, 174, 212), (236, 180, 176), (228, 196, 144),
    (204, 210, 120), (180, 222, 120), (168, 226, 144), (152, 226, 180),
    (160, 214, 228), (160, 162, 160), (0, 0, 0), (0, 0, 0)
]

MAPPER_NAMES = {
    0: "NROM (Sin Mapper / 16-32KB PRG)",
    1: "MMC1 (SxROM - Nintendo)",
    2: "UxROM (PRG Switch)",
    3: "CNROM (CHR Switch)",
    4: "MMC3 (TxROM - IRQ Scanline)",
    7: "AxROM (Single-Screen)",
    9: "MMC2 (PxROM - Punch-Out!!)",
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
    "---", "C-3", "C#3", "D-3", "D#3", "E-3", "F-3", "F#3", "G-3", "G#3", "A-3", "A#3", "B-3",
    "C-4", "C#4", "D-4", "D#4", "E-4", "F-4", "F#4", "G-4", "G#4", "A-4", "A#4", "B-4",
    "C-5", "C#5", "D-5", "D#5", "E-5", "F-5", "F#5", "G-5", "G#5", "A-5", "A#5", "B-5"
]
NOTE_FREQS = [0.0] + [130.81 * (2 ** (i / 12.0)) for i in range(36)]
NOTE_TO_IDX = {n: i for i, n in enumerate(NOTE_NAMES)}

DRUM_NAMES = ["---", "DUM (Kick)", "CLAP (Snare)", "TS (Hi-Hat)"]
DRUM_TO_IDX = {n: i for i, n in enumerate(DRUM_NAMES)}


def nes_rgb(idx):
    return NES_MASTER_PALETTE[idx & 0x3F]


def rgb_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def build_default_chr():
    chr_data = bytearray(8192)
    def put_hex(offset, hex_str):
        raw = bytes.fromhex(hex_str.replace(" ", ""))
        chr_data[offset:offset + len(raw)] = raw

    put_hex(0x0010,
        "DB999999DB9999996666424266664242"
        "00000000810000000000000000000000"
        "18181818000018181818181800001818"
        "FFFF00000000FFFFFFFFAA55AA55FFFF"
        "FF80BDADADBD8080FFFE80B5B5808080"
        "FF00BDADADBD0000FFFF00B5B5000000"
        "FF03BDADADBD0303FF7F01B5B5010101"
        "8080BD8080FFFF008080BD808000FFFF"
        "0000BD0000FFFF000000BD000000FFFF"
        "0303BD0303FFFF010101BD010101FFFF"
        "D5D5FFFFD5D5FFFF8080808080808080"
        "B6B6FFFFB6B6FFFF0000000000000000"
        "ABABFFFFABABFFFF0303030303030303"
        "FF000024000000FF00FF000000000000"
    )
    put_hex(0x1010,
        "01030307070F3F7E000001010303061C7CEFCF1F9FCF18001830706000000000"
        "1F7FF89EBF7B3C1800001F61430700001F0F0700000000000000000000000000"
        "0018181818180000001818181818000000001824241800000000001818000000"
        "0000000000000000000000000000000000000000000000FF00000000000000FF"
        "071F3F7FF3FF7F3F00071C300F1F07001F0F3737130300000700080800000000"
        "0103070F1F3F7F7F00000103060C19337FDFCF87030100003F00000000000000"
        "18183C7EFFDB9918001818243C180000"
        "183C3C7E5A7E5A7E0018002400240024"
        "007E427E00000000003C3C3C00000000"
    )
    put_hex(0x1800,
        "01030307070F1F3F0000010D0D050D157FFFEF1F9FCF0D0199B5AD32320C0301"
        "03070727272F3F7F03030323272101037F7F7F7F3F0F0606819D819D030E0606"
        "01030327272F1F7F01020220262E19057F7F7F3B1B0F03012561612424092020"
        "00242424242424000000242424240000"
        "00183C7E420000000000183C7E420000"
        "0018187E7E1818000000183C3C180000"
        "142A5D3F7F3F5F2F081C3E7F7F3F1E0C"
        "92492408814210884020080001020800"
    )
    return chr_data


# =============================================================================
# INICIALIZACIÓN DEL ESTADO GLOBAL EN MEMORIA
# =============================================================================
def init_state():
    if "initialized" in st.session_state:
        return
    st.session_state.initialized = True
    st.session_state.rom_name = "shooter.nes"
    st.session_state.asm_name = "shooter.s"
    st.session_state.asm_text = ""

    st.session_state.header = bytearray([0x4E, 0x45, 0x53, 0x1A, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    st.session_state.prg_data = bytearray(16384)
    st.session_state.chr_data = build_default_chr()
    st.session_state.nametable = bytearray([((i % 14) + 1) for i in range(960)])

    st.session_state.palette = [
        0x0F, 0x00, 0x0C, 0x18, 0x0F, 0x01, 0x02, 0x12,
        0x0F, 0x16, 0x27, 0x38, 0x0F, 0x30, 0x00, 0x10,
        0x0F, 0x2C, 0x38, 0x11, 0x0F, 0x0C, 0x24, 0x38,
        0x0F, 0x2A, 0x38, 0x30, 0x0F, 0x30, 0x16, 0x27
    ]

    st.session_state.asm_strings = []
    st.session_state.asm_tables = {}

    st.session_state.tracker = [
        {"Paso": f"{i:02d}",
         "Pulso_1": NOTE_NAMES[17 if i % 4 == 0 else (20 if i % 4 == 2 else 0)],
         "Pulso_2": NOTE_NAMES[12 if i % 2 == 0 else 15],
         "Triangulo": NOTE_NAMES[5 if i % 2 == 0 else 17],
         "Ruido": DRUM_NAMES[1 if i % 4 == 0 else (2 if i % 4 == 2 else 3)]}
        for i in range(32)
    ]

    for f in os.listdir("."):
        if f.lower().endswith(".nes"):
            with open(f, "rb") as fp:
                load_nes_rom(bytearray(fp.read()), f)
            break
    for f in os.listdir("."):
        if f.lower().endswith((".s", ".asm")):
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                load_asm_source(fp.read(), f)
            break


def load_nes_rom(data: bytearray, filename: str):
    if len(data) < 16 or data[:4] != b"NES\x1a":
        st.error("El archivo no contiene una firma iNES ('NES\\x1A') válida.")
        return
    st.session_state.rom_name = filename
    st.session_state.header = data[:16]
    prg_banks = data[4]
    chr_banks = data[5]
    has_trainer = bool(data[6] & 0x04)

    offset = 16 + (512 if has_trainer else 0)
    prg_size = prg_banks * 16384
    chr_size = chr_banks * 8192

    st.session_state.prg_data = bytearray(data[offset:offset + prg_size])
    if chr_size > 0 and len(data) >= offset + prg_size + chr_size:
        st.session_state.chr_data = bytearray(data[offset + prg_size:offset + prg_size + chr_size])
    else:
        st.session_state.chr_data = bytearray(data[offset:offset + 8192]) if len(data) >= offset + 8192 else bytearray(8192)


def export_nes_rom() -> bytes:
    hdr = bytearray(st.session_state.header)
    prg = st.session_state.prg_data
    chr_d = st.session_state.chr_data
    hdr[4] = max(1, len(prg) // 16384)
    hdr[5] = len(chr_d) // 8192 if int(st.session_state.header[5]) > 0 else 0
    if hdr[5] > 0:
        return bytes(hdr + prg + chr_d)
    return bytes(hdr + prg)


def load_asm_source(text: str, filename: str):
    st.session_state.asm_name = filename
    st.session_state.asm_text = text

    strings = []
    for m in re.finditer(r'(PRINT\s+\$[0-9A-Fa-f]+,\s*"|[A-Za-z0-9_]+:\s*\.byte\s+"|\.asciiz\s+")([^"]*)(")', text):
        strings.append({"Prefijo": m.group(1), "Texto": m.group(2), "Longitud": len(m.group(2))})
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


def export_asm_source() -> bytes:
    text = st.session_state.asm_text
    if not text:
        return b"; No se ha cargado ningun archivo .s"

    for item in st.session_state.asm_strings:
        pref_esc = re.escape(item["Prefijo"])
        new_txt = item["Texto"]
        text = re.sub(rf'({pref_esc})[^"]*(")', rf'\g<1>{new_txt}\g<2>', text, count=1)

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


def get_tile_pixels(chr_bank_idx: int, pat_table: int, tile_id: int):
    offset = (chr_bank_idx * 8192) + (pat_table * 4096) + (tile_id * 16)
    mat = [[0] * 8 for _ in range(8)]
    chr_d = st.session_state.chr_data
    if offset + 16 > len(chr_d):
        return mat
    for y in range(8):
        b0 = chr_d[offset + y]
        b1 = chr_d[offset + 8 + y]
        for x in range(8):
            bit0 = (b0 >> (7 - x)) & 1
            bit1 = (b1 >> (7 - x)) & 1
            mat[y][x] = (bit1 << 1) | bit0
    return mat


def set_tile_pixels(chr_bank_idx: int, pat_table: int, tile_id: int, mat):
    offset = (chr_bank_idx * 8192) + (pat_table * 4096) + (tile_id * 16)
    if offset + 16 > len(st.session_state.chr_data):
        return
    for y in range(8):
        b0, b1 = 0, 0
        for x in range(8):
            c = int(mat[y][x]) & 3
            b0 = (b0 << 1) | (c & 1)
            b1 = (b1 << 1) | ((c >> 1) & 1)
        st.session_state.chr_data[offset + y] = b0
        st.session_state.chr_data[offset + 8 + y] = b1


def render_pattern_table(chr_bank_idx: int, pat_table: int, pal_group: int, highlight_tile: int = None):
    sub_pal = [nes_rgb(st.session_state.palette[pal_group * 4 + c]) for c in range(4)]
    img = Image.new("RGB", (128, 128))
    px = img.load()
    for t_id in range(256):
        tx = (t_id % 16) * 8
        ty = (t_id // 16) * 8
        mat = get_tile_pixels(chr_bank_idx, pat_table, t_id)
        for y in range(8):
            for x in range(8):
                px[tx + x, ty + y] = sub_pal[mat[y][x]]
    img = img.resize((384, 384), Image.NEAREST)
    if highlight_tile is not None:
        draw = ImageDraw.Draw(img)
        sx = (highlight_tile % 16) * 24
        sy = (highlight_tile // 16) * 24
        draw.rectangle([sx, sy, sx + 23, sy + 23], outline=(0, 229, 255), width=2)
    return img


def render_metasprite_16x16(chr_bank_idx: int, pat_table: int, tl: int, tr: int, bl: int, br: int, flip_h_right: bool, pal_group: int):
    sub_pal = [nes_rgb(st.session_state.palette[pal_group * 4 + c]) for c in range(4)]
    img = Image.new("RGB", (16, 16), sub_pal[0])
    px = img.load()
    quads = [(0, 0, tl, False), (8, 0, tr, flip_h_right), (0, 8, bl, False), (8, 8, br, flip_h_right)]
    for qx, qy, t_id, fl_h in quads:
        mat = get_tile_pixels(chr_bank_idx, pat_table, t_id)
        for y in range(8):
            for x in range(8):
                sx = (7 - x) if fl_h else x
                c = mat[y][sx]
                px[qx + x, qy + y] = sub_pal[c]
    return img.resize((160, 160), Image.NEAREST)


def disassemble_6502(prg_bytes: bytes, bank_idx: int, start_offset: int, num_lines: int = 45):
    bank_size = 16384
    base_rom = bank_idx * bank_size
    cpu_base = 0xC000 if len(prg_bytes) == 16384 or bank_idx == (len(prg_bytes) // 16384 - 1) else 0x8000
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
            operand = f"${op:02X}"
            size = 1
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
            addr = raw_chunk[1] | (raw_chunk[2] << 8)
            operand = f"${addr:04X}"
        elif mode == "absx":
            addr = raw_chunk[1] | (raw_chunk[2] << 8)
            operand = f"${addr:04X},X"
        elif mode == "absy":
            addr = raw_chunk[1] | (raw_chunk[2] << 8)
            operand = f"${addr:04X},Y"
        elif mode == "ind":
            addr = raw_chunk[1] | (raw_chunk[2] << 8)
            operand = f"(${addr:04X})"
        elif mode == "rel":
            signed_ofs = raw_chunk[1] - 256 if raw_chunk[1] >= 128 else raw_chunk[1]
            target = (cpu_addr + 2 + signed_ofs) & 0xFFFF
            operand = f"${target:04X}"
        else:
            operand = ""

        lines.append(f"${cpu_addr:04X}  {hex_str:<8s}  {mnem:<4s} {operand}")
        pc += size

    return "\n".join(lines)


def synthesize_tracker_wav(tracker_rows, step_frames=6):
    sample_rate = 22050
    samples_per_step = int(sample_rate * (step_frames / 60.0))
    pcm = bytearray()
    lfsr = 1

    for row in tracker_rows:
        f1 = NOTE_FREQS[NOTE_TO_IDX.get(row["Pulso_1"], 0)]
        f2 = NOTE_FREQS[NOTE_TO_IDX.get(row["Pulso_2"], 0)]
        ft = NOTE_FREQS[NOTE_TO_IDX.get(row["Triangulo"], 0)] * 0.5
        dh = DRUM_TO_IDX.get(row["Ruido"], 0)

        for i in range(samples_per_step):
            t = i / sample_rate
            env = max(0.25, 1.0 - (i / samples_per_step) * 0.65)
            v1 = (1.0 if (t * f1) % 1.0 < 0.25 else -1.0) * 0.22 * env if f1 > 0 else 0.0
            v2 = (1.0 if (t * f2) % 1.0 < 0.50 else -1.0) * 0.14 * env if f2 > 0 else 0.0
            if ft > 0:
                ph = (t * ft) % 1.0
                vt = (4.0 * ph - 1.0 if ph < 0.5 else 3.0 - 4.0 * ph) * 0.28
            else:
                vt = 0.0

            vd = 0.0
            if dh > 0 and i < int(sample_rate * 0.045):
                d_env = 1.0 - (i / (sample_rate * 0.045))
                if dh == 1:
                    vd = math.sin(2 * math.pi * (110.0 - i * 0.12) * t) * 0.35 * d_env
                elif dh == 2:
                    bit = (lfsr ^ (lfsr >> 1)) & 1
                    lfsr = (lfsr >> 1) | (bit << 14)
                    vd = (1.0 if (lfsr & 1) else -1.0) * 0.25 * d_env
                elif dh == 3 and i < int(sample_rate * 0.022):
                    bit = (lfsr ^ (lfsr >> 6)) & 1
                    lfsr = (lfsr >> 1) | (bit << 14)
                    vd = (1.0 if (lfsr & 1) else -1.0) * 0.16 * d_env

            val = int(max(-1.0, min(1.0, v1 + v2 + vt + vd)) * 30000)
            pcm += struct.pack("<h", val)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


init_state()

with st.sidebar:
    st.markdown("## 📂 Selector Universal de Archivos")
    st.caption("Abre cualquier ROM `.nes` (comercial o homebrew), banco `.chr` o código `.s`/`.asm`.")

    up_nes = st.file_uploader("💿 Cargar ROM de NES (.nes)", type=["nes"])
    if up_nes is not None:
        if st.button("📥 Abrir ROM .nes", use_container_width=True):
            load_nes_rom(bytearray(up_nes.read()), up_nes.name)
            st.success(f"ROM cargada: {up_nes.name}")

    up_chr = st.file_uploader("🎨 Cargar Banco Gráfico (.chr / .bin)", type=["chr", "bin"])
    if up_chr is not None:
        if st.button("📥 Importar CHR", use_container_width=True):
            raw_chr = bytearray(up_chr.read())
            if len(raw_chr) >= 4096:
                st.session_state.chr_data = raw_chr
                st.success(f"CHR cargado ({len(raw_chr):,} bytes)")

    up_asm = st.file_uploader("📝 Cargar Código 6502 (.s / .asm)", type=["s", "asm"])
    if up_asm is not None:
        if st.button("📥 Procesar Código .s", use_container_width=True):
            load_asm_source(up_asm.read().decode("utf-8", errors="ignore"), up_asm.name)
            st.success(f"Código cargado: {up_asm.name}")

    st.divider()
    st.markdown("## 💾 Exportar Archivos")
    st.download_button(
        "⬇️ Descargar ROM (.nes) modificada",
        data=export_nes_rom(),
        file_name=f"mod_{st.session_state.rom_name}",
        mime="application/octet-stream",
        use_container_width=True,
    )
    st.download_button(
        "⬇️ Exportar Bancos Gráficos (.chr)",
        data=bytes(st.session_state.chr_data),
        file_name="graphics.chr",
        mime="application/octet-stream",
        use_container_width=True,
    )
    if st.session_state.asm_text:
        st.download_button(
            "⬇️ Descargar Código (.s) modificado",
            data=export_asm_source(),
            file_name=st.session_state.asm_name,
            mime="text/plain",
            use_container_width=True,
        )

st.title("🕹️ NES SHOOTER STUDIO — Inspector y Editor Universal de ROMs y Homebrew")
st.caption(f"**ROM Activa:** `{st.session_state.rom_name}` | **Código 6502 Activo:** `{st.session_state.asm_name}` | **Licencia:** `CC0 1.0 Universal`")

tab_chr, tab_txt, tab_map, tab_mus, tab_dis = st.tabs([
    "🎨 Visor y Editor CHR / Sprites",
    "📝 Editor de Textos y Tablas (.nes / .s)",
    "🗺️ Constructor de Mapas (Nametable)",
    "🎵 Estudio Chiptune (2A03)",
    "🔍 Inspector iNES y Desensamblador 6502"
])

with tab_chr:
    num_chr_banks = max(1, len(st.session_state.chr_data) // 8192)
    c1, c2, c3 = st.columns([1.15, 1.15, 1])

    with c1:
        st.subheader("🧩 Explorador de Bancos CHR")
        bank_sel = st.selectbox("Banco CHR de 8 KB:", range(num_chr_banks), format_func=lambda i: f"Banco CHR #{i} (${i*0x2000:04X})")
        pat_sel = st.radio("Tabla de Patrones PPU:", [0, 1], format_func=lambda p: "Tabla 0 ($0000 - Fondo/Sprites)" if p == 0 else "Tabla 1 ($1000 - Sprites/Fondo)", horizontal=True, index=1)
        pal_sel = st.selectbox("Sub-Paleta de Previsualización:", range(8), index=4, format_func=lambda g: f"Paleta #{g} ({'BG' if g < 4 else 'Sprite'} {g % 4})")
        tile_id = st.number_input("Tile Seleccionado (0..255):", 0, 255, 128)

        st.image(render_pattern_table(bank_sel, pat_sel, pal_sel, tile_id), caption=f"Banco #{bank_sel} - Tabla #{pat_sel} (Tile #{tile_id} / ${tile_id:02X})")

    with c2:
        st.subheader(f"✏️ Editor de Píxeles 8×8 (Tile ${tile_id:02X})")
        st.caption("Edita los valores `0..3` de cada píxel y guarda los cambios directamente en la ROM:")
        mat = get_tile_pixels(bank_sel, pat_sel, tile_id)
        ed_mat = st.data_editor(mat, use_container_width=True, key=f"ed_{bank_sel}_{pat_sel}_{tile_id}")
        if st.button("💾 Guardar Tile en CHR", use_container_width=True):
            set_tile_pixels(bank_sel, pat_sel, tile_id, ed_mat)
            st.rerun()

        st.markdown("**Personalizar Colores de la Sub-Paleta Activa:**")
        p_cols = st.columns(4)
        for c_i in range(4):
            with p_cols[c_i]:
                p_idx = pal_sel * 4 + c_i
                st.session_state.palette[p_idx] = st.number_input(f"Color {c_i} (0..63)", 0, 63, int(st.session_state.palette[p_idx]), key=f"pal_{p_idx}")
                hx = rgb_hex(nes_rgb(st.session_state.palette[p_idx]))
                st.markdown(f"<div style='height:18px;background:{hx};border:1px solid #fff;'></div>", unsafe_allow_html=True)

    with c3:
        st.subheader("👾 Armador de Metasprites 16×16")
        st.caption("Combina cualquier grupo de 4 tiles de la ROM para visualizar personajes o naves:")
        ms_c1, ms_c2 = st.columns(2)
        with ms_c1:
            t_tl = st.number_input("Tile Sup-Izq", 0, 255, tile_id)
            t_bl = st.number_input("Tile Inf-Izq", 0, 255, min(255, tile_id + 1))
        with ms_c2:
            t_tr = st.number_input("Tile Sup-Der", 0, 255, tile_id)
            t_br = st.number_input("Tile Inf-Der", 0, 255, min(255, tile_id + 1))
        mirror_r = st.checkbox("Espejar horizontalmente mitad derecha (Simetría)", value=True)
        st.image(render_metasprite_16x16(bank_sel, pat_sel, t_tl, t_tr, t_bl, t_br, mirror_r, pal_sel), caption="Vista Previa Metasprite 16×16")

with tab_txt:
    t_col1, t_col2 = st.columns(2)

    with t_col1:
        st.subheader("🔤 Parcheador de Textos en Binario (.nes)")
        st.caption("Escanea cadenas ASCII dentro de `PRG-ROM` y permite reemplazarlas directamente en la ROM:")
        prg = st.session_state.prg_data
        matches = list(re.finditer(rb"[A-Za-z0-9\-\.,!# ]{5,}", bytes(prg)))
        if matches:
            rom_strs = [
                {"Offset_Hex": f"${m.start():04X}", "Texto_Original": m.group(0).decode("ascii", errors="ignore"), "Nuevo_Texto": m.group(0).decode("ascii", errors="ignore"), "Max_Len": len(m.group(0))}
                for m in matches[:40]
            ]
            ed_rom_strs = st.data_editor(rom_strs, disabled=["Offset_Hex", "Texto_Original", "Max_Len"], use_container_width=True, height=340)
            if st.button("✔ Parchear Textos en PRG-ROM", use_container_width=True):
                for row in ed_rom_strs:
                    ofs = int(row["Offset_Hex"][1:], 16)
                    ln = int(row["Max_Len"])
                    new_b = row["Nuevo_Texto"][:ln].ljust(ln).encode("ascii", errors="replace")
                    st.session_state.prg_data[ofs:ofs + ln] = new_b
                st.success("Textos parcheados exitosamente en el binario de la ROM.")
        else:
            st.info("Carga una ROM .nes en la barra lateral para escanear sus cadenas de texto.")

    with t_col2:
        st.subheader("📜 Editor de Textos y Tablas de Código (.s / .asm)")
        if st.session_state.asm_text:
            if st.session_state.asm_strings:
                st.markdown("**Cadenas de Texto detectadas en `.s`:**")
                st.session_state.asm_strings = st.data_editor(st.session_state.asm_strings, disabled=["Prefijo", "Longitud"], use_container_width=True, height=200)

            if st.session_state.asm_tables:
                tbl_name = st.selectbox("Editar Tabla de Datos (`.byte`) del archivo `.s`:", list(st.session_state.asm_tables.keys()))
                cur_vals = st.session_state.asm_tables[tbl_name]
                raw_ed = st.text_area(f"Valores de `{tbl_name}` ({len(cur_vals)} bytes):", ", ".join(str(x) for x in cur_vals), height=120)
                if st.button(f"✔ Actualizar Tabla `{tbl_name}`", use_container_width=True):
                    nums = [int(t) for t in re.findall(r"\d+", raw_ed)]
                    if nums:
                        st.session_state.asm_tables[tbl_name] = nums
                        st.success(f"Tabla {tbl_name} actualizada.")
        else:
            st.info("Carga cualquier archivo `.s` o `.asm` en la barra lateral para editar sus textos y tablas `.byte` de forma visual.")

with tab_map:
    nm_c1, nm_c2 = st.columns([1.3, 1])
    with nm_c1:
        st.subheader("🖥️ Visor de Nametable PPU (32×30 Tiles / 256×240 px)")
        map_chr_bank = st.selectbox("Usar Banco CHR:", range(num_chr_banks), key="map_chr_b")
        map_pat = st.radio("Tabla de Patrones de Fondo:", [0, 1], horizontal=True, key="map_pt")
        map_pal = st.selectbox("Paleta de Fondo:", range(4), key="map_pal")

        sub_p = [nes_rgb(st.session_state.palette[map_pal * 4 + c]) for c in range(4)]
        nt_img = Image.new("RGB", (256, 240), sub_p[0])
        nt_px = nt_img.load()
        nt_data = st.session_state.nametable
        for ty in range(30):
            for tx in range(32):
                t_id = nt_data[ty * 32 + tx]
                mat = get_tile_pixels(map_chr_bank, map_pat, t_id)
                for py in range(8):
                    for px_i in range(8):
                        nt_px[tx * 8 + px_i, ty * 8 + py] = sub_p[mat[py][px_i]]
        st.image(nt_img.resize((512, 480), Image.NEAREST), caption="Previsualización de Pantalla Completa (Nametable)")

    with nm_c2:
        st.subheader("🛠️ Herramientas de Nametable")
        up_nam = st.file_uploader("Importar archivo Nametable (.nam / 960-1024 B)", type=["nam", "bin"])
        if up_nam is not None:
            nam_b = bytearray(up_nam.read())
            if len(nam_b) >= 960:
                st.session_state.nametable = nam_b[:960]
                st.rerun()

        if st.button("🎲 Generar Mapa con Tiles del Banco Actual", use_container_width=True):
            for ty in range(30):
                for tx in range(32):
                    st.session_state.nametable[ty * 32 + tx] = ((ty * 32 + tx) % 14) + 1
            st.rerun()

        st.download_button(
            "⬇️ Exportar Nametable (.nam)",
            data=bytes(st.session_state.nametable),
            file_name="screen.nam",
            mime="application/octet-stream",
            use_container_width=True,
        )

with tab_mus:
    st.subheader("🎹 Tracker Chiptune 2A03 y Sintetizador en el Navegador")
    m_c1, m_c2 = st.columns([1, 1.6])

    with m_c1:
        tempo_frames = st.slider("Velocidad del Secuenciador (Cuadros por Paso):", 3, 18, 6)
        wav_data = synthesize_tracker_wav(st.session_state.tracker, tempo_frames)
        st.audio(wav_data, format="audio/wav")
        st.download_button("⬇️ Descargar Audio Sintetizado (.wav)", data=wav_data, file_name="nes_chiptune.wav", mime="audio/wav", use_container_width=True)

        if st.session_state.asm_tables:
            st.markdown("**Importar Pista desde Tabla `.s`:**")
            mel_tbl = st.selectbox("Tabla para Pulso 1:", list(st.session_state.asm_tables.keys()))
            if st.button("📥 Cargar Tabla en el Tracker", use_container_width=True):
                arr = st.session_state.asm_tables[mel_tbl]
                for i in range(min(32, len(arr))):
                    n_idx = arr[i] if arr[i] < len(NOTE_NAMES) else 0
                    st.session_state.tracker[i]["Pulso_1"] = NOTE_NAMES[n_idx]
                st.rerun()

    with m_c2:
        st.session_state.tracker = st.data_editor(
            st.session_state.tracker,
            column_config={
                "Pulso_1": st.column_config.SelectboxColumn("Pulso 1 (Lead)", options=NOTE_NAMES),
                "Pulso_2": st.column_config.SelectboxColumn("Pulso 2 (Armonía)", options=NOTE_NAMES),
                "Triangulo": st.column_config.SelectboxColumn("Triángulo (Bajo)", options=NOTE_NAMES),
                "Ruido": st.column_config.SelectboxColumn("Ruido (Percusión)", options=DRUM_NAMES),
            },
            use_container_width=True,
            height=380,
        )

with tab_dis:
    st.subheader("🔍 Cabecera iNES, Vectores de Hardware y Desensamblador 6502")
    hdr = st.session_state.header
    prg = st.session_state.prg_data
    chr_d = st.session_state.chr_data

    prg_banks = hdr[4]
    chr_banks = hdr[5]
    f6, f7 = hdr[6], hdr[7]
    mapper_id = (f7 & 0xF0) | (f6 >> 4)
    mirror_str = "Four-Screen" if (f6 & 8) else ("Vertical" if (f6 & 1) else "Horizontal")
    sram_str = "Sí (Batería)" if (f6 & 2) else "No"

    nmi_vec = prg[-6] | (prg[-5] << 8) if len(prg) >= 6 else 0
    rst_vec = prg[-4] | (prg[-3] << 8) if len(prg) >= 6 else 0
    irq_vec = prg[-2] | (prg[-1] << 8) if len(prg) >= 6 else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Mapper ID", f"#{mapper_id}", MAPPER_NAMES.get(mapper_id, "Mapper Especial"))
    k2.metric("PRG-ROM (Código)", f"{len(prg) // 1024} KB ({prg_banks} bancos)")
    k3.metric("CHR-ROM / RAM", f"{len(chr_d) // 1024} KB ({'CHR-RAM' if chr_banks == 0 else f'{chr_banks} bancos'})")
    k4.metric("Mirroring / SRAM", f"{mirror_str} / {sram_str}")

    st.markdown(f"""
    <div class="retro-card">
        <b>Vectores de Interrupción del Procesador 6502:</b>
        &nbsp;&nbsp;• <code>NMI ($FFFA)</code>: <b>${nmi_vec:04X}</b>
        &nbsp;&nbsp;• <code>RESET ($FFFC)</code>: <b>${rst_vec:04X}</b>
        &nbsp;&nbsp;• <code>IRQ/BRK ($FFFE)</code>: <b>${irq_vec:04X}</b>
    </div>
    """, unsafe_allow_html=True)

    d_c1, d_c2, d_c3 = st.columns(3)
    num_prg_banks = max(1, len(prg) // 16384)
    with d_c1:
        prg_bank_sel = st.selectbox("Banco PRG (16 KB):", range(num_prg_banks), index=num_prg_banks - 1)
    with d_c2:
        default_ofs = (rst_vec & 0x3FFF) if (rst_vec >= 0x8000 and prg_bank_sel == num_prg_banks - 1) else 0
        start_hex = st.text_input("Offset Inicial dentro del Banco (Hex $0000..$3FFF):", f"{default_ofs:04X}")
    with d_c3:
        num_ins = st.slider("Instrucciones a desensamblar:", 15, 120, 45)

    try:
        ofs_val = max(0, min(0x3FFF, int(start_hex.replace("$", "").strip(), 16)))
    except ValueError:
        ofs_val = 0

    asm_dump = disassemble_6502(prg, prg_bank_sel, ofs_val, num_ins)
    st.markdown(f'<div class="code-box">{asm_dump}</div>', unsafe_allow_html=True)