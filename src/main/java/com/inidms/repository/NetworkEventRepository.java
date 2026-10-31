package com.inidms.repository;

import com.inidms.model.NetworkEvent;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NetworkEventRepository extends JpaRepository<NetworkEvent, Long> {
}
