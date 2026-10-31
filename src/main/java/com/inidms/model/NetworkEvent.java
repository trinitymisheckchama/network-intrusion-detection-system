package com.inidms.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(
        name = "network_events",
        indexes = {
                @Index(name = "idx_network_events_captured_at", columnList = "captured_at"),
                @Index(name = "idx_network_events_source_ip", columnList = "source_ip")
        }
)
public class NetworkEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "source_ip", nullable = false, length = 45)
    private String sourceIp;

    @Column(name = "destination_ip", nullable = false, length = 45)
    private String destinationIp;

    @Column(name = "source_port")
    private Integer sourcePort;

    @Column(name = "destination_port")
    private Integer destinationPort;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 8)
    private NetworkProtocol protocol;

    @Column(name = "packet_size", nullable = false)
    private Integer packetSize;

    @Column(name = "event_type", nullable = false, length = 64)
    private String eventType;

    @Column(name = "captured_at", nullable = false)
    private Instant capturedAt;

    protected NetworkEvent() {
    }

    public NetworkEvent(
            String sourceIp,
            String destinationIp,
            Integer sourcePort,
            Integer destinationPort,
            NetworkProtocol protocol,
            Integer packetSize,
            String eventType,
            Instant capturedAt
    ) {
        this.sourceIp = sourceIp;
        this.destinationIp = destinationIp;
        this.sourcePort = sourcePort;
        this.destinationPort = destinationPort;
        this.protocol = protocol;
        this.packetSize = packetSize;
        this.eventType = eventType;
        this.capturedAt = capturedAt;
    }

    public Long getId() {
        return id;
    }

    public String getSourceIp() {
        return sourceIp;
    }

    public String getDestinationIp() {
        return destinationIp;
    }

    public Integer getSourcePort() {
        return sourcePort;
    }

    public Integer getDestinationPort() {
        return destinationPort;
    }

    public NetworkProtocol getProtocol() {
        return protocol;
    }

    public Integer getPacketSize() {
        return packetSize;
    }

    public String getEventType() {
        return eventType;
    }

    public Instant getCapturedAt() {
        return capturedAt;
    }
}
