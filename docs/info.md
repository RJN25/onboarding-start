<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

A write-only SPI peripheral (mode 0) configures a 16-channel PWM generator running from the 10 MHz system clock.

The SPI inputs (SCLK, COPI, nCS) are synchronized into the system clock domain with 2-stage flip-flop chains. Each
transaction is 16 bits, MSB first: 1 R/W bit (1 = write), a 7-bit address, and 8 data bits. Registers update on the
nCS rising edge, and only for complete write transactions to valid addresses; reads and invalid addresses are ignored.

| Address | Register        | Description                              | Reset |
|---------|-----------------|------------------------------------------|-------|
| 0x00    | en_reg_out_7_0  | Enable outputs on uo_out[7:0]            | 0x00  |
| 0x01    | en_reg_out_15_8 | Enable outputs on uio_out[7:0]           | 0x00  |
| 0x02    | en_reg_pwm_7_0  | Enable PWM on uo_out[7:0]                | 0x00  |
| 0x03    | en_reg_pwm_15_8 | Enable PWM on uio_out[7:0]               | 0x00  |
| 0x04    | pwm_duty_cycle  | Duty cycle (0x00 = 0%, 0xFF = 100%)      | 0x00  |

Each output is 0 when its output-enable bit is 0, 1 when output is enabled and PWM is disabled, and the PWM signal when
both are enabled. The PWM frequency is about 3 kHz (10 MHz / (13 * 256)), with duty cycle = pwm_duty_cycle / 256,
except 0xFF which forces the output high.

## How to test

Drive SPI mode 0 transactions on ui_in[0] (SCLK), ui_in[1] (COPI) and ui_in[2] (nCS) at around 100 kHz. For example,
write 0xFF to 0x00 to drive all of uo_out high, then write 0xFF to 0x02 and 0x80 to 0x04 to get a 50% 3 kHz PWM on
uo_out.

## External hardware

None required; an SPI controller (e.g. a microcontroller) and an oscilloscope or logic analyzer are useful for testing.
