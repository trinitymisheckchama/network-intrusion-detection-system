package com.inidms.service;

import com.inidms.api.NetworkEventRequest;
import com.inidms.api.NetworkEventResponse;
import com.inidms.model.NetworkEvent;
import com.inidms.repository.NetworkEventRepository;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

@Service
public class NetworkEventService {

    private final NetworkEventRepository repository;

    public NetworkEventService(NetworkEventRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public NetworkEventResponse saveEvent(NetworkEventRequest request) {
        Instant capturedAt = request.capturedAt() == null ? Instant.now() : request.capturedAt();
        NetworkEvent event = new NetworkEvent(
                request.sourceIp(),
                request.destinationIp(),
                request.sourcePort(),
                request.destinationPort(),
                request.protocol(),
                request.packetSize(),
                request.eventType(),
                capturedAt
        );
        return NetworkEventResponse.from(repository.save(event));
    }

    @Transactional(readOnly = true)
    public List<NetworkEventResponse> getEvents(int page, int size) {
        return repository.findAll(PageRequest.of(
                        page,
                        size,
                        Sort.by(Sort.Direction.DESC, "capturedAt")
                ))
                .map(NetworkEventResponse::from)
                .getContent();
    }
}
