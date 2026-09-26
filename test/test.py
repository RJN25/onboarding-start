# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

# ---------------------------------------------------------------------------
# PWM tests
# ---------------------------------------------------------------------------

CLK_PERIOD_NS = 100                 # 10 MHz system clock
PWM_PERIOD_CYCLES = 13 * 256        # PWM counter steps every 13 clocks, 256 steps per period
PWM_TIMEOUT_CYCLES = 2 * PWM_PERIOD_CYCLES + 100

async def start_and_reset(dut):
    """Start the 10 MHz clock and reset the design with SPI idle."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

def output_bit(dut, index):
    """Read bit `index` of the 16-bit output {uio_out, uo_out}."""
    value = (int(dut.uio_out.value) << 8) | int(dut.uo_out.value)
    return (value >> index) & 0x1

async def wait_for_level(dut, index, level, timeout_cycles=PWM_TIMEOUT_CYCLES):
    """Wait until output bit `index` is `level`. Returns the sim time (ns) or None on timeout."""
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        if output_bit(dut, index) == level:
            return cocotb.utils.get_sim_time(units="ns")
    return None

async def wait_for_rising_edge(dut, index, timeout_cycles=PWM_TIMEOUT_CYCLES):
    """Wait for a 0 -> 1 transition on output bit `index`. Returns the sim time (ns) or None on timeout."""
    if await wait_for_level(dut, index, 0, timeout_cycles) is None:
        return None
    return await wait_for_level(dut, index, 1, timeout_cycles)

async def measure_pwm(dut, index):
    """Measure one PWM period on output bit `index`. Returns (frequency_hz, duty_percent).

    A constant output returns (0, 0.0) if always low or (0, 100.0) if always high.
    """
    t_rise = await wait_for_rising_edge(dut, index)
    if t_rise is None:
        # No rising edge within two periods: output is constant
        return 0, 100.0 * output_bit(dut, index)
    t_fall = await wait_for_level(dut, index, 0)
    assert t_fall is not None, f"Output {index} got stuck high mid-period"
    t_rise_next = await wait_for_level(dut, index, 1)
    assert t_rise_next is not None, f"Output {index} got stuck low mid-period"
    period_ns = t_rise_next - t_rise
    return 1e9 / period_ns, 100.0 * (t_fall - t_rise) / period_ns

async def assert_constant(dut, index, level, cycles=PWM_TIMEOUT_CYCLES):
    """Assert output bit `index` holds `level` for `cycles` clock cycles (longer than one PWM period)."""
    for _ in range(cycles):
        await RisingEdge(dut.clk)
        assert output_bit(dut, index) == level, f"Output {index} expected constant {level}"

# (name, output bit index, output enable address, PWM enable address, register bit)
PWM_CHANNELS = [
    ("uo_out[0]", 0, 0x00, 0x02, 0),
    ("uo_out[7]", 7, 0x00, 0x02, 7),
    ("uio_out[0]", 8, 0x01, 0x03, 0),
    ("uio_out[7]", 15, 0x01, 0x03, 7),
]

@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("Start PWM frequency test")
    await start_and_reset(dut)

    for duty in [0x80, 0x01, 0xFE]:
        await send_spi_transaction(dut, 1, 0x04, duty)
        for name, index, out_addr, pwm_addr, reg_bit in PWM_CHANNELS:
            await send_spi_transaction(dut, 1, out_addr, 1 << reg_bit)
            await send_spi_transaction(dut, 1, pwm_addr, 1 << reg_bit)
            frequency, _ = await measure_pwm(dut, index)
            dut._log.info(f"{name} duty 0x{duty:02X}: frequency {frequency:.2f} Hz")
            assert 2970 <= frequency <= 3030, f"{name}: expected 3 kHz +/- 1%, got {frequency:.2f} Hz"
            # Disable the channel again before moving on
            await send_spi_transaction(dut, 1, out_addr, 0x00)
            await send_spi_transaction(dut, 1, pwm_addr, 0x00)

    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    dut._log.info("Start PWM duty cycle test")
    await start_and_reset(dut)

    # Enable output + PWM on every channel
    for addr in [0x00, 0x01, 0x02, 0x03]:
        await send_spi_transaction(dut, 1, addr, 0xFF)

    # Edge cases: 0x00 must stay low and 0xFF must stay high on every channel
    await send_spi_transaction(dut, 1, 0x04, 0x00)
    for index in range(16):
        _, duty = await measure_pwm(dut, index)
        assert duty == 0.0, f"Output {index}: duty 0x00 should be constant low, got {duty:.2f}%"
    await send_spi_transaction(dut, 1, 0x04, 0xFF)
    for index in range(16):
        _, duty = await measure_pwm(dut, index)
        assert duty == 100.0, f"Output {index}: duty 0xFF should be constant high, got {duty:.2f}%"

    # Sweep of mid-range values: duty = value / 256
    for value in [0x01, 0x10, 0x40, 0x80, 0xC0, 0xCF, 0xFE]:
        await send_spi_transaction(dut, 1, 0x04, value)
        expected = 100.0 * value / 256
        for name, index, _, _, _ in PWM_CHANNELS:
            frequency, duty = await measure_pwm(dut, index)
            dut._log.info(f"{name} duty 0x{value:02X}: measured {duty:.2f}% (expected {expected:.2f}%), {frequency:.2f} Hz")
            assert abs(duty - expected) <= 1.0, f"{name}: expected {expected:.2f}% +/- 1%, got {duty:.2f}%"

    dut._log.info("PWM Duty Cycle test completed successfully")


@cocotb.test()
async def test_pwm_enable_interaction(dut):
    dut._log.info("Start output enable / PWM enable interaction test")
    await start_and_reset(dut)
    await send_spi_transaction(dut, 1, 0x04, 0x80)  # 50% duty

    # Output disabled, PWM enabled -> output 0 (output enable takes precedence)
    await send_spi_transaction(dut, 1, 0x02, 0xFF)
    await send_spi_transaction(dut, 1, 0x03, 0xFF)
    for index in [0, 7, 8, 15]:
        await assert_constant(dut, index, 0)
    assert dut.uo_out.value == 0x00 and dut.uio_out.value == 0x00

    # Output enabled, PWM disabled -> output 1
    await send_spi_transaction(dut, 1, 0x02, 0x00)
    await send_spi_transaction(dut, 1, 0x03, 0x00)
    await send_spi_transaction(dut, 1, 0x00, 0xFF)
    await send_spi_transaction(dut, 1, 0x01, 0xFF)
    for index in [0, 7, 8, 15]:
        await assert_constant(dut, index, 1)
    assert dut.uo_out.value == 0xFF and dut.uio_out.value == 0xFF

    # Output enabled, PWM enabled on alternating bits -> PWM only on those bits
    await send_spi_transaction(dut, 1, 0x02, 0xAA)
    await send_spi_transaction(dut, 1, 0x03, 0x55)
    for index in range(16):
        frequency, duty = await measure_pwm(dut, index)
        if (0x55AA >> index) & 0x1:
            assert 2970 <= frequency <= 3030 and abs(duty - 50.0) <= 1.0, \
                f"Output {index}: expected 50% PWM, got {duty:.2f}% at {frequency:.2f} Hz"
        else:
            assert duty == 100.0, f"Output {index}: expected constant high, got {duty:.2f}%"

    # PWM on all bits, only some outputs enabled -> disabled outputs stay 0
    await send_spi_transaction(dut, 1, 0x02, 0xFF)
    await send_spi_transaction(dut, 1, 0x03, 0xFF)
    await send_spi_transaction(dut, 1, 0x00, 0x0F)
    await send_spi_transaction(dut, 1, 0x01, 0xF0)
    for index in range(16):
        _, duty = await measure_pwm(dut, index)
        if (0xF00F >> index) & 0x1:
            assert abs(duty - 50.0) <= 1.0, f"Output {index}: expected 50% PWM, got {duty:.2f}%"
        else:
            assert duty == 0.0, f"Output {index}: expected constant low, got {duty:.2f}%"

    dut._log.info("Enable interaction test completed successfully")
