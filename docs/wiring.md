# Wiring notes

## Pin map (SPI0 on the RP2040‑Zero)

```
RP2040-Zero (USB-C at the bottom)         microSD
  left edge, next to USB:  GP0  ───────── DAT0 (pin 7)  MISO
                           GP1  ───────── CD/DAT3 (pin 2)  CS
                           GP2  ───────── CLK (pin 5)
                           GP3  ───────── CMD (pin 3)  MOSI
  right edge:              3V3  ───────── VDD (pin 4)
                           GND  ───────── VSS (pin 6)
```

GP0–GP3 are adjacent pins on the left edge, which keeps soldering simple.

## microSD pin order

A microSD card has 8 evenly spaced contacts, numbered 1–8:

`1 DAT2 · 2 CD/DAT3 · 3 CMD · 4 VDD · 5 CLK · 6 VSS · 7 DAT0 · 8 DAT1`

The numbering is fixed; the only question with a loose slot or a flex‑cable board
(for example the `HAC-SD-01` board) is **which end is pin 1 and which pad goes to which pin**.

## Verify before powering a card

1. With the board unplugged, check each wire's continuity from the RP2040 pad to the slot pin (multimeter beep mode).
2. Check there is no short between neighbouring pins, and none between 3V3, 5V and GND.
3. Plug in USB **without** a card and confirm the LED turns blue.
4. Try a spare/blank card first.
5. Optional but helpful: a 10 µF capacitor across 3V3/GND near the slot, and a 10 kΩ pull‑up on DAT1 and DAT2.

If the card detect switch pin is wired, the firmware ignores it.

## Using a different board

Change `PIN_MISO`, `PIN_CS`, `PIN_SCK`, `PIN_MOSI` in `firmware/main.c` (the SPI pins must belong to the same SPI block, see the RP2040 datasheet) and `PICO_BOARD` in `firmware/CMakeLists.txt`.
