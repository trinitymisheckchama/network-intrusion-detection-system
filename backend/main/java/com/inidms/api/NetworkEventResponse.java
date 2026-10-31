package com.inidms.api;

import com.inidms.model.NetworkEvent;
import com.inidms.model.NetworkProtocol;

import java.time.Instant;

public record NetworkEventResponse(
        Long id,
        String sourceIp,
        String destinationIp,
        Integer sourcePort,
        Integer destinationPort,
        NetworkProtocol protocol,
        Integer packetSize,
        String eventType,
        Instant capturedAt
) {
    public static NetworkEventResponse from(NetworkEvent event) {
        return new NetworkEventResponse(
                event.getId(),
                event.getSourceIp(),
                event.getDestinationIp(),
                event.getSourcePort(),
                event.getDestinationPort(),
                event.getProtocol(),
                event.getPacketSize(),
                event.getEventType(),
                event.getCapturedAt()
        );
    }
}
