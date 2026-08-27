package com.datamend.backend.repository;

import com.datamend.backend.entity.Analysis;
import com.datamend.backend.entity.AnalysisStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.UUID;

@Repository
public interface AnalysisRepository extends JpaRepository<Analysis, UUID> {
    List<Analysis> findByStatus(AnalysisStatus status);
    List<Analysis> findByDatasetId(UUID datasetId);
}