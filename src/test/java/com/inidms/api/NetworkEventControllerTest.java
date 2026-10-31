package com.inidms.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;

import static org.hamcrest.Matchers.startsWith;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class NetworkEventControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void createsAndListsNetworkEvents() throws Exception {
        String request = objectMapper.writeValueAsString(Map.of(
                "sourceIp", "192.168.1.105",
                "destinationIp", "192.168.1.10",
                "sourcePort", 45678,
                "destinationPort", 22,
                "protocol", "TCP",
                "packetSize", 120,
                "eventType", "SUSPICIOUS_CONNECTION"
        ));

        mockMvc.perform(post("/api/events")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(request))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").isNumber())
                .andExpect(jsonPath("$.sourceIp").value("192.168.1.105"))
                .andExpect(jsonPath("$.capturedAt").value(startsWith("20")));

        mockMvc.perform(get("/api/events").param("page", "0").param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].eventType").value("SUSPICIOUS_CONNECTION"));
    }

    @Test
    void rejectsPortsOutsideTheValidRange() throws Exception {
        String request = objectMapper.writeValueAsString(Map.of(
                "sourceIp", "192.168.1.105",
                "destinationIp", "192.168.1.10",
                "sourcePort", 45678,
                "destinationPort", 70000,
                "protocol", "TCP",
                "packetSize", 120,
                "eventType", "SUSPICIOUS_CONNECTION"
        ));

        mockMvc.perform(post("/api/events")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(request))
                .andExpect(status().isBadRequest());
    }

    @Test
    void rejectsPageSizesAboveTheLimit() throws Exception {
        mockMvc.perform(get("/api/events").param("size", "101"))
                .andExpect(status().isBadRequest());
    }
}
