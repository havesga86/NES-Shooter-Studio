# NES Shooter Studio — Universal ROM Inspector & 6502 Homebrew Toolkit

Suite visual interactiva escrita en Python (Streamlit / Stlite) para visualizar, modificar e inspeccionar **cualquier ROM de Nintendo Entertainment System (`.nes`)** —tanto comercial como *homebrew*— así como archivos de código fuente en ensamblador 6502 (`.s` / `.asm`).

## Características Principales

* **Visor y Editor Universal de CHR-ROM y Metasprites:** Soporta ROMs multi-banco (`CHR-ROM` y `CHR-RAM`), permite editar tiles de 8×8 píxeles en tiempo real, armar metasprites de 16×16 combinando cualquier grupo de 4 tiles, personalizar las paletas de 64 colores de la PPU 2C02 y exportar bancos `.chr` o `.nes`.
* **Parcheador de Textos y Tablas (`.nes` y `.s`):** Escanea automáticamente cadenas de texto ASCII dentro de binarios `.nes` para parchearlas en el acto, y detecta todas las cadenas y tablas `.byte` dentro de archivos `.s` / `.asm` para editarlas visualmente.
* **Visor y Constructor de Nametables (256×240):** Renderiza pantallas completas de 32×30 tiles usando cualquier banco CHR y permite importar o exportar archivos `.nam`.
* **Estudio Chiptune y Sintetizador 2A03:** Secuenciador *Tracker* interactivo de 4 canales (Pulso 1, Pulso 2, Triángulo y Ruido) con síntesis de audio en tiempo real en el navegador, importación de tablas musicales desde código `.s` y exportación a `.wav`.
* **Inspector Técnico iNES y Desensamblador 6502:** Analiza cabeceras iNES, Mapper ID (NROM, MMC1, UxROM, CNROM, MMC3, etc.), *mirroring*, vectores de interrupción (`NMI`, `RESET`, `IRQ`) e incluye un desensamblador 6502 para inspeccionar el código máquina de cualquier banco `PRG-ROM`.

## Ejecución Online y Local

### Ejecutar 100% en el navegador (GitHub Pages)
Gracias a `index.html` con **Stlite (WebAssembly)**, la aplicación se ejecuta directamente en el navegador desde el enlace de GitHub Pages del repositorio sin requerir servidor.

### Ejecutar localmente en PC
```bash
pip install -r requirements.txt
streamlit run app.py
