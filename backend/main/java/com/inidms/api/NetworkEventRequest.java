package com.inidms.api;

import com.inidms.model.NetworkProtocol;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.time.Instant;

public record NetworkEventRequest(
        @NotBlank
        @Size(max = 45)
        String sourceIp,

        @NotBlank
        @Size(max = 45)
        String destinationIp,

        @Min(0)
        @Max(65535)
        Integer sourcePort,

        @Min(0)
        @Max(65535)
        Integer destinationPort,

        @NotNull
        NetworkProtocol protocol,

        @NotNull
        @Min(0)
        @Max(65535)
        Integer packetSize,

        @NotBlank
        @Pattern(regexp = "[A-Z][A-Z0-9_]{0,63}")
        String eventType,

        Instant capturedAt
) {
}
