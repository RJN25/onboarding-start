/*
 * Copyright (c) 2024 Arjan
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

// Write-only SPI peripheral (mode 0) that drives the PWM control registers.
// Transaction: 1 R/W bit + 7 address bits + 8 data bits, MSB first.
module spi_peripheral (
    input  wire       clk,      // system clock (10 MHz)
    input  wire       rst_n,    // active-low reset
    input  wire       sclk,     // SPI clock (asynchronous)
    input  wire       copi,     // SPI data in (asynchronous)
    input  wire       ncs,      // SPI chip select, active low (asynchronous)
    output reg  [7:0] en_reg_out_7_0,
    output reg  [7:0] en_reg_out_15_8,
    output reg  [7:0] en_reg_pwm_7_0,
    output reg  [7:0] en_reg_pwm_15_8,
    output reg  [7:0] pwm_duty_cycle
);

    localparam [6:0] MAX_ADDRESS = 7'h04;

    // Synchronizers: [0] and [1] form the 2-FF chain, [2] is the extra
    // sample used for edge detection on the edge-sensitive signals.
    reg [2:0] sclk_sync;
    reg [2:0] ncs_sync;
    reg [1:0] copi_sync;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_sync <= 3'b000;
            ncs_sync  <= 3'b111;
            copi_sync <= 2'b00;
        end else begin
            sclk_sync <= {sclk_sync[1:0], sclk};
            ncs_sync  <= {ncs_sync[1:0],  ncs};
            copi_sync <= {copi_sync[0],   copi};
        end
    end

    wire sclk_posedge = (sclk_sync[2] == 1'b0) && (sclk_sync[1] == 1'b1);
    wire ncs_posedge  = (ncs_sync[2]  == 1'b0) && (ncs_sync[1]  == 1'b1);
    wire ncs_active   = (ncs_sync[1]  == 1'b0);
    wire copi_bit     = copi_sync[1];

    // Shift in bits while nCS is low; flag a complete transaction on nCS rising edge.
    reg [15:0] shift_reg;
    reg [4:0]  bit_count;
    reg        transaction_ready;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_reg         <= 16'h0000;
            bit_count         <= 5'd0;
            transaction_ready <= 1'b0;
        end else if (ncs_active) begin
            transaction_ready <= 1'b0;
            if (sclk_posedge && bit_count != 5'd16) begin
                shift_reg <= {shift_reg[14:0], copi_bit};
                bit_count <= bit_count + 5'd1;
            end
        end else begin
            // Single-cycle pulse, only for a full-length transaction
            transaction_ready <= ncs_posedge && (bit_count == 5'd16);
            if (!ncs_posedge) begin
                bit_count <= 5'd0;
            end
        end
    end

    wire       rw_bit  = shift_reg[15];
    wire [6:0] address = shift_reg[14:8];
    wire [7:0] data    = shift_reg[7:0];

    // Update registers only for valid write transactions
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            en_reg_out_7_0  <= 8'h00;
            en_reg_out_15_8 <= 8'h00;
            en_reg_pwm_7_0  <= 8'h00;
            en_reg_pwm_15_8 <= 8'h00;
            pwm_duty_cycle  <= 8'h00;
        end else if (transaction_ready && rw_bit && address <= MAX_ADDRESS) begin
            case (address)
                7'h00: en_reg_out_7_0  <= data;
                7'h01: en_reg_out_15_8 <= data;
                7'h02: en_reg_pwm_7_0  <= data;
                7'h03: en_reg_pwm_15_8 <= data;
                7'h04: pwm_duty_cycle  <= data;
                default: ;
            endcase
        end
    end

endmodule
