/*
 * SD / microSD CID + CSD reader for the Waveshare RP2040-Zero
 *
 * Wiring (SPI0):
 *   SD DAT0 (MISO)   -> GP0
 *   SD CD/DAT3 (CS)  -> GP1
 *   SD CLK           -> GP2
 *   SD CMD (MOSI)    -> GP3
 *   SD VDD -> 3V3,  SD VSS -> GND
 *
 * USB serial (CDC) protocol:
 *   host sends "r"   -> device replies  CID=<32 hex>  CSD=<32 hex>  or  ERR=<CODE>
 *   card inserted    -> device sends CID=/CSD= by itself
 *   card removed     -> device sends REMOVED
 *
 * Error codes: NO_CARD, BAD_CMD8, INIT_TIMEOUT, CID_FAIL
 *
 * On-board RGB LED: blue = waiting for card, green = read OK, red = error.
 */
#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include "hardware/pio.h"
#include "ws2812.pio.h"

#define PIN_MISO 0
#define PIN_CS   1
#define PIN_SCK  2
#define PIN_MOSI 3
#define PIN_LED  16          /* WS2812 on the RP2040-Zero */
#define SPI_PORT spi0

static PIO led_pio = pio0;
static uint led_sm;

static void led_rgb(uint8_t r, uint8_t g, uint8_t b) {
    uint32_t grb = ((uint32_t)g << 16) | ((uint32_t)r << 8) | b;
    pio_sm_put_blocking(led_pio, led_sm, grb << 8u);
}

static inline void cs_set(int v) { gpio_put(PIN_CS, v); }

static uint8_t xfer_ff(void) {
    uint8_t tx = 0xFF, rx;
    spi_write_read_blocking(SPI_PORT, &tx, &rx, 1);
    return rx;
}

static void spi_end(void) {
    cs_set(1);
    xfer_ff();
}

/* Send an SD command and wait for R1 (CS stays low until spi_end()). */
static uint8_t send_cmd(uint8_t cmd, uint32_t arg, uint8_t crc) {
    uint8_t buf[6] = {
        (uint8_t)(0x40 | cmd), (uint8_t)(arg >> 24), (uint8_t)(arg >> 16),
        (uint8_t)(arg >> 8), (uint8_t)arg, crc
    };
    cs_set(0);
    spi_write_blocking(SPI_PORT, buf, 6);
    for (int i = 0; i < 16; i++) {
        uint8_t r = xfer_ff();
        if (r != 0xFF) return r;
    }
    return 0xFF;
}

/* Put the card in SPI mode. Returns NULL on success, otherwise an error code. */
static const char *init_card(void) {
    spi_set_baudrate(SPI_PORT, 400 * 1000);
    cs_set(1);
    uint8_t dummy[10];
    memset(dummy, 0xFF, sizeof dummy);
    spi_write_blocking(SPI_PORT, dummy, sizeof dummy);   /* >= 74 clocks */

    int ok = 0;
    for (int i = 0; i < 5; i++) {
        uint8_t r = send_cmd(0, 0, 0x95);
        spi_end();
        if (r == 0x01) { ok = 1; break; }
        sleep_ms(5);
    }
    if (!ok) return "NO_CARD";

    int v2 = 0;
    uint8_t r = send_cmd(8, 0x1AA, 0x87);
    if (r == 0x01) {
        uint8_t resp[4];
        for (int i = 0; i < 4; i++) resp[i] = xfer_ff();
        spi_end();
        if (resp[2] != 0x01 || resp[3] != 0xAA) return "BAD_CMD8";
        v2 = 1;
    } else {
        spi_end();   /* SD v1 cards do not know CMD8 */
    }

    absolute_time_t deadline = make_timeout_time_ms(2000);
    for (;;) {
        send_cmd(55, 0, 0xFF);
        spi_end();
        r = send_cmd(41, v2 ? 0x40000000 : 0, 0xFF);
        spi_end();
        if (r == 0x00) break;
        if (absolute_time_diff_us(get_absolute_time(), deadline) < 0)
            return "INIT_TIMEOUT";
        sleep_ms(10);
    }
    return NULL;
}

/* Read a 16-byte register (CMD9 = CSD, CMD10 = CID). */
static int read_reg(uint8_t cmd, uint8_t out[16]) {
    if (send_cmd(cmd, 0, 0xFF) != 0x00) { spi_end(); return 0; }
    absolute_time_t deadline = make_timeout_time_ms(300);
    uint8_t t = 0xFF;
    while (absolute_time_diff_us(get_absolute_time(), deadline) > 0) {
        t = xfer_ff();
        if (t == 0xFE) break;
    }
    if (t != 0xFE) { spi_end(); return 0; }
    uint8_t tx[16];
    memset(tx, 0xFF, sizeof tx);
    spi_write_read_blocking(SPI_PORT, tx, out, 16);
    xfer_ff(); xfer_ff();    /* CRC16 */
    spi_end();
    return 1;
}

static void print_hex(const char *tag, const uint8_t *d) {
    printf("%s=", tag);
    for (int i = 0; i < 16; i++) printf("%02x", d[i]);
    printf("\n");
}

/* Read the card and print the result; report_err prints ERR=<CODE> on failure. */
static int do_read(int report_err) {
    const char *err = init_card();
    uint8_t cid[16], csd[16];
    if (err) {
        if (report_err) printf("ERR=%s\n", err);
        return 0;
    }
    if (!read_reg(10, cid)) {
        if (report_err) printf("ERR=CID_FAIL\n");
        return 0;
    }
    print_hex("CID", cid);
    if (read_reg(9, csd)) print_hex("CSD", csd);
    return 1;
}

static int card_alive(void) {
    uint8_t r = send_cmd(13, 0, 0xFF);   /* SEND_STATUS */
    spi_end();
    return r != 0xFF;
}

int main(void) {
    stdio_init_all();

    uint offset = pio_add_program(led_pio, &ws2812_program);
    led_sm = pio_claim_unused_sm(led_pio, true);
    ws2812_program_init(led_pio, led_sm, offset, PIN_LED, 800000);
    led_rgb(0, 0, 20);

    spi_init(SPI_PORT, 400 * 1000);
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SCK,  GPIO_FUNC_SPI);
    gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);
    gpio_pull_up(PIN_MISO);
    gpio_init(PIN_CS);
    gpio_set_dir(PIN_CS, GPIO_OUT);
    cs_set(1);

    int present = 0;
    absolute_time_t next_poll = make_timeout_time_ms(500);

    for (;;) {
        int c = getchar_timeout_us(0);
        if (c == 'r' || c == 'R') {
            if (do_read(1)) { present = 1; led_rgb(0, 25, 0); }
            else            { present = 0; led_rgb(25, 0, 0); }
        }

        if (absolute_time_diff_us(get_absolute_time(), next_poll) <= 0) {
            next_poll = make_timeout_time_ms(700);
            if (!present) {
                if (do_read(0)) { present = 1; led_rgb(0, 25, 0); }
            } else if (!card_alive()) {
                present = 0;
                led_rgb(0, 0, 20);
                printf("REMOVED\n");
            }
        }
        sleep_ms(2);
    }
}
