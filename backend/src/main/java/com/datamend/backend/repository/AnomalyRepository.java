package com.datamend.backend.repository;

import com.datamend.backend.entity.Anomaly;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.UUID;

@Repository
public interface AnomalyRepository extends JpaRepository<Anomaly, UUID> {
    List<Anomaly> findByAnalysisId(UUID analysisId);
}