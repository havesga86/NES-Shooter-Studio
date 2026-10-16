import io
import math
import re
import struct
import wave
import streamlit as st
from PIL import Image, ImageDraw

# =============================================================================
# CONFIGURACIÓN DE PÁGINA Y CSS DE ALTO CONTRASTE (ANTI-MODO OSCURO ROTO)
# =============================================================================
st.set_page_config(
    page_title="NES Shooter Studio",
    page_icon="🕹️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Forzar tema claro de alto contraste legible en cualquier navegador */
    .stApp {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 2px solid #cbd5e1 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #0f172a !important;
    }
    h1, h2, h3, h4, p, label, span, div {
        color: #0f172a;
    }
    /* Tarjetas limpias */
    .studio-card {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-left: 5px solid #2563eb !important;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    /* Pestañas bien legibles */
    button[data-baseweb="tab"] {
        background-color: #e2e8f0 !important;
        color: #1e293b !important;
        font-weight: 700 !important;
        border-radius: 6px 6px 0 0 !important;
        margin-right: 4px !important;
        padding: 10px 18px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }
    /* Inputs, Selectboxes y Textareas siempre con fondo blanco y letra negra */
    input, textarea, select, [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #94a3b8 !important;
    }
    /* Botones de acción */
    .stButton > button, .stDownloadButton > button {
        background-color: #2563eb !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 6px !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background-color: #1d4ed8 !important;
        color: #ffffff !important;
    }
    /* Visor de código y desensamblador */
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
        font-size: 15px !important;
        white-space: pre !important;
        line-height: 1.4 !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CONSTANTES DE HARDWARE NES (PALETA 2C02, MAPPERS, OPCODES 6502 Y NOTAS 2A03)
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
    0: "NROM (Estándar 16-32KB PRG)",
    1: "MMC1 (SxROM - Nintendo)",
    2: "UxROM (Cambio de bancos PRG)",
    3: "CNROM (Cambio de bancos CHR)",
    4: "MMC3 (TxROM - Contador IRQ)",
    7: "AxROM",
    9: "MMC2 (PxROM)",
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
    return NES_MASTER_PALETTE[idx & 0x3F]


def rgb_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


# =============================================================================
# INICIALIZACIÓN DEL ESTADO (VACÍO HASTA QUE EL USUARIO SUBA UN ARCHIVO)
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
    st.session_state.palette = [
        0x0F, 0x00, 0x10, 0x30, 0x0F, 0x01, 0x11, 0x21,
        0x0F, 0x16, 0x27, 0x38, 0x0F, 0x09, 0x19, 0x29,
        0x0F, 0x2C, 0x38, 0x11, 0x0F, 0x16, 0x27, 0x30,
        0x0F, 0x2A, 0x38, 0x30, 0x0F, 0x14, 0x24, 0x38
    ]

    st.session_state.asm_strings = []
    st.session_state.asm_tables = {}
    st.session_state.songs = {}
    st.session_state.note_lo = list(DEFAULT_NOTE_LO)
    st.session_state.note_hi = list(DEFAULT_NOTE_HI)


# =============================================================================
# ANALIZADORES AUTOMÁTICOS AL SUBIR ARCHIVO .NES O .S
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
    if chr_size > 0 and len(data) >= offset + prg_size + chr_size:
        st.session_state.chr_data = bytearray(data[offset + prg_size:offset + prg_size + chr_size])
    else:
        st.session_state.chr_data = bytearray(data[offset:offset + 8192]) if len(data) >= offset + 8192 else bytearray(8192)

    # Buscar paletas en PRG-ROM (bloques de 16 o 32 bytes que inicien con $0F y valores <= $3F)
    prg = st.session_state.prg_data
    for i in range(len(prg) - 32):
        if prg[i] == 0x0F and prg[i + 4] == 0x0F and prg[i + 8] == 0x0F and prg[i + 12] == 0x0F:
            cand = list(prg[i:i + 32])
            if all(b <= 0x3F for b in cand) and len(set(cand)) >= 6:
                st.session_state.palette = cand
                break

    # Detectar canciones dentro del binario .nes si aún no hay canciones cargadas desde .s
    if not st.session_state.songs:
        detect_songs_in_rom(prg)


def detect_songs_in_rom(prg: bytearray):
    songs = {}
    # 1. Buscar firma de la tabla de notas de SHOOTER o secuencias musicales en PRG-ROM
    sig = bytes([0x00, 0xA6, 0x3A, 0xFB, 0xC4, 0xAB])
    pos = prg.find(sig)
    if pos != -1 and pos + 800 <= len(prg):
        st.session_state.note_lo = list(prg[pos:pos + 24])
        st.session_state.note_hi = list(prg[pos + 24:pos + 48])
        base = pos + 48 + 36  # Saltar song_order (36 bytes)
        if base + 800 <= len(prg):
            songs["Tema Principal (Extraído de ROM)"] = {
                "tempo": 6,
                "mel": list(prg[base:base + 64]),
                "harm": list(prg[base + 256:base + 320]),
                "bass": list(prg[base + 512:base + 576]),
                "drum": list(prg[base + 768:base + 784]),
                "rom_offset": base,
            }
            s_base = base + 784
            if s_base + 112 <= len(prg):
                songs["Tema de Historia / Suspenso (ROM)"] = {
                    "tempo": 12,
                    "mel": list(prg[s_base:s_base + 32]),
                    "harm": list(prg[s_base + 32:s_base + 64]),
                    "bass": list(prg[s_base + 64:s_base + 96]),
                    "drum": list(prg[s_base + 96:s_base + 112]),
                    "rom_offset": s_base,
                }

    # 2. Escaneo universal de patrones rítmicos/melódicos en cualquier ROM comercial o homebrew
    for i in range(0, len(prg) - 64, 32):
        chunk = list(prg[i:i + 32])
        if all(0 <= b <= 23 for b in chunk) and 8 <= len(set(chunk)) <= 16 and chunk.count(0) >= 3:
            if len(songs) < 8:
                songs[f"Secuencia Musical ROM @ ${i:04X}"] = {
                    "tempo": 7,
                    "mel": chunk,
                    "harm": [max(0, (x - 4) if x > 4 else 0) for x in chunk],
                    "bass": [1 if step % 2 == 0 else 8 for step in range(32)],
                    "drum": [1 if step % 4 == 0 else (2 if step % 4 == 2 else 3) for step in range(16)],
                    "rom_offset": i,
                }
    st.session_state.songs = songs


def analyze_asm_file(text: str, filename: str):
    st.session_state.has_asm = True
    st.session_state.asm_name = filename
    st.session_state.asm_text = text

    # Extraer todas las cadenas de texto (.byte "..." y macros PRINT)
    strings = []
    for m in re.finditer(r'(PRINT\s+\$[0-9A-Fa-f]+,\s*"|[A-Za-z0-9_]+:\s*\.byte\s+"|\.asciiz\s+")([^"]*)(")', text):
        strings.append({
            "Identificador": m.group(1).strip().rstrip('"'),
            "Texto": m.group(2),
            "Caracteres": len(m.group(2)),
            "_raw_prefix": m.group(1)
        })
    st.session_state.asm_strings = strings

    # Extraer todas las tablas numéricas (.byte ...)
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

    # Construir lista de canciones automáticamente a partir de las etiquetas del archivo .s
    songs = {}
    if "bgm_mel" in tables:
        songs["1. Tema Principal del Juego (bgm)"] = {
            "tempo": 6,
            "mel": tables.get("bgm_mel", [0] * 64),
            "harm": tables.get("bgm_harm", [0] * 64),
            "bass": tables.get("bgm_bass", [0] * 64),
            "drum": tables.get("bgm_drum", [0] * 16),
            "labels": ("bgm_mel", "bgm_harm", "bgm_bass", "bgm_drum"),
        }
    if "susp_mel" in tables:
        songs["2. Tema de Historia / Suspenso (susp)"] = {
            "tempo": 12,
            "mel": tables.get("susp_mel", [0] * 32),
            "harm": tables.get("susp_pad", [0] * 32),
            "bass": tables.get("susp_bass", [0] * 32),
            "drum": tables.get("susp_drum", [0] * 16),
            "labels": ("susp_mel", "susp_pad", "susp_bass", "susp_drum"),
        }
    if "sel_mel" in tables:
        songs["3. Tema de Selección de Nave (sel)"] = {
            "tempo": 7,
            "mel": tables.get("sel_mel", [0] * 32),
            "harm": tables.get("sel_pad", [0] * 32),
            "bass": tables.get("sel_bass", [0] * 32),
            "drum": tables.get("sel_drum", [0] * 16),
            "labels": ("sel_mel", "sel_pad", "sel_bass", "sel_drum"),
        }
    if "go_notes" in tables:
        songs["4. Tonada de Game Over (go_notes)"] = {
            "tempo": 10,
            "mel": tables["go_notes"],
            "harm": [0] * len(tables["go_notes"]),
            "bass": tables["go_notes"],
            "drum": [0] * 8,
            "labels": ("go_notes", None, None, None),
        }

    # Detectar cualquier otra tabla musical en otros archivos .s homebrew
    for lbl, arr in tables.items():
        if lbl not in ("bgm_mel", "bgm_harm", "bgm_bass", "bgm_drum", "susp_mel", "susp_pad", "susp_bass", "susp_drum", "sel_mel", "sel_pad", "sel_bass", "sel_drum", "go_notes"):
            if any(k in lbl.lower() for k in ("mel", "song", "music", "note", "tune", "sfx", "jng")):
                songs[f"Pista Detectada: {lbl}"] = {
                    "tempo": 7,
                    "mel": [min(23, x) for x in arr],
                    "harm": [0] * len(arr),
                    "bass": [0] * len(arr),
                    "drum": [0] * 16,
                    "labels": (lbl, None, None, None),
                }

    st.session_state.songs = songs


# =============================================================================
# FUNCIONES DE EXPORTACIÓN (.S Y .NES)
# =============================================================================
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


def build_updated_nes() -> bytes:
    hdr = bytearray(st.session_state.header)
    prg = st.session_state.prg_data
    chr_d = st.session_state.chr_data
    if len(hdr) >= 6 and hdr[5] > 0:
        return bytes(hdr + prg + chr_d)
    return bytes(hdr + prg)


# =============================================================================
# RENDERIZADO DE TILES CHR, SPRITES Y AUDIO 2A03
# =============================================================================
def get_tile_matrix(bank_idx: int, table_idx: int, tile_id: int):
    offset = (bank_idx * 8192) + (table_idx * 4096) + (tile_id * 16)
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


def set_tile_matrix(bank_idx: int, table_idx: int, tile_id: int, mat):
    offset = (bank_idx * 8192) + (table_idx * 4096) + (tile_id * 16)
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


def render_chr_sheet(bank_idx: int, table_idx: int, pal_group: int, selected_tile: int):
    sub_pal = [nes_rgb(st.session_state.palette[pal_group * 4 + c]) for c in range(4)]
    img = Image.new("RGB", (128, 128))
    px = img.load()
    for t_id in range(256):
        tx = (t_id % 16) * 8
        ty = (t_id // 16) * 8
        mat = get_tile_matrix(bank_idx, table_idx, t_id)
        for y in range(8):
            for x in range(8):
                px[tx + x, ty + y] = sub_pal[mat[y][x]]
    img = img.resize((384, 384), Image.NEAREST)
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


def synthesize_song_wav(song_dict: dict) -> bytes:
    sample_rate = 22050
    step_frames = song_dict.get("tempo", 6)
    mel = song_dict["mel"]
    harm = song_dict["harm"]
    bass = song_dict["bass"]
    drum = song_dict["drum"]

    n_lo = st.session_state.note_lo
    n_hi = st.session_state.note_hi

    def get_freq(n_idx, is_tri=False):
        if n_idx <= 0 or n_idx >= len(n_lo):
            return 0.0
        period = (n_hi[n_idx] << 8) | n_lo[n_idx]
        if period <= 0:
            return 0.0
        return 1789773.0 / ((32.0 if is_tri else 16.0) * (period + 1))

    samples_per_step = int(sample_rate * (step_frames / 60.0))
    pcm = bytearray()
    lfsr = 1
    num_steps = min(128, len(mel))

    for s in range(num_steps):
        f1 = get_freq(mel[s], False)
        f2 = get_freq(harm[s] if s < len(harm) else 0, False)
        ft = get_freq(bass[s] if s < len(bass) else 0, True)
        dh = drum[s % len(drum)] if drum else 0

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


def disassemble_6502(prg_bytes: bytes, bank_idx: int, start_offset: int, num_lines: int = 40):
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


# =============================================================================
# FLUJO PRINCIPAL DE LA APLICACIÓN
# =============================================================================
init_state()

st.title("🕹️ NES Shooter Studio")
st.markdown("Suite visual universal para analizar y modificar ROMs de Nintendo NES (`*.nes`) y código fuente en ensamblador 6502 (`*.s` / `*.asm`).")

# -----------------------------------------------------------------------------
# PASO 1: PANTALLA LIMPIA HASTA QUE SE SUBA UN ARCHIVO .NES O .S
# -----------------------------------------------------------------------------
if not st.session_state.has_nes and not st.session_state.has_asm:
    st.markdown("""
    <div class="studio-card">
        <h3>📂 Paso 1: Sube tu archivo para comenzar el análisis</h3>
        <p>Selecciona cualquier archivo <b>.nes</b> (ROM compilada comercial o homebrew) o un archivo <b>.s / .asm</b> (código fuente en ensamblador 6502). Una vez subido, la aplicación analizará sus bancos gráficos, textos, tablas, vectores y canciones automáticamente.</p>
    </div>
    """, unsafe_allow_html=True)

    u_col1, u_col2 = st.columns(2)
    with u_col1:
        up_nes_main = st.file_uploader("💿 Subir archivo ROM (*.nes)", type=["nes"], key="main_nes_up")
        if up_nes_main is not None:
            analyze_nes_file(bytearray(up_nes_main.read()), up_nes_main.name)
            st.rerun()
    with u_col2:
        up_asm_main = st.file_uploader("📝 Subir código ensamblador (*.s / *.asm)", type=["s", "asm"], key="main_asm_up")
        if up_asm_main is not None:
            analyze_asm_file(up_asm_main.read().decode("utf-8", errors="ignore"), up_asm_main.name)
            st.rerun()
    st.stop()

# -----------------------------------------------------------------------------
# BARRA LATERAL (GESTIÓN DE ARCHIVOS CARGADOS Y DESCARGAS)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("📂 Archivos en Sesión")
    if st.session_state.has_nes:
        st.success(f"💿 ROM: {st.session_state.nes_name}")
    if st.session_state.has_asm:
        st.success(f"📝 ASM: {st.session_state.asm_name}")

    st.markdown("**Cargar o añadir otro archivo:**")
    side_nes = st.file_uploader("Cambiar / Añadir ROM (.nes)", type=["nes"], key="side_nes")
    if side_nes is not None:
        if st.button("📥 Analizar esta ROM .nes", use_container_width=True):
            analyze_nes_file(bytearray(side_nes.read()), side_nes.name)
            st.rerun()

    side_asm = st.file_uploader("Cambiar / Añadir Código (.s)", type=["s", "asm"], key="side_asm")
    if side_asm is not None:
        if st.button("📥 Analizar este Código .s", use_container_width=True):
            analyze_asm_file(side_asm.read().decode("utf-8", errors="ignore"), side_asm.name)
            st.rerun()

    st.divider()
    st.header("💾 Guardar Cambios")
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
    if st.button("🔄 Cerrar archivos y volver al inicio", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# -----------------------------------------------------------------------------
# PESTAÑAS DINÁMICAS SEGÚN LOS ARCHIVOS ANALIZADOS
# -----------------------------------------------------------------------------
tab_spr, tab_mus, tab_txt, tab_ins = st.tabs([
    "🎨 1. Visor y Editor de Sprites",
    "🎵 2. Canciones Chiptune (2A03)",
    "📝 3. Editor de Textos y Parámetros",
    "🔍 4. Inspector de ROM y Código 6502"
])

# =============================================================================
# PESTAÑA 1: VISOR Y EDITOR DE SPRITES
# =============================================================================
with tab_spr:
    if not st.session_state.has_nes:
        st.info("💡 Sube un archivo **.nes** en el panel izquierdo para visualizar y editar los gráficos CHR-ROM y los sprites.")
    else:
        num_chr = max(1, len(st.session_state.chr_data) // 8192)
        col_s1, col_s2, col_s3 = st.columns([1.15, 1.15, 1])

        with col_s1:
            st.subheader("1. Selecciona un Bloque Gráfico")
            b_idx = st.selectbox("Banco Gráfico CHR (8 KB):", range(num_chr), format_func=lambda i: f"Banco #{i}")
            t_idx = st.radio("Tabla de Patrones:", [0, 1], format_func=lambda x: "Tabla 0: Fondo / Escenario" if x == 0 else "Tabla 1: Naves / Personajes", horizontal=True, index=1)
            p_grp = st.selectbox("Paleta de Color:", range(8), index=4, format_func=lambda g: f"Paleta #{g} ({'Fondo' if g < 4 else 'Sprite'})")
            tile_num = st.number_input("Número de Tile a editar (0 a 255):", 0, 255, 128)

            st.image(render_chr_sheet(b_idx, t_idx, p_grp, tile_num), caption=f"Mapa completo de 256 tiles (Tile #{tile_num} seleccionado en azul)")

        with col_s2:
            st.subheader(f"2. Editor del Tile #{tile_num}")
            st.caption("Cambia los valores (0=Transparente, 1=Color 1, 2=Color 2, 3=Color 3) y pulsa Aplicar:")
            cur_mat = get_tile_matrix(b_idx, t_idx, tile_num)
            new_mat = st.data_editor(cur_mat, use_container_width=True, key=f"tile_grid_{b_idx}_{t_idx}_{tile_num}")
            if st.button("✔ Aplicar cambios al Tile", use_container_width=True):
                set_tile_matrix(b_idx, t_idx, tile_num, new_mat)
                st.success(f"Tile #{tile_num} actualizado en la ROM.")
                st.rerun()

            st.markdown("**Colores de la Paleta seleccionada (0 a 63 de la NES):**")
            pc = st.columns(4)
            for ci in range(4):
                with pc[ci]:
                    p_pos = p_grp * 4 + ci
                    st.session_state.palette[p_pos] = st.number_input(f"C{ci}", 0, 63, int(st.session_state.palette[p_pos]), key=f"p_{p_pos}")
                    hx = rgb_hex(nes_rgb(st.session_state.palette[p_pos]))
                    st.markdown(f"<div style='height:22px;background:{hx};border:2px solid #334155;border-radius:4px;'></div>", unsafe_allow_html=True)

        with col_s3:
            st.subheader("3. Visor de Sprite 16×16")
            st.caption("Previsualiza cómo se ve la nave o personaje completo uniendo sus tiles superior e inferior:")
            top_t = st.number_input("Tile Mitad Superior:", 0, 255, tile_num)
            bot_t = st.number_input("Tile Mitad Inferior:", 0, 255, min(255, tile_num + 1))
            sym_mode = st.checkbox("Simetría horizontal automática (Espejo)", value=True)
            st.image(render_metasprite(b_idx, t_idx, top_t, top_t, bot_t, bot_t, sym_mode, p_grp), caption="Vista previa de Sprite 16×16")

# =============================================================================
# PESTAÑA 2: CANCIONES CHIPTUNE DETECTADAS Y EDITOR SIMPLE
# =============================================================================
with tab_mus:
    st.subheader("🎵 Canciones y Secuencias Chiptune Detectadas")
    songs = st.session_state.songs

    if not songs:
        st.warning("No se detectaron tablas musicales automáticamente en este archivo.")
    else:
        m_col1, m_col2 = st.columns([1, 1.5])
        with m_col1:
            song_names = list(songs.keys())
            sel_song_name = st.selectbox("🎼 Elige una canción de la lista:", song_names)
            active_song = songs[sel_song_name]

            active_song["tempo"] = st.slider(
                "Velocidad de la canción (menor número = más rápido):",
                min_value=3, max_value=18, value=int(active_song.get("tempo", 6))
            )

            wav_bytes = synthesize_song_wav(active_song)
            st.markdown("**🔊 Reproductor integrado (Chip 2A03):**")
            st.audio(wav_bytes, format="audio/wav")

            st.download_button(
                "⬇️ Descargar esta canción en formato .WAV",
                data=wav_bytes,
                file_name=f"{sel_song_name[:20].strip()}.wav",
                mime="audio/wav",
                use_container_width=True,
            )

        with m_col2:
            st.markdown(f"**🎹 Editor Paso a Paso: `{sel_song_name}`**")
            st.caption("Haz clic en cualquier celda para cambiar la nota musical o el golpe de batería y pulsa el botón de abajo para escuchar tu cambio:")

            mel_arr = active_song["mel"]
            harm_arr = active_song["harm"]
            bass_arr = active_song["bass"]
            drum_arr = active_song["drum"]

            total_blocks = max(1, (len(mel_arr) + 15) // 16)
            blk = 0
            if total_blocks > 1:
                blk = st.selectbox("Compás / Bloque de 16 pasos a editar:", range(total_blocks), format_func=lambda b: f"Compás #{b + 1} (Pasos {b*16} a {b*16 + 15})")

            start_s = blk * 16
            end_s = min(len(mel_arr), start_s + 16)

            step_rows = []
            for s in range(start_s, end_s):
                m_v = mel_arr[s] if s < len(mel_arr) else 0
                h_v = harm_arr[s] if s < len(harm_arr) else 0
                b_v = bass_arr[s] if s < len(bass_arr) else 0
                d_v = drum_arr[s % len(drum_arr)] if drum_arr else 0
                step_rows.append({
                    "Paso": f"Paso {s:02d}",
                    "Melodia": NOTE_NAMES[m_v] if m_v < len(NOTE_NAMES) else NOTE_NAMES[0],
                    "Armonia": NOTE_NAMES[h_v] if h_v < len(NOTE_NAMES) else NOTE_NAMES[0],
                    "Bajo": NOTE_NAMES[b_v] if b_v < len(NOTE_NAMES) else NOTE_NAMES[0],
                    "Bateria": DRUM_NAMES[d_v] if d_v < len(DRUM_NAMES) else DRUM_NAMES[0],
                })

            ed_steps = st.data_editor(
                step_rows,
                disabled=["Paso"],
                column_config={
                    "Melodia": st.column_config.SelectboxColumn("Pulso 1 (Melodía)", options=NOTE_NAMES),
                    "Armonia": st.column_config.SelectboxColumn("Pulso 2 (Armonía)", options=NOTE_NAMES),
                    "Bajo": st.column_config.SelectboxColumn("Triángulo (Bajo)", options=NOTE_NAMES),
                    "Bateria": st.column_config.SelectboxColumn("Ruido (Batería)", options=DRUM_NAMES),
                },
                use_container_width=True,
                height=380,
                key=f"song_ed_{sel_song_name}_{blk}"
            )

            if st.button("✔ Actualizar Canción y Escuchar", use_container_width=True):
                for idx_r, r in enumerate(ed_steps):
                    pos = start_s + idx_r
                    if pos < len(mel_arr):
                        mel_arr[pos] = NOTE_TO_IDX.get(r["Melodia"], 0)
                    if pos < len(harm_arr):
                        harm_arr[pos] = NOTE_TO_IDX.get(r["Armonia"], 0)
                    if pos < len(bass_arr):
                        bass_arr[pos] = NOTE_TO_IDX.get(r["Bajo"], 0)
                    if (pos % len(drum_arr)) < len(drum_arr):
                        drum_arr[pos % len(drum_arr)] = DRUM_TO_IDX.get(r["Bateria"], 0)

                # Si la canción proviene del binario .nes, escribir también en PRG-ROM
                if "rom_offset" in active_song and st.session_state.has_nes:
                    rofs = active_song["rom_offset"]
                    for i_m, v_m in enumerate(mel_arr):
                        if rofs + i_m < len(st.session_state.prg_data):
                            st.session_state.prg_data[rofs + i_m] = v_m
                st.rerun()

# =============================================================================
# PESTAÑA 3: EDITOR DE TEXTOS Y PARÁMETROS
# =============================================================================
with tab_txt:
    col_t1, col_t2 = st.columns(2)

    with col_t1:
        st.subheader("📝 Textos del Archivo Ensamblador (.s)")
        if not st.session_state.has_asm:
            st.info("Sube un archivo **.s / .asm** para editar sus textos, líneas de historia y parámetros con nombre.")
        else:
            if st.session_state.asm_strings:
                st.caption("Modifica cualquier texto en la columna **Texto**:")
                ed_asm_s = st.data_editor(
                    st.session_state.asm_strings,
                    column_order=("Identificador", "Texto", "Caracteres"),
                    disabled=["Identificador", "Caracteres"],
                    use_container_width=True,
                    height=380,
                )
                st.session_state.asm_strings = ed_asm_s

                story_preview = [r["Texto"] for r in ed_asm_s if "st_l" in r["Identificador"]]
                if story_preview:
                    st.markdown("**Vista previa en pantalla de TV NES:**")
                    st.markdown(f'<div class="tv-preview">' + "\n".join(story_preview) + '</div>', unsafe_allow_html=True)

    with col_t2:
        st.subheader("🔤 Textos Internos del Binario (.nes)")
        if not st.session_state.has_nes:
            st.info("Sube un archivo **.nes** para escanear y parchear los textos guardados dentro de la ROM.")
        else:
            prg = st.session_state.prg_data
            found = list(re.finditer(rb"[A-Za-z0-9\-\.,!# ]{5,}", bytes(prg)))
            if found:
                st.caption("Edita la columna **Texto_En_ROM** (se ajustará automáticamente al tamaño exacto para no dañar la ROM):")
                rom_rows = [
                    {
                        "Direccion": f"${m.start():04X}",
                        "Texto_En_ROM": m.group(0).decode("ascii", errors="ignore"),
                        "Largo_Max": len(m.group(0)),
                    }
                    for m in found[:45]
                ]
                ed_rom = st.data_editor(rom_rows, disabled=["Direccion", "Largo_Max"], use_container_width=True, height=380)
                if st.button("✔ Aplicar Textos en la ROM (.nes)", use_container_width=True):
                    for r in ed_rom:
                        ofs = int(r["Direccion"][1:], 16)
                        ln = int(r["Largo_Max"])
                        st.session_state.prg_data[ofs:ofs + ln] = r["Texto_En_ROM"][:ln].ljust(ln).encode("ascii", errors="replace")
                    st.success("✔ Textos actualizados en la ROM.")

# =============================================================================
# PESTAÑA 4: INSPECTOR TÉCNICO DE ROM Y DESENSAMBLADOR 6502
# =============================================================================
with tab_ins:
    if st.session_state.has_nes:
        st.subheader(f"🔍 Análisis Técnico de `{st.session_state.nes_name}`")
        hdr = st.session_state.header
        prg = st.session_state.prg_data
        chr_d = st.session_state.chr_data

        prg_b, chr_b, f6, f7 = hdr[4], hdr[5], hdr[6], hdr[7]
        mapper = (f7 & 0xF0) | (f6 >> 4)
        mirror = "Vertical" if (f6 & 1) else "Horizontal"

        nmi_v = prg[-6] | (prg[-5] << 8) if len(prg) >= 6 else 0
        rst_v = prg[-4] | (prg[-3] << 8) if len(prg) >= 6 else 0
        irq_v = prg[-2] | (prg[-1] << 8) if len(prg) >= 6 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Mapper", f"#{mapper}", MAPPER_NAMES.get(mapper, "Especial"))
        m2.metric("Código PRG-ROM", f"{prg_b * 16} KB ({prg_b} bancos)")
        m3.metric("Gráficos CHR", f"{chr_b * 8} KB" if chr_b > 0 else "CHR-RAM")
        m4.metric("Mirroring", mirror)

        st.markdown(f"""
        <div class="studio-card">
            <b>Vectores de Arranque e Interrupción del Procesador 6502:</b><br>
            • <b>Vector RESET ($FFFC):</b> <code>${rst_v:04X}</code> (Punto donde inicia el programa al encender la consola)<br>
            • <b>Vector NMI ($FFFA):</b> <code>${nmi_v:04X}</code> (Interrupción de refresco de pantalla a 60 Hz)<br>
            • <b>Vector IRQ ($FFFE):</b> <code>${irq_v:04X}</code> (Interrupción de audio/mapper)
        </div>
        """, unsafe_allow_html=True)

        st.subheader("⚙️ Desensamblador 6502 en Vivo")
        num_p_banks = max(1, len(prg) // 16384)
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            b_sel = st.selectbox("Banco PRG:", range(num_p_banks), index=num_p_banks - 1)
        with dc2:
            jump_vec = st.selectbox("Saltar a dirección:", [
                ("Inicio del vector RESET", rst_v & 0x3FFF),
                ("Inicio del vector NMI", nmi_v & 0x3FFF),
                ("Inicio del Banco ($0000)", 0x0000),
            ], format_func=lambda x: f"{x[0]} (+${x[1]:04X})")
        with dc3:
            n_lines = st.slider("Líneas de código a mostrar:", 20, 120, 45)

        st.markdown(f'<div class="asm-viewer">{disassemble_6502(prg, b_sel, jump_vec[1], n_lines)}</div>', unsafe_allow_html=True)

    if st.session_state.has_asm:
        st.subheader(f"📄 Tablas de Datos Detectadas en `{st.session_state.asm_name}`")
        if st.session_state.asm_tables:
            sel_t = st.selectbox("Inspeccionar / Editar tabla `.byte`:", list(st.session_state.asm_tables.keys()))
            vals = st.session_state.asm_tables[sel_t]
            raw_s = st.text_area(f"Bytes de `{sel_t}` ({len(vals)} elementos):", ", ".join(str(v) for v in vals), height=110)
            if st.button(f"✔ Guardar cambios en tabla `{sel_t}`"):
                nums = [int(x) for x in re.findall(r"\d+", raw_s)]
                if nums:
                    st.session_state.asm_tables[sel_t] = nums
                    st.success(f"Tabla `{sel_t}` actualizada.")
