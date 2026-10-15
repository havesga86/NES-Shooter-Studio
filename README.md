# NES Shooter Studio

[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](http://creativecommons.org/publicdomain/zero/1.0/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Stlite_WebAssembly-ff4b4b.svg)](https://streamlit.io/)
[![Platform](https://img.shields.io/badge/Hardware-NES_6502_%2F_2A03_%2F_2C02-orange.svg)]()

**NES Shooter Studio** es una suite visual interactiva en Python que funciona tanto en navegador (mediante WebAssembly) como en escritorio para visualizar, modificar e inspeccionar **cualquier ROM de Nintendo Entertainment System (`*.nes`)** —tanto comercial como *homebrew*— así como código fuente en ensamblador 6502 (`*.s` / `*.asm`). Incluye soporte nativo para el proyecto homebrew **SHOOTER (Herscom - 2026)**.

---

## Características Principales

* **Visor y Editor de Sprites / CHR-ROM:** Soporta ROMs multi-banco (`CHR-ROM` y `CHR-RAM`) y archivos `.chr`. Permite editar tiles de 8×8 píxeles en tiempo real, armar metasprites de 16×16 combinando cualquier grupo de 4 tiles y personalizar las paletas de 64 colores de la PPU 2C02.
* **Editor y Parcheador de Textos (`.nes` y `.s`):** Escanea automáticamente cadenas de texto ASCII dentro de binarios `.nes` para parchearlas directamente en la ROM, y detecta todas las cadenas y tablas `.byte` dentro de archivos `.s` / `.asm` para editarlas de forma visual.
* **Visor y Constructor de Mapas (Nametable 256×240):** Renderiza pantallas completas de 32×30 tiles usando cualquier banco CHR y permite importar o exportar archivos `.nam`.
* **Estudio Chiptune y Sintetizador 2A03:** Secuenciador *Tracker* interactivo de 4 canales (Pulso 1, Pulso 2, Triángulo y Ruido) con síntesis de audio en tiempo real en el navegador, importación de tablas musicales desde código `.s` y exportación a `.wav`.
* **Inspector Técnico iNES y Desensamblador 6502:** Analiza cabeceras iNES, Mapper ID (NROM, MMC1, UxROM, CNROM, MMC3, etc.), *mirroring*, vectores de interrupción (`NMI`, `RESET`, `IRQ`) e incluye un desensamblador 6502 para inspeccionar el código máquina de cualquier banco `PRG-ROM`.

---

## Cómo Ejecutarlo

### Opción 1: Online desde el Navegador (GitHub Pages)
Gracias a `index.html` con **Stlite (WebAssembly)**, **NES Shooter Studio** se ejecuta directamente en el navegador sin necesidad de instalar nada ni configurar servidores externos. Solo abre la URL de **GitHub Pages** de este repositorio.

### Opción 2: Ejecución Local en PC
1. Clona este repositorio:
   ```bash
   git clone [https://github.com/TU_USUARIO/NES-Shooter-Studio.git](https://github.com/TU_USUARIO/NES-Shooter-Studio.git)
   cd NES-Shooter-Studio
